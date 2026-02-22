import re

from fastapi.testclient import TestClient

from app.main import app


def test_request_id_is_generated():
    client = TestClient(app)
    res = client.get("/health")
    assert res.status_code == 200

    rid = res.headers.get("X-Request-ID")
    assert rid is not None
    assert re.fullmatch(r"[0-9a-f-]{36}", rid) is not None


def test_request_id_is_propagated():
    client = TestClient(app)
    res = client.get("/health", headers={"X-Request-ID": "my-request-id"})
    assert res.status_code == 200
    assert res.headers["X-Request-ID"] == "my-request-id"
