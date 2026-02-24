from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.membership import Membership
from app.services.audit import write_audit_log


def _snapshot(ms: Membership) -> dict[str, Any]:
    return {"user_id": str(ms.user_id), "role": ms.role}


def add_member(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    user_id: UUID,
    role: str,
) -> Membership:
    exists = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    ).scalar_one_or_none()
    if exists is not None:
        raise ValueError("already a member")

    ms = Membership(user_id=user_id, workspace_id=workspace_id, role=role)
    db.add(ms)
    db.flush()

    write_audit_log(
        db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action="member.add",
        target_type="membership",
        target_id=ms.id,
        before=None,
        after=_snapshot(ms),
    )

    db.commit()
    db.refresh(ms)
    return ms


def remove_member(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    user_id: UUID,
) -> None:
    ms = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    ).scalar_one_or_none()
    if ms is None:
        raise KeyError("member not found")

    before = _snapshot(ms)
    target_id = ms.id

    db.execute(
        delete(Membership).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    )

    write_audit_log(
        db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action="member.remove",
        target_type="membership",
        target_id=target_id,
        before=before,
        after=None,
    )

    db.commit()
    return None


def change_role(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    user_id: UUID,
    role: str,
) -> Membership:
    ms = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id, Membership.user_id == user_id
        )
    ).scalar_one_or_none()
    if ms is None:
        raise KeyError("member not found")

    before = _snapshot(ms)

    ms.role = role

    write_audit_log(
        db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action="member.change_role",
        target_type="membership",
        target_id=ms.id,
        before=before,
        after=_snapshot(ms),
    )

    db.commit()
    db.refresh(ms)
    return ms
