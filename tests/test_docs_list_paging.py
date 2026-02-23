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


def test_list_docs_paging_and_sort_updated_at_desc():
    client = TestClient(app)

    token_owner, _owner_id = _signup_and_login(client)
    token_member, member_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    _insert_membership(member_id, ws_id, "member")

    doc_ids: list[str] = []
    for i in range(10):
        r = client.post(
            f"/workspaces/{ws_id}/docs",
            json={"title": f"d{i}", "body": "b", "tags": []},
            headers={"Authorization": f"Bearer {token_member}"},
        )
        assert r.status_code == 201
        doc_ids.append(r.json()["id"])

    for i, doc_id in enumerate(doc_ids):
        time.sleep(0.005)
        r = client.patch(
            f"/workspaces/{ws_id}/docs/{doc_id}",
            json={"title": f"d{i}-u"},
            headers={"Authorization": f"Bearer {token_member}"},
        )
        assert r.status_code == 200

    r1 = client.get(
        f"/workspaces/{ws_id}/docs?page=1&page_size=3&sort=updated_at_desc",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r1.status_code == 200
    body1 = r1.json()
    assert body1["total"] == 10
    assert body1["page"] == 1
    assert body1["page_size"] == 3
    assert len(body1["items"]) == 3

    titles1 = [it["title"] for it in body1["items"]]
    assert titles1 == ["d9-u", "d8-u", "d7-u"]

    r4 = client.get(
        f"/workspaces/{ws_id}/docs?page=4&page_size=3&sort=updated_at_desc",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r4.status_code == 200
    body4 = r4.json()
    assert body4["total"] == 10
    assert len(body4["items"]) == 1
