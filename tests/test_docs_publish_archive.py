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


def test_publish_archive_transitions_and_viewer_forbidden():
    client = TestClient(app)

    token_owner, _ = _signup_and_login(client)
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
        json={"title": "t", "body": "b", "tags": []},
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_doc.status_code == 201
    doc = r_doc.json()
    doc_id = doc["id"]
    assert doc["status"] == "draft"
    assert doc["published_at"] is None
    assert doc["archived_at"] is None

    r_forbidden = client.post(
        f"/workspaces/{ws_id}/docs/{doc_id}/publish",
        headers={"Authorization": f"Bearer {token_viewer}"},
    )
    assert r_forbidden.status_code == 403

    r_pub = client.post(
        f"/workspaces/{ws_id}/docs/{doc_id}/publish",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_pub.status_code == 200
    pub = r_pub.json()
    assert pub["status"] == "published"
    assert pub["published_at"] is not None
    assert pub["archived_at"] is None

    r_pub_again = client.post(
        f"/workspaces/{ws_id}/docs/{doc_id}/publish",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_pub_again.status_code == 409

    r_arc = client.post(
        f"/workspaces/{ws_id}/docs/{doc_id}/archive",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_arc.status_code == 200
    arc = r_arc.json()
    assert arc["status"] == "archived"
    assert arc["archived_at"] is not None

    r_pub_from_arch = client.post(
        f"/workspaces/{ws_id}/docs/{doc_id}/publish",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_pub_from_arch.status_code == 409

    r_arc_again = client.post(
        f"/workspaces/{ws_id}/docs/{doc_id}/archive",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_arc_again.status_code == 409
