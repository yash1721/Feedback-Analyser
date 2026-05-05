from fastapi import APIRouter
from fastapi.responses import Response

from app.core.metrics import metrics_response

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
def get_metrics() -> Response:
    content, content_type = metrics_response()
    return Response(content=content, media_type=content_type)
