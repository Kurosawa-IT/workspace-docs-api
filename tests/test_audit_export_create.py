import uuid
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.audit_log import AuditLog


def _signup_and_login(client: TestClient) -> tuple[str, str]:
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"
    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201
    user_id = r1.json()["id"]
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    return r2.json()["access_token"], user_id


def _audit_count(ws_id: str) -> int:
    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.workspace_id == UUID(ws_id))
        ).scalar_one()


def test_export_create_writes_audit_log():
    client = TestClient(app)

    token, user_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    before = _audit_count(ws_id)

    idem = "idem-" + str(uuid.uuid4())
    r_exp = client.post(
        f"/workspaces/{ws_id}/exports",
        json={"format": "json"},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem},
    )
    assert r_exp.status_code in (200, 201)
    job_id = r_exp.json()["id"]

    after = _audit_count(ws_id)
    assert after == before + 1

    with engine.connect() as conn:
        s = Session(bind=conn)
        try:
            log = (
                s.execute(
                    select(AuditLog)
                    .where(AuditLog.workspace_id == UUID(ws_id), AuditLog.action == "export.create")
                    .order_by(AuditLog.created_at.desc())
                    .limit(1)
                )
                .scalars()
                .one()
            )
        finally:
            s.close()

    assert str(log.actor_user_id) == user_id
    assert log.target_type == "job"
    assert str(log.target_id) == job_id
    assert log.request_id is not None and log.request_id != "-"
