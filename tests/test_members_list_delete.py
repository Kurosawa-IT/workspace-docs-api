import uuid

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db.session import engine
from app.main import app
from app.models.membership import Membership


def _signup_and_login(client: TestClient) -> tuple[str, str, str]:
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"
    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201
    user_id = r1.json()["id"]
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    token = r2.json()["access_token"]
    return token, user_id, email


def _insert_membership(user_id: str, workspace_id: str, role: str) -> None:
    with engine.connect() as conn:
        s = Session(bind=conn)
        try:
            s.add(Membership(user_id=user_id, workspace_id=workspace_id, role=role))
            s.commit()
        finally:
            s.close()


def test_owner_admin_can_list_member_viewer_forbidden_and_delete_removes_membership():
    client = TestClient(app)

    token_owner, _owner_id, _owner_email = _signup_and_login(client)
    token_admin, admin_id, _admin_email = _signup_and_login(client)
    token_member, member_id, member_email = _signup_and_login(client)
    token_viewer, viewer_id, _viewer_email = _signup_and_login(client)

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

    r1 = client.get(
        f"/workspaces/{ws_id}/members", headers={"Authorization": f"Bearer {token_owner}"}
    )
    assert r1.status_code == 200

    r2 = client.get(
        f"/workspaces/{ws_id}/members", headers={"Authorization": f"Bearer {token_admin}"}
    )
    assert r2.status_code == 200

    r3 = client.get(
        f"/workspaces/{ws_id}/members", headers={"Authorization": f"Bearer {token_member}"}
    )
    assert r3.status_code == 403
    r4 = client.get(
        f"/workspaces/{ws_id}/members", headers={"Authorization": f"Bearer {token_viewer}"}
    )
    assert r4.status_code == 403

    r5 = client.delete(
        f"/workspaces/{ws_id}/members/{member_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r5.status_code == 204

    r6 = client.get(
        f"/workspaces/{ws_id}/members", headers={"Authorization": f"Bearer {token_owner}"}
    )
    assert r6.status_code == 200
    emails = {m["email"] for m in r6.json()}
    assert member_email not in emails


def test_cannot_remove_self():
    client = TestClient(app)

    token_owner, owner_id, _owner_email = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    r = client.delete(
        f"/workspaces/{ws_id}/members/{owner_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r.status_code == 400
