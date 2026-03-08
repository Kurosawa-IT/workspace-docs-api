from __future__ import annotations

import re

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest
from sqlalchemy import func, select

from app.db.session import SessionLocal
from app.models.job import Job

HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "path", "status"],
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "path", "status"],
)


_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)


JOB_QUEUE_DEPTH = Gauge(
    "job_queue_depth",
    "Current number of jobs by type and status",
    ["type", "status"],
)

JOB_LATENCY_SECONDS = Gauge(
    "job_latency_seconds",
    "Latency from queued to succeeded for the latest completed job",
    ["type"],
)


def normalize_path(path: str) -> str:
    return _UUID_RE.sub("{id}", path)


def render_metrics() -> tuple[bytes, str]:
    refresh_job_metrics()
    return generate_latest(), CONTENT_TYPE_LATEST


def refresh_job_metrics() -> None:
    with SessionLocal() as db:
        rows = db.execute(
            select(Job.type, Job.status, func.count()).group_by(Job.type, Job.status)
        ).all()

        counts: dict[tuple[str, str], int] = {}
        for job_type, status, count in rows:
            counts[(job_type, status)] = int(count)

        for status in ("queued", "running", "succeeded", "failed"):
            JOB_QUEUE_DEPTH.labels(type="export", status=status).set(
                counts.get(("export", status), 0)
            )

        latest = db.execute(
            select(Job)
            .where(Job.type == "export", Job.status == "succeeded")
            .order_by(Job.updated_at.desc(), Job.id.desc())
            .limit(1)
        ).scalar_one_or_none()

        if latest is None:
            JOB_LATENCY_SECONDS.labels(type="export").set(0)
        else:
            latency = (latest.updated_at - latest.created_at).total_seconds()
            JOB_LATENCY_SECONDS.labels(type="export").set(max(latency, 0))
