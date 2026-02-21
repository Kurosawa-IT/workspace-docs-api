import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_me_requires_bearer_token():
    client = TestClient(app)
    res = client.get("/auth/me")
    assert res.status_code == 401


def test_me_returns_current_user():
    client = TestClient(app)
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"

    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201
    user_id = r1.json()["id"]

    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    token = r2.json()["access_token"]

    r3 = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r3.status_code == 200
    body = r3.json()
    assert body["id"] == user_id
    assert body["email"] == email
