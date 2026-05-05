import hashlib
from dataclasses import dataclass

from fastapi import Header, Request

from app.config import Settings, get_settings
from app.core.exceptions import FeedbackIQError


class AuthenticationError(FeedbackIQError):
    status_code = 401
    code = "authentication_failed"


class AuthorizationError(FeedbackIQError):
    status_code = 403
    code = "authorization_failed"


@dataclass(frozen=True)
class ApiKeyPrincipal:
    key_id: str
    role: str


ROLE_PERMISSIONS = {
    "admin": {"*"},
    "analyst": {
        "feedback:read",
        "feedback:write",
        "ingestion:write",
        "knowledge:read",
        "knowledge:write",
        "retrieval:search",
        "analysis:run",
        "analysis:read",
        "analytics:read",
    },
    "reviewer": {
        "workflow:write",
        "ticket:read",
        "ticket:write",
        "review:read",
        "review:write",
    },
    "service": {
        "processing:write",
        "processing:read",
        "evaluation:read",
        "evaluation:run",
        "retrieval:search",
        "analysis:run",
        "analytics:read",
    },
}


def parse_api_keys(settings: Settings) -> dict[str, ApiKeyPrincipal]:
    parsed: dict[str, ApiKeyPrincipal] = {}
    if not settings.api_keys.strip():
        return parsed
    for item in settings.api_keys.split(","):
        value = item.strip()
        if not value:
            continue
        if ":" in value:
            key, role = value.split(":", maxsplit=1)
        else:
            key, role = value, "admin"
        key = key.strip()
        role = role.strip() or "admin"
        if key:
            parsed[key] = ApiKeyPrincipal(key_id=api_key_id(key), role=role)
    return parsed


def api_key_id(api_key: str) -> str:
    return hashlib.sha256(api_key.encode("utf-8")).hexdigest()[:12]


def authenticate_api_key(api_key: str | None, settings: Settings | None = None) -> ApiKeyPrincipal | None:
    settings = settings or get_settings()
    if not settings.auth_enabled:
        return ApiKeyPrincipal(key_id="auth-disabled", role="admin")
    if not api_key:
        raise AuthenticationError("API key is required.")
    principal = parse_api_keys(settings).get(api_key)
    if principal is None:
        raise AuthenticationError("API key is invalid.")
    return principal


def has_permission(principal: ApiKeyPrincipal, permission: str) -> bool:
    permissions = ROLE_PERMISSIONS.get(principal.role, set())
    return "*" in permissions or permission in permissions


def require_permission(permission: str):
    def dependency(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ) -> ApiKeyPrincipal | None:
        principal = authenticate_api_key(x_api_key)
        if principal is None:
            return None
        request.state.api_key_id = principal.key_id
        request.state.api_role = principal.role
        if not has_permission(principal, permission):
            raise AuthorizationError("API key role does not allow this action.", {"permission": permission})
        return principal

    return dependency
