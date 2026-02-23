from fastapi.testclient import TestClient

from app.main import app


def test_error_shape_unauthorized_is_unified():
    client = TestClient(app)

    res = client.get("/auth/me")
    assert res.status_code == 401

    body = res.json()
    assert "request_id" in body
    assert "error" in body

    err = body["error"]
    assert set(err.keys()) == {"code", "message", "details"}
    assert err["code"] == "unauthorized"
