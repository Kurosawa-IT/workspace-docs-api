from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.job import Job
from app.services.audit import write_audit_log


def create_export_job(
    db: Session,
    *,
    workspace_id: UUID,
    idempotency_key: str,
    actor_user_id: UUID,
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

    write_audit_log(
        db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action="export.create",
        target_type="job",
        target_id=job.id,
        before=None,
        after={
            "type": job.type,
            "idempotency_key": job.idempotency_key,
            "format": (payload or {}).get("format"),
        },
    )
    db.commit()
    return job, True
