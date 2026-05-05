from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.domain.security.models import SecurityAuditLog


class SecurityAuditRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, **fields) -> SecurityAuditLog:
        event = SecurityAuditLog(**fields)
        self.session.add(event)
        self.session.flush()
        self.session.refresh(event)
        return event

    def list(
        self,
        *,
        limit: int,
        offset: int,
        event_type: str | None = None,
        severity: str | None = None,
        decision: str | None = None,
    ) -> tuple[list[SecurityAuditLog], int]:
        statement = select(SecurityAuditLog)
        if event_type is not None:
            statement = statement.where(SecurityAuditLog.event_type == event_type)
        if severity is not None:
            statement = statement.where(SecurityAuditLog.severity == severity)
        if decision is not None:
            statement = statement.where(SecurityAuditLog.decision == decision)
        total = self.session.scalar(select(func.count()).select_from(statement.subquery())) or 0
        events = list(
            self.session.scalars(
                statement.order_by(SecurityAuditLog.created_at.desc(), SecurityAuditLog.id.desc())
                .limit(limit)
                .offset(offset)
            )
        )
        return events, total
