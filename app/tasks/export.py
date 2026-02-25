from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select

from app.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.job import Job


@celery_app.task(name="export.run")
def run_export(job_id: str) -> str:
    now = datetime.now(UTC)

    with SessionLocal() as db:
        job = db.execute(select(Job).where(Job.id == UUID(job_id))).scalar_one_or_none()
        if job is None:
            return "missing"

        job.status = "running"
        job.updated_at = now
        db.commit()

        job.status = "succeeded"
        job.result = {"message": "ok"}
        job.updated_at = datetime.now(UTC)
        db.commit()

    return "ok"
