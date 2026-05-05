from app.config import Settings


class SecurityConfigError(RuntimeError):
    pass


def validate_security_config(settings: Settings) -> None:
    if settings.environment != "production":
        return
    if not settings.auth_enabled:
        raise SecurityConfigError("AUTH_ENABLED must be true in production.")
    if not settings.api_keys.strip():
        raise SecurityConfigError("API_KEYS must be configured in production.")
    insecure_values = {"changeme", "local-admin-key", "dev-key", "test-key", "secret"}
    configured_keys = [item.split(":", maxsplit=1)[0].strip() for item in settings.api_keys.split(",")]
    if any(key in insecure_values for key in configured_keys):
        raise SecurityConfigError("Production API keys must not use default placeholder values.")
    if not settings.pii_redaction_enabled:
        raise SecurityConfigError("PII_REDACTION_ENABLED must be true in production.")
