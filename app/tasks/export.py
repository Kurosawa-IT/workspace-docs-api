from __future__ import annotations

import csv
import io
import json
import logging
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

logger = logging.getLogger(__name__)


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


def _to_csv(docs: list[Document]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["id", "title", "status", "updated_at"])
    for d in docs:
        w.writerow([str(d.id), d.title, d.status, d.updated_at.isoformat()])
    return buf.getvalue()


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

        fmt = "json"
        force_fail = False
        if isinstance(job.payload, dict):
            fmt = job.payload.get("format", "json")
            force_fail = bool(job.payload.get("force_fail"))
        if fmt not in {"json", "csv"}:
            fmt = "json"

        job.status = "running"
        job.error = None
        job.updated_at = now
        db.commit()

        try:
            if force_fail:
                raise RuntimeError("forced failure for test")

            docs = (
                db.execute(
                    select(Document)
                    .where(Document.workspace_id == job.workspace_id)
                    .order_by(Document.updated_at.desc(), Document.id.desc())
                )
                .scalars()
                .all()
            )

            if fmt == "csv":
                content = _to_csv(docs)
                final_path = out_dir / f"{job.id}.csv"
                tmp_path = out_dir / f"{job.id}.csv.tmp"
                tmp_path.write_text(content, encoding="utf-8")
            else:
                payload = {
                    "job_id": str(job.id),
                    "workspace_id": str(job.workspace_id),
                    "generated_at": now.isoformat(),
                    "count": len(docs),
                    "docs": [_to_json_doc(d) for d in docs],
                }
                final_path = out_dir / f"{job.id}.json"
                tmp_path = out_dir / f"{job.id}.json.tmp"
                tmp_path.write_text(
                    json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
                )

            os.replace(tmp_path, final_path)

            job.status = "succeeded"
            job.result = {"path": str(final_path), "count": len(docs), "format": fmt}
            job.updated_at = datetime.now(UTC)
            db.commit()
            return job.result

        except Exception as e:
            logger.exception(
                "export failed job_id=%s workspace_id=%s",
                str(job.id),
                str(job.workspace_id),
            )
            job.status = "failed"
            job.error = str(e)
            job.updated_at = datetime.now(UTC)
            db.commit()
            return {"error": str(e)}
