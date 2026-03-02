import uuid

from fastapi.testclient import TestClient

from app.main import app


def _signup_and_login(client: TestClient) -> tuple[str, str]:
    email = f"{uuid.uuid4()}@example.com"
    password = "password123"
    r1 = client.post("/auth/signup", json={"email": email, "password": password})
    assert r1.status_code == 201
    user_id = r1.json()["id"]
    r2 = client.post("/auth/login", json={"email": email, "password": password})
    assert r2.status_code == 200
    return r2.json()["access_token"], user_id


def test_export_forced_failure_marks_failed_and_download_is_409():
    client = TestClient(app)

    token, user_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    idem = "idem-" + str(uuid.uuid4())

    r_exp = client.post(
        f"/workspaces/{ws_id}/exports",
        json={"format": "json", "force_fail": True},
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": idem},
    )
    assert r_exp.status_code in (200, 201)
    job_id = r_exp.json()["id"]

    r_job = client.get(
        f"/workspaces/{ws_id}/jobs/{job_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_job.status_code == 200
    body = r_job.json()
    assert body["status"] == "failed"
    assert body["error"] is not None
    assert body["error"] != ""

    r_dl = client.get(
        f"/workspaces/{ws_id}/jobs/{job_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_dl.status_code == 409
