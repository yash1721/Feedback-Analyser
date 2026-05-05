from datetime import datetime

from pydantic import BaseModel


class SecurityAuditLogRead(BaseModel):
    id: int
    event_type: str
    severity: str
    actor_type: str
    actor_id: str | None
    correlation_id: str | None
    path: str | None
    method: str | None
    decision: str
    reason: str | None
    metadata_json: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class SecurityAuditLogListResponse(BaseModel):
    items: list[SecurityAuditLogRead]
    total: int
    limit: int
    offset: int
