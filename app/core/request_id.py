import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.correlation import new_correlation_id, reset_correlation_id, set_correlation_id

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        request_id = request.headers.get("X-Correlation-ID") or request.headers.get("X-Request-ID") or new_correlation_id()
        token = set_correlation_id(request_id)
        request.state.request_id = request_id
        request.state.correlation_id = request_id
        logger.info("HTTP request started", extra={"method": request.method, "path": request.url.path})
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Correlation-ID"] = request_id
            logger.info(
                "HTTP request completed",
                extra={"method": request.method, "path": request.url.path, "status_code": response.status_code},
            )
            return response
        finally:
            reset_correlation_id(token)
