import uuid

from fastapi.testclient import TestClient

from app.main import app


def _signup_and_login(client: TestClient) -> str:
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"
    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    return r2.json()["access_token"]


def test_get_workspace_requires_membership():
    client = TestClient(app)

    token_a = _signup_and_login(client)
    token_b = _signup_and_login(client)

    r1 = client.post(
        "/workspaces", json={"name": "A1"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    assert r1.status_code == 201
    ws_id = r1.json()["id"]

    r2 = client.get(f"/workspaces/{ws_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert r2.status_code == 200
    assert r2.json()["id"] == ws_id

    r3 = client.get(f"/workspaces/{ws_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert r3.status_code == 404
