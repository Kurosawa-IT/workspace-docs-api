from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "workspace_docs",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.autodiscover_tasks(["app"])

if settings.app_env in {"ci", "test"}:
    celery_app.conf.task_always_eager = True
    celery_app.conf.task_eager_propagates = True

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=2,
)
