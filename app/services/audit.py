from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.request_id import request_id_var
from app.models.audit_log import AuditLog


def write_audit_log(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID | None,
    action: str,
    target_type: str,
    target_id: UUID | None,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    log = AuditLog(
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        before=before,
        after=after,
        request_id=request_id_var.get(),
    )
    db.add(log)
