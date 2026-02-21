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


def test_list_workspaces_only_returns_my_memberships():
    client = TestClient(app)

    token_a = _signup_and_login(client)
    token_b = _signup_and_login(client)

    r1 = client.post(
        "/workspaces", json={"name": "A1"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    assert r1.status_code == 201
    r2 = client.post(
        "/workspaces", json={"name": "A2"}, headers={"Authorization": f"Bearer {token_a}"}
    )
    assert r2.status_code == 201

    r3 = client.post(
        "/workspaces", json={"name": "B1"}, headers={"Authorization": f"Bearer {token_b}"}
    )
    assert r3.status_code == 201

    r4 = client.get("/workspaces", headers={"Authorization": f"Bearer {token_a}"})
    assert r4.status_code == 200
    names_a = {w["name"] for w in r4.json()}
    assert names_a == {"A1", "A2"}

    r5 = client.get("/workspaces", headers={"Authorization": f"Bearer {token_b}"})
    assert r5.status_code == 200
    names_b = {w["name"] for w in r5.json()}
    assert names_b == {"B1"}
