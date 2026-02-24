from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    actor_user_id: UUID | None
    action: str
    target_type: str
    target_id: UUID | None
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    request_id: str | None
    ip: str | None
    user_agent: str | None
    created_at: datetime


class AuditLogListOut(BaseModel):
    items: list[AuditLogOut]
    total: int
    page: int
    page_size: int
