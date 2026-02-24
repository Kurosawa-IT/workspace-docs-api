from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.document import Document
from app.services.audit import write_audit_log


def _snapshot(doc: Document) -> dict[str, Any]:
    return {"title": doc.title, "status": doc.status, "tags": doc.tags}


def create_document(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    title: str,
    body: str,
    tags: list[str],
) -> Document:
    doc = Document(
        workspace_id=workspace_id,
        title=title,
        body=body,
        status="draft",
        tags=tags,
        created_by=actor_user_id,
        updated_by=actor_user_id,
    )
    db.add(doc)
    db.flush()  # doc.id を確定

    write_audit_log(
        db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action="doc.create",
        target_type="document",
        target_id=doc.id,
        before=None,
        after=_snapshot(doc),
    )

    db.commit()
    db.refresh(doc)
    return doc


def update_document(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    doc_id: UUID,
    title: str | None = None,
    body: str | None = None,
    tags: list[str] | None = None,
) -> Document:
    doc = db.execute(
        select(Document).where(Document.id == doc_id, Document.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if doc is None:
        raise KeyError("document not found")

    before = _snapshot(doc)

    changed = False
    if title is not None:
        doc.title = title
        changed = True
    if body is not None:
        doc.body = body
        changed = True
    if tags is not None:
        doc.tags = tags
        changed = True

    if changed:
        now = datetime.now(UTC)
        doc.updated_by = actor_user_id
        doc.updated_at = now

    write_audit_log(
        db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action="doc.update",
        target_type="document",
        target_id=doc.id,
        before=before,
        after=_snapshot(doc),
    )

    db.commit()
    db.refresh(doc)
    return doc


def delete_document(
    db: Session,
    *,
    workspace_id: UUID,
    actor_user_id: UUID,
    doc_id: UUID,
) -> None:
    doc = db.execute(
        select(Document).where(Document.id == doc_id, Document.workspace_id == workspace_id)
    ).scalar_one_or_none()
    if doc is None:
        raise KeyError("document not found")

    before = _snapshot(doc)

    db.execute(delete(Document).where(Document.id == doc_id, Document.workspace_id == workspace_id))

    write_audit_log(
        db,
        workspace_id=workspace_id,
        actor_user_id=actor_user_id,
        action="doc.delete",
        target_type="document",
        target_id=doc_id,
        before=before,
        after=None,
    )

    db.commit()
    return None
