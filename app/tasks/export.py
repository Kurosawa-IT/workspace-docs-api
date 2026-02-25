from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from app.celery_app import celery_app
from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.job import Job


def _to_json_doc(d: Document) -> dict:
    def dt(x):
        return x.isoformat() if x is not None else None

    return {
        "id": str(d.id),
        "workspace_id": str(d.workspace_id),
        "title": d.title,
        "body": d.body,
        "status": d.status,
        "tags": d.tags,
        "created_by": str(d.created_by),
        "updated_by": str(d.updated_by),
        "created_at": dt(d.created_at),
        "updated_at": dt(d.updated_at),
        "published_at": dt(d.published_at),
        "archived_at": dt(d.archived_at),
    }


@celery_app.task(name="export.run")
def run_export(job_id: str) -> dict:
    job_uuid = UUID(job_id)
    now = datetime.now(UTC)

    out_dir = Path(settings.EXPORT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    with SessionLocal() as db:
        job = db.execute(select(Job).where(Job.id == job_uuid)).scalar_one_or_none()
        if job is None:
            return {"status": "missing"}

        job.status = "running"
        job.error = None
        job.updated_at = now
        db.commit()

        try:
            docs = (
                db.execute(
                    select(Document)
                    .where(Document.workspace_id == job.workspace_id)
                    .order_by(Document.updated_at.desc(), Document.id.desc())
                )
                .scalars()
                .all()
            )

            payload = {
                "job_id": str(job.id),
                "workspace_id": str(job.workspace_id),
                "generated_at": now.isoformat(),
                "count": len(docs),
                "docs": [_to_json_doc(d) for d in docs],
            }

            final_path = out_dir / f"{job.id}.json"
            tmp_path = out_dir / f"{job.id}.json.tmp"

            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            os.replace(tmp_path, final_path)

            job.status = "succeeded"
            job.result = {"path": str(final_path), "count": len(docs)}
            job.updated_at = datetime.now(UTC)
            db.commit()
            return job.result

        except Exception as e:
            job.status = "failed"
            job.error = str(e)
            job.updated_at = datetime.now(UTC)
            db.commit()
            return {"error": str(e)}
