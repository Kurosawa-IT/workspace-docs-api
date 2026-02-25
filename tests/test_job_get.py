import uuid
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
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


def test_get_job_visible_only_with_membership():
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

    r_exp = client.post(
        f"/workspaces/{ws_id}/exports",
        headers={"Authorization": f"Bearer {token_member}", "Idempotency-Key": idem},
    )
    assert r_exp.status_code in (200, 201)
    job_id = r_exp.json()["id"]

    r_get = client.get(
        f"/workspaces/{ws_id}/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_get.status_code == 200
    body = r_get.json()
    assert body["id"] == job_id
    assert body["status"] in {"queued", "running", "succeeded", "failed"}

    r_out = client.get(
        f"/workspaces/{ws_id}/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token_outsider}"},
    )
    assert r_out.status_code == 404
