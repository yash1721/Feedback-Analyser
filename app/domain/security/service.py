from app.core.correlation import get_correlation_id
from app.domain.security.models import SecurityAuditLog
from app.domain.security.repository import SecurityAuditRepository


class SecurityAuditService:
    def __init__(self, repository: SecurityAuditRepository) -> None:
        self.repository = repository

    def record_event(
        self,
        *,
        event_type: str,
        severity: str,
        decision: str,
        reason: str | None = None,
        actor_type: str = "system",
        actor_id: str | None = None,
        path: str | None = None,
        method: str | None = None,
        metadata: dict | None = None,
        commit: bool = True,
    ) -> SecurityAuditLog:
        event = self.repository.create(
            event_type=event_type,
            severity=severity,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=get_correlation_id(),
            path=path,
            method=method,
            decision=decision,
            reason=reason,
            metadata_json=metadata,
        )
        if commit:
            self.repository.session.commit()
        return event

    def list_events(
        self,
        *,
        limit: int,
        offset: int,
        event_type: str | None = None,
        severity: str | None = None,
        decision: str | None = None,
    ) -> tuple[list[SecurityAuditLog], int]:
        return self.repository.list(limit=limit, offset=offset, event_type=event_type, severity=severity, decision=decision)
