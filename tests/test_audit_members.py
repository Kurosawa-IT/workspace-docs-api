import uuid
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select
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


def _latest_action(ws_id: str, action: str) -> AuditLog:
    with engine.connect() as conn:
        s = Session(bind=conn)
        try:
            return (
                s.execute(
                    select(AuditLog)
                    .where(AuditLog.workspace_id == UUID(ws_id), AuditLog.action == action)
                    .order_by(AuditLog.created_at.desc())
                    .limit(1)
                )
                .scalars()
                .one()
            )
        finally:
            s.close()


def test_audit_for_member_add_remove_change_role():
    client = TestClient(app)

    token_owner, owner_id = _signup_and_login(client)
    token_other, other_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    r_add = client.post(
        f"/workspaces/{ws_id}/members",
        json={"user_id": other_id, "role": "member"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_add.status_code in (200, 201)

    a_add = _latest_action(ws_id, "member.add")
    assert str(a_add.actor_user_id) == owner_id
    assert a_add.target_type == "membership"
    assert a_add.after is not None and a_add.after["role"] == "member"

    r_ch = client.patch(
        f"/workspaces/{ws_id}/members/{other_id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ch.status_code == 200

    a_ch = _latest_action(ws_id, "member.change_role")
    assert a_ch.before is not None and a_ch.before["role"] == "member"
    assert a_ch.after is not None and a_ch.after["role"] == "admin"

    r_rm = client.delete(
        f"/workspaces/{ws_id}/members/{other_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_rm.status_code == 204

    a_rm = _latest_action(ws_id, "member.remove")
    assert a_rm.before is not None and a_rm.before["role"] == "admin"
    assert a_rm.after is None
