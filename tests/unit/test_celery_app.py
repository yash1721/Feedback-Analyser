from app.workers.celery_app import celery_app


def test_celery_worker_pool_is_configured() -> None:
    assert celery_app.conf.worker_pool in {"solo", "prefork"}
