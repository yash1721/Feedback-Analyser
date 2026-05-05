from fastapi import APIRouter

from app.config import get_settings
from app.core.health import liveness_status, readiness_status
from app.core.responses import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check() -> dict:
    settings = get_settings()
    return success_response(data=liveness_status(settings))


@router.get("/live")
def live_check() -> dict:
    return success_response(data=liveness_status(get_settings()))


@router.get("/ready")
def ready_check() -> dict:
    return success_response(data=readiness_status(get_settings()))
