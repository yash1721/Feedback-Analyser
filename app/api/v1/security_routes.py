from fastapi import APIRouter, Depends, Query

from app.core.auth import require_permission
from app.core.responses import success_response
from app.dependencies import get_security_audit_service
from app.domain.security.schemas import SecurityAuditLogListResponse, SecurityAuditLogRead
from app.domain.security.service import SecurityAuditService

router = APIRouter(
    prefix="/security",
    tags=["security"],
    dependencies=[Depends(require_permission("security:audit:read"))],
)


@router.get("/audit-logs")
def list_security_audit_logs(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    event_type: str | None = None,
    severity: str | None = None,
    decision: str | None = None,
    service: SecurityAuditService = Depends(get_security_audit_service),
) -> dict:
    events, total = service.list_events(
        limit=limit,
        offset=offset,
        event_type=event_type,
        severity=severity,
        decision=decision,
    )
    response = SecurityAuditLogListResponse(
        items=[SecurityAuditLogRead.model_validate(event) for event in events],
        total=total,
        limit=limit,
        offset=offset,
    )
    return success_response(data=response.model_dump(mode="json"))
