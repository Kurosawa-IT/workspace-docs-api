from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "workspace_docs",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

celery_app.autodiscover_tasks(["app"])
