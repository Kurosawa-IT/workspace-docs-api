import uuid
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.audit_log import AuditLog
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


def _audit_count(ws_id: str) -> int:
    with engine.connect() as conn:
        return conn.execute(
            select(func.count()).select_from(AuditLog).where(AuditLog.workspace_id == UUID(ws_id))
        ).scalar_one()


def test_audit_increases_on_doc_create_update_delete_and_has_actor_action_target():
    client = TestClient(app)

    token_owner, _ = _signup_and_login(client)
    token_member, member_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    _insert_membership(member_id, ws_id, "member")

    before = _audit_count(ws_id)

    r_doc = client.post(
        f"/workspaces/{ws_id}/docs",
        json={"title": "t", "body": "b", "tags": ["a"]},
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_doc.status_code == 201
    doc_id = r_doc.json()["id"]
    after_create = _audit_count(ws_id)
    assert after_create == before + 1

    r_up = client.patch(
        f"/workspaces/{ws_id}/docs/{doc_id}",
        json={"title": "t2"},
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_up.status_code == 200
    after_update = _audit_count(ws_id)
    assert after_update == after_create + 1

    r_del = client.delete(
        f"/workspaces/{ws_id}/docs/{doc_id}",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_del.status_code == 204
    after_delete = _audit_count(ws_id)
    assert after_delete == after_update + 1

    with engine.connect() as conn:
        s = Session(bind=conn)
        row = (
            s.execute(
                select(AuditLog)
                .where(AuditLog.workspace_id == UUID(ws_id))
                .order_by(AuditLog.created_at.desc())
                .limit(1)
            )
            .scalars()
            .one()
        )

    assert row.actor_user_id == UUID(member_id)
    assert row.action in {"doc.create", "doc.update", "doc.delete"}
    assert row.target_type == "document"
    assert row.target_id is not None
