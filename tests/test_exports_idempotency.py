import uuid
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.job import Job
from app.models.membership import Membership


def _signup_and_login(client: TestClient) -> tuple[str, str]:
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"
    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201
    user_id = r1.json()["id"]
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    return r2.json()["access_token"], user_id


def _insert_membership(user_id: str, workspace_id: str, role: str) -> None:
    with engine.connect() as conn:
        s = Session(bind=conn)
        try:
            s.add(Membership(user_id=UUID(user_id), workspace_id=UUID(workspace_id), role=role))
            s.commit()
        finally:
            s.close()


def _job_count(ws_id: str, idem: str) -> int:
    with engine.connect() as conn:
        return conn.execute(
            select(func.count())
            .select_from(Job)
            .where(
                Job.workspace_id == UUID(ws_id), Job.type == "export", Job.idempotency_key == idem
            )
        ).scalar_one()


def test_export_idempotency_and_auth():
    client = TestClient(app)

    token_owner, _ = _signup_and_login(client)
    token_member, member_id = _signup_and_login(client)
    token_outsider, _ = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    _insert_membership(member_id, ws_id, "member")

    idem = "idem-" + str(uuid.uuid4())

    r1 = client.post(
        f"/workspaces/{ws_id}/exports",
        headers={"Authorization": f"Bearer {token_member}", "Idempotency-Key": idem},
    )
    assert r1.status_code in (200, 201)
    job_id_1 = r1.json()["id"]

    r2 = client.post(
        f"/workspaces/{ws_id}/exports",
        headers={"Authorization": f"Bearer {token_member}", "Idempotency-Key": idem},
    )
    assert r2.status_code == 200
    job_id_2 = r2.json()["id"]

    assert job_id_1 == job_id_2
    assert _job_count(ws_id, idem) == 1

    r3 = client.post(
        f"/workspaces/{ws_id}/exports",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r3.status_code == 422

    r4 = client.post(
        f"/workspaces/{ws_id}/exports",
        headers={"Authorization": f"Bearer {token_outsider}", "Idempotency-Key": "x"},
    )
    assert r4.status_code == 404
