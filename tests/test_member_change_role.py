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
    token = r2.json()["access_token"]
    return token, user_id


def _insert_membership(user_id: str, workspace_id: str, role: str) -> None:
    with engine.connect() as conn:
        s = Session(bind=conn)
        try:
            s.add(
                Membership(
                    user_id=UUID(user_id),
                    workspace_id=UUID(workspace_id),
                    role=role,
                )
            )
            s.commit()
        finally:
            s.close()


def test_owner_can_change_role_others_forbidden():
    client = TestClient(app)

    token_owner, _owner_id = _signup_and_login(client)
    token_admin, admin_id = _signup_and_login(client)
    token_member, member_id = _signup_and_login(client)
    token_viewer, viewer_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    _insert_membership(admin_id, ws_id, "admin")
    _insert_membership(member_id, ws_id, "member")
    _insert_membership(viewer_id, ws_id, "viewer")

    r_ok = client.patch(
        f"/workspaces/{ws_id}/members/{member_id}",
        json={"role": "admin"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ok.status_code == 200
    assert r_ok.json()["user_id"] == member_id
    assert r_ok.json()["role"] == "admin"

    r_admin = client.patch(
        f"/workspaces/{ws_id}/members/{viewer_id}",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {token_admin}"},
    )
    assert r_admin.status_code == 403

    r_member = client.patch(
        f"/workspaces/{ws_id}/members/{viewer_id}",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_member.status_code == 403

    r_viewer = client.patch(
        f"/workspaces/{ws_id}/members/{admin_id}",
        json={"role": "member"},
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert r_viewer.status_code == 403
