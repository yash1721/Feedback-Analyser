from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.v1 import (
    feedback_records_routes,
    feedback_routes,
    health_routes,
    ingestion_routes,
    ocr_routes,
    processing_routes,
    retrieval_routes,
)
from app.config import get_settings
from app.core.exceptions import FeedbackIQError
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.core.responses import error_response


def create_app() -> FastAPI:
    configure_logging()
    settings = get_settings()
    application = FastAPI(title=settings.app_name, debug=settings.debug, version="0.1.0")
    application.add_middleware(RequestIdMiddleware)
    application.include_router(health_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(ocr_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(ingestion_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(feedback_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(feedback_records_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(processing_routes.router, prefix=settings.api_v1_prefix)
    application.include_router(retrieval_routes.router, prefix=settings.api_v1_prefix)

    @application.exception_handler(FeedbackIQError)
    async def feedbackiq_exception_handler(_: Request, exc: FeedbackIQError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(exc.code, exc.message, exc.details),
        )

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content=error_response("validation_error", "Invalid request payload.", exc.errors()),
        )

    return application


app = create_app()
