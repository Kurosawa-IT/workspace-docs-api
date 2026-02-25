from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job import Job


def create_export_job(
    db: Session,
    *,
    workspace_id: UUID,
    idempotency_key: str,
    payload: dict | None = None,
) -> tuple[Job, bool]:
    existing = db.execute(
        select(Job).where(
            Job.workspace_id == workspace_id,
            Job.type == "export",
            Job.idempotency_key == idempotency_key,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return existing, False

    now = datetime.now(UTC)
    job = Job(
        workspace_id=workspace_id,
        type="export",
        status="queued",
        idempotency_key=idempotency_key,
        payload=payload,
        updated_at=now,
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        existing2 = db.execute(
            select(Job).where(
                Job.workspace_id == workspace_id,
                Job.type == "export",
                Job.idempotency_key == idempotency_key,
            )
        ).scalar_one()
        return existing2, False

    db.refresh(job)
    return job, True
