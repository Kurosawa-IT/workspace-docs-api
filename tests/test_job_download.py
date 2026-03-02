import uuid
from pathlib import Path
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import engine
from app.main import app
from app.models.job import Job
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


def test_download_succeeded_job_returns_file():
    client = TestClient(app)
    token, user_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    export_dir = Path(settings.EXPORT_DIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    filename = f"dummy-{uuid.uuid4()}.csv"
    p = export_dir / filename
    p.write_text("id,title\n1,csv-title\n", encoding="utf-8")

    with engine.connect() as conn:
        s = Session(bind=conn)
        try:
            job = Job(
                workspace_id=UUID(ws_id),
                type="export",
                status="succeeded",
                idempotency_key="idem-" + str(uuid.uuid4()),
                payload={"format": "csv"},
                result={"path": str(p), "format": "csv"},
            )
            s.add(job)
            s.commit()
            s.refresh(job)
            job_id = str(job.id)
        finally:
            s.close()

    r_dl = client.get(
        f"/workspaces/{ws_id}/jobs/{job_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_dl.status_code == 200
    assert len(r_dl.content) > 10


def test_download_running_job_returns_409():
    client = TestClient(app)
    token, user_id = _signup_and_login(client)

    r_ws = client.post(
        "/workspaces",
        json={"name": "WS"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_ws.status_code == 201
    ws_id = r_ws.json()["id"]

    with engine.connect() as conn:
        s = Session(bind=conn)
        try:
            job = Job(
                workspace_id=UUID(ws_id),
                type="export",
                status="running",
                idempotency_key="idem-" + str(uuid.uuid4()),
                payload={"format": "json"},
            )
            s.add(job)
            s.commit()
            s.refresh(job)
            job_id = str(job.id)
        finally:
            s.close()

    r_dl = client.get(
        f"/workspaces/{ws_id}/jobs/{job_id}/download",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r_dl.status_code == 409
