import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_create_workspace_creates_owner_membership():
    client = TestClient(app)

    email = f"{uuid.uuid4()}@example.com"
    password = "password123"

    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201

    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    token = r2.json()["access_token"]

    r3 = client.post(
        "/workspaces",
        json={"name": "My Workspace"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 201
    body = r3.json()
    assert body["name"] == "My Workspace"
    assert "id" in body
