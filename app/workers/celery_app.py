import os

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "feedbackiq",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    task_track_started=True,
    timezone="UTC",
    worker_pool=os.getenv("CELERY_WORKER_POOL", "solo" if os.name == "nt" else "prefork"),
)
