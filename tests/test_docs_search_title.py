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


def test_search_by_title_query_ilike():
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

    for title in ["Hello World", "Hello FastAPI", "Goodbye"]:
        r = client.post(
            f"/workspaces/{ws_id}/docs",
            json={"title": title, "body": "b", "tags": []},
            headers={"Authorization": f"Bearer {token_member}"},
        )
        assert r.status_code == 201

    r_search = client.get(
        f"/workspaces/{ws_id}/docs?query=hello",
        headers={"Authorization": f"Bearer {token_member}"},
    )
    assert r_search.status_code == 200
    titles = {it["title"] for it in r_search.json()["items"]}
    assert titles == {"Hello World", "Hello FastAPI"}
