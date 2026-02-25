import time

from app.celery_app import celery_app


@celery_app.task(name="dummy.add")
def add(a: int, b: int) -> int:
    return a + b


@celery_app.task(name="dummy.sleep")
def sleep(seconds: int) -> str:
    time.sleep(seconds)
    return f"slept {seconds}s"
