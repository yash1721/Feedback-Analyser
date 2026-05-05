from fastapi import APIRouter, Header

from app.config import get_settings
from app.core.auth import authenticate_api_key
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
def ready_check(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> dict:
    settings = get_settings()
    if settings.ready_auth_required:
        authenticate_api_key(x_api_key, settings)
    return success_response(data=readiness_status(get_settings()))
