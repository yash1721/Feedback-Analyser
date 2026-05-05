from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import (
    analysis_routes,
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
    ticket_routes,
    workflow_routes,
)
from app.config import get_settings
from app.core.exceptions import FeedbackIQError
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.core.responses import error_response
from app.core.telemetry import configure_telemetry
from app.middleware.metrics import HttpMetricsMiddleware


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings)
    application = FastAPI(title=settings.app_name, debug=settings.debug, version="0.1.0")
    application.add_middleware(HttpMetricsMiddleware)
    application.add_middleware(RequestIdMiddleware)
    configure_telemetry(settings, application)
    application.include_router(analysis_routes.router, prefix=settings.api_v1_prefix)
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

    return application


app = create_app()
