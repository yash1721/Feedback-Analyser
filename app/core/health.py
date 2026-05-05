from sqlalchemy import text

from app.config import Settings
from app.db.session import get_engine


def liveness_status(settings: Settings) -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
    }


def readiness_status(settings: Settings) -> dict:
    components = {
        "database": _check_database(),
        "redis": _check_redis(settings),
        "qdrant": _check_qdrant(settings),
    }
    overall = "ready" if all(component["status"] == "ok" for component in components.values()) else "not_ready"
    return {
        "status": overall,
        "service": settings.app_name,
        "environment": settings.environment,
        "components": components,
    }


def _check_database() -> dict:
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "error_code": "database_unavailable", "error_message": str(exc)}


def _check_redis(settings: Settings) -> dict:
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=1, socket_timeout=1)
        client.ping()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "error_code": "redis_unavailable", "error_message": str(exc)}


def _check_qdrant(settings: Settings) -> dict:
    if settings.vector_provider != "qdrant":
        return {"status": "skipped", "reason": "vector_provider is not qdrant"}
    try:
        from qdrant_client import QdrantClient

        client = QdrantClient(url=settings.qdrant_url, timeout=2)
        client.get_collections()
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "error_code": "qdrant_unavailable", "error_message": str(exc)}
