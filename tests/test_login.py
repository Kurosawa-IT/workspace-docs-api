import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_login_success_returns_token():
    client = TestClient(app)
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"

    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201

    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    body = r2.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_login_wrong_password_is_401():
    client = TestClient(app)
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"

    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201

    r2 = client.post("/auth/login", json={"email": email, "password": "wrongpass123"})
    assert r2.status_code == 401
