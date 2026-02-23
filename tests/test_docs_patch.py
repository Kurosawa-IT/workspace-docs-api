import time
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


def test_patch_doc_member_ok_viewer_forbidden_and_updates_updated_fields():
    client = TestClient(app)

    token_owner, _owner_id = _signup_and_login(client)
    token_member, member_id = _signup_and_login(client)
    token_viewer, viewer_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    _insert_membership(member_id, ws_id, "member")
    _insert_membership(viewer_id, ws_id, "viewer")

    r_doc = client.post(
        f"/workspaces/{ws_id}/docs",
        json={"title": "t1", "body": "b1", "tags": ["a"]},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_doc.status_code == 201
    doc = r_doc.json()
    doc_id = doc["id"]
    old_updated_at = doc["updated_at"]
    old_updated_by = doc["updated_by"]
    time.sleep(0.01)

    r_patch = client.patch(
        f"/workspaces/{ws_id}/docs/{doc_id}",
        json={"title": "t2"},
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_patch.status_code == 200
    patched = r_patch.json()
    assert patched["title"] == "t2"
    assert patched["body"] == "b1"
    assert patched["tags"] == ["a"]

    assert patched["updated_by"] == member_id
    assert patched["updated_by"] != old_updated_by
    assert patched["updated_at"] != old_updated_at

    r_forbidden = client.patch(
        f"/workspaces/{ws_id}/docs/{doc_id}",
        json={"title": "t3"},
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert r_forbidden.status_code == 403
