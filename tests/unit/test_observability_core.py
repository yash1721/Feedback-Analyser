import json
import logging

from app.config import Settings
from app.core.health import liveness_status, readiness_status
from app.core.logging import JsonLogFormatter
from app.core.redaction import redact_text_preview


def test_redact_text_preview_masks_email_and_phone():
    result = redact_text_preview("Email test@example.com or call +1 555 123 4567 for details.", max_length=200)

    assert "test@example.com" not in result["preview"]
    assert "555 123 4567" not in result["preview"]
    assert "[REDACTED_EMAIL]" in result["preview"]
    assert result["text_hash"]


def test_json_log_formatter_includes_service_environment_and_extra_fields():
    formatter = JsonLogFormatter(service_name="FeedbackIQ", environment="test")
    record = logging.LogRecord(
        name="test.logger",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="hello",
        args=(),
        exc_info=None,
    )
    record.feedback_id = 123
    record.correlation_id = "corr-1"

    payload = json.loads(formatter.format(record))

    assert payload["service"] == "FeedbackIQ"
    assert payload["environment"] == "test"
    assert payload["correlation_id"] == "corr-1"
    assert payload["feedback_id"] == 123


def test_liveness_status_is_ok():
    result = liveness_status(Settings(environment="test"))

    assert result["status"] == "ok"
    assert result["service"] == "FeedbackIQ"


def test_readiness_status_aggregates_components(monkeypatch):
    monkeypatch.setattr("app.core.health._check_database", lambda: {"status": "ok"})
    monkeypatch.setattr("app.core.health._check_redis", lambda settings: {"status": "ok"})
    monkeypatch.setattr("app.core.health._check_qdrant", lambda settings: {"status": "ok"})

    result = readiness_status(Settings(environment="test"))

    assert result["status"] == "ready"
    assert result["components"]["database"]["status"] == "ok"
