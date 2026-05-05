from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import (
    analysis_routes,
    analytics_routes,
    evaluation_routes,
    feedback_records_routes,
    feedback_routes,
    health_routes,
    ingestion_routes,
    knowledge_routes,
    metrics_routes,
    ocr_routes,
    processing_routes,
    review_routes,
    retrieval_routes,
    security_routes,
    ticket_routes,
    workflow_routes,
)
from app.config import get_settings
from app.core.auth import AuthenticationError
from app.core.exceptions import FeedbackIQError
from app.core.logging import configure_logging
from app.core.metrics import AUTH_FAILURES_TOTAL
from app.core.request_id import RequestIdMiddleware
from app.core.responses import error_response
from app.core.security_config import validate_security_config
from app.core.telemetry import configure_telemetry
from app.db.session import get_session_factory
from app.domain.security.repository import SecurityAuditRepository
from app.domain.security.service import SecurityAuditService
from app.middleware.metrics import HttpMetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    validate_security_config(settings)
    configure_logging(settings)
    application = FastAPI(title=settings.app_name, debug=settings.debug, version="0.1.0")
    application.add_middleware(HttpMetricsMiddleware)
    application.add_middleware(RateLimitMiddleware, settings=settings)
    application.add_middleware(RequestIdMiddleware)
    configure_telemetry(settings, application)
    application.include_router(analysis_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(analytics_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(evaluation_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(health_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(ocr_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(ingestion_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(knowledge_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(metrics_routes.router)
    application.include_router(feedback_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(feedback_records_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(processing_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(retrieval_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(workflow_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(ticket_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(review_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(security_routes.router, prefix=settings.api_v1_prefix)

    @application.exception_handler(FeedbackIQError)
    async def feedbackiq_exception_handler(request: Request, exc: FeedbackIQError) -> JSONResponse:
        import logging

        logging.getLogger(__name__).warning(
            "Application error",
            extra={
                "error_code": exc.code,
                "status_code": exc.status_code,
                "path": request.url.path,
                "method": request.method,
            },
        )
        if isinstance(exc, AuthenticationError):
            AUTH_FAILURES_TOTAL.labels(reason=exc.code).inc()
            _record_security_event(
                event_type="auth_failed",
                severity="MEDIUM",
                decision="BLOCKED",
                reason=exc.message,
                path=request.url.path,
                method=request.method,
            )
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, exc.details),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        import logging

        logging.getLogger(__name__).warning(
            "Request validation error",
            extra={"error_code": "validation_error", "status_code": 422, "path": request.url.path, "method": request.method},
        )
        return JSONResponse(
            status_code=422,
            content=error_response("validation_error", "Invalid request payload.", exc.errors()),
        )

    @application.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        import logging

        logging.getLogger(__name__).exception(
            "Unhandled application error",
            extra={
                "error_code": "internal_error",
                "status_code": 500,
                "path": request.url.path,
                "method": request.method,
                "exception_type": exc.__class__.__name__,
            },
        )
        return JSONResponse(
            status_code=500,
            content=error_response("internal_error", "Internal server error.", None),
        )

    return application


def _record_security_event(*, event_type: str, severity: str, decision: str, reason: str, path: str, method: str) -> None:
    try:
        with get_session_factory()() as session:
            SecurityAuditService(SecurityAuditRepository(session)).record_event(
                event_type=event_type,
                severity=severity,
                decision=decision,
                reason=reason,
                path=path,
                method=method,
            )
    except Exception:
        import logging

        logging.getLogger(__name__).exception("Security audit event could not be persisted")


app = create_app()
