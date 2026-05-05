from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.config import Settings
from app.core.auth import api_key_id
from app.core.metrics import RATE_LIMITED_REQUESTS_TOTAL
from app.core.rate_limit import InMemoryRateLimiter
from app.core.responses import error_response


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, *, settings: Settings, limiter: InMemoryRateLimiter | None = None) -> None:
        super().__init__(app)
        self.settings = settings
        self.limiter = limiter or InMemoryRateLimiter()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.settings.rate_limit_enabled or request.url.path in {"/metrics"} or request.url.path.startswith("/api/v1/health"):
            return await call_next(request)
        identity = request.headers.get("X-API-Key")
        key = f"api:{api_key_id(identity)}" if identity else f"ip:{request.client.host if request.client else 'unknown'}"
        limit = self.settings.rate_limit_requests_per_minute + self.settings.rate_limit_burst
        decision = self.limiter.check(key, limit=limit)
        if not decision.allowed:
            RATE_LIMITED_REQUESTS_TOTAL.labels(endpoint_group=_endpoint_group(request.url.path)).inc()
            return JSONResponse(
                status_code=429,
                content=error_response(
                    "rate_limited",
                    "Rate limit exceeded.",
                    {"retry_after_seconds": decision.retry_after_seconds},
                ),
                headers={"Retry-After": str(decision.retry_after_seconds)},
            )
        return await call_next(request)


def _endpoint_group(path: str) -> str:
    parts = [part for part in path.split("/") if part]
    if len(parts) >= 3 and parts[0] == "api" and parts[1] == "v1":
        return parts[2]
    return parts[0] if parts else "root"
