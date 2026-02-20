import uuid

from fastapi.testclient import TestClient

from app.main import app


def test_signup_success():
    client = TestClient(app)
    email = f"{uuid.uuid4()}@example.com"
    res = client.post("/auth/signup", json={"email": email, "password": "password123"})
    assert res.status_code == 201
    body = res.json()
    assert body["email"] == email
    assert body["is_active"] is True


def test_signup_duplicate_email_returns_409():
    client = TestClient(app)
    email = f"{uuid.uuid4()}@example.com"
    res1 = client.post("/auth/signup", json={"email": email, "password": "password123"})
    assert res1.status_code == 201

    res2 = client.post("/auth/signup", json={"email": email, "password": "password123"})
    assert res2.status_code == 409
