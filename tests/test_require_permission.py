import uuid

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
            s.add(Membership(user_id=user_id, workspace_id=workspace_id, role=role))
            s.commit()
        finally:
            s.close()


def test_viewer_access_protected_route_returns_403():
    client = TestClient(app)

    token_owner, _owner_id = _signup_and_login(client)
    token_viewer, viewer_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    _insert_membership(viewer_id, ws_id, "viewer")

    r = client.get(
        f"/workspaces/{ws_id}/members",
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert r.status_code == 403
