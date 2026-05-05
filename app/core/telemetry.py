from app.config import Settings


def configure_telemetry(settings: Settings, app=None) -> None:
    if not settings.otel_enabled:
        return
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    except ImportError:
        return
    if app is not None:
        FastAPIInstrumentor.instrument_app(app)
