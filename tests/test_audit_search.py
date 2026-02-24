import uuid
from datetime import timedelta
from urllib.parse import urlencode
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


def _latest_audit(ws_id: str, action: str) -> AuditLog:
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


def test_audit_search_filters_action_actor_period_and_non_member_hidden():
    client = TestClient(app)

    token_owner, owner_id = _signup_and_login(client)
    token_member, member_id = _signup_and_login(client)
    token_outsider, _ = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    r_add = client.post(
        f"/workspaces/{ws_id}/members",
        json={"user_id": member_id, "role": "member"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_add.status_code in (200, 201)

    r_doc = client.post(
        f"/workspaces/{ws_id}/docs",
        json={"title": "t", "body": "b", "tags": []},
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_doc.status_code == 201

    r_action = client.get(
        f"/workspaces/{ws_id}/audit?action=doc.create&page=1&page_size=10",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_action.status_code == 200
    body = r_action.json()
    assert body["total"] >= 1
    assert all(it["action"] == "doc.create" for it in body["items"])

    r_actor = client.get(
        f"/workspaces/{ws_id}/audit?action=member.add&actor={owner_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_actor.status_code == 200
    body2 = r_actor.json()
    assert body2["total"] >= 1
    assert all(it["actor_user_id"] == owner_id for it in body2["items"])
    assert all(it["action"] == "member.add" for it in body2["items"])

    a = _latest_audit(ws_id, "doc.create")
    from_ts = (a.created_at - timedelta(seconds=1)).isoformat()
    to_ts = (a.created_at + timedelta(seconds=1)).isoformat()

    params = urlencode(
        {
            "action": "doc.create",
            "from": from_ts,
            "to": to_ts,
        }
    )

    r_period = client.get(
        f"/workspaces/{ws_id}/audit?{params}",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_period.status_code == 200

    r_out = client.get(
        f"/workspaces/{ws_id}/audit",
        headers={"Authorization": f"Bearer {token_outsider}"},
    )
    assert r_out.status_code == 404
