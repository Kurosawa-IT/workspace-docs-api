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
            s.add(Membership(user_id=UUID(user_id), workspace_id=UUID(workspace_id), role=role))
            s.commit()
        finally:
            s.close()


def test_get_doc_viewer_ok_non_member_404_and_missing_doc_404():
    client = TestClient(app)

    token_owner, _owner_id = _signup_and_login(client)
    token_viewer, viewer_id = _signup_and_login(client)
    token_outsider, _outsider_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    _insert_membership(viewer_id, ws_id, "viewer")

    r_doc = client.post(
        f"/workspaces/{ws_id}/docs",
        json={"title": "t", "body": "b", "tags": ["a", "b"]},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_doc.status_code == 201
    doc = r_doc.json()
    doc_id = doc["id"]

    r_get = client.get(
        f"/workspaces/{ws_id}/docs/{doc_id}",
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert r_get.status_code == 200
    body = r_get.json()
    assert body["id"] == doc_id
    assert body["workspace_id"] == ws_id
    assert body["status"] == "draft"
    assert body["tags"] == ["a", "b"]
    assert "created_at" in body
    assert "updated_at" in body

    r_out = client.get(
        f"/workspaces/{ws_id}/docs/{doc_id}",
        headers={"Authorization": f"Bearer {token_outsider}"},
    )
    assert r_out.status_code == 404

    missing_id = str(uuid.uuid4())
    r_missing = client.get(
        f"/workspaces/{ws_id}/docs/{missing_id}",
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert r_missing.status_code == 404
