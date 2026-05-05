from fastapi import APIRouter, Header
from fastapi.responses import Response

from app.config import get_settings
from app.core.auth import authenticate_api_key
from app.core.metrics import metrics_response

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def get_metrics(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> Response:
    settings = get_settings()
    if settings.metrics_auth_required:
        authenticate_api_key(x_api_key, settings)
    content, content_type = metrics_response()
    return Response(content=content, media_type=content_type)
