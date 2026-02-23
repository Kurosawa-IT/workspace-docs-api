from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql import and_

from app.api.deps import WorkspaceContext, get_current_user, get_current_workspace, require
from app.core import rbac
from app.db.session import get_db
from app.models.document import Document
from app.models.membership import Membership
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.document import DocumentCreateIn, DocumentListOut, DocumentOut, DocumentUpdateIn
from app.schemas.membership import MemberOut, MemberRoleUpdateIn
from app.schemas.workspace import WorkspaceCreateIn, WorkspaceOut

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.post("", response_model=WorkspaceOut, status_code=status.HTTP_201_CREATED)
def create_workspace(
    payload: WorkspaceCreateIn,
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> WorkspaceOut:
    ws = Workspace(name=payload.name)
    db.add(ws)
    db.flush()

    membership = Membership(
        user_id=user.id,
        workspace_id=ws.id,
        role="owner",
    )
    db.add(membership)

    db.commit()
    db.refresh(ws)
    return ws


@router.get("", response_model=list[WorkspaceOut])
def list_workspaces(
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[WorkspaceOut]:
    stmt = (
        select(Workspace)
        .join(Membership, Membership.workspace_id == Workspace.id)
        .where(Membership.user_id == user.id)
        .order_by(Workspace.created_at.desc())
    )
    items = db.execute(stmt).scalars().all()
    return list(items)


@router.get("/{workspace_id}", response_model=WorkspaceOut)
def get_workspace(ws: Workspace = Depends(get_current_workspace)) -> WorkspaceOut:  # noqa: B008
    return ws


@router.get("/{workspace_id}/members", response_model=list[MemberOut])
def list_members(
    ctx: WorkspaceContext = Depends(require(rbac.A_MEMBER_LIST)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> list[MemberOut]:
    stmt = (
        select(Membership.user_id, User.email, Membership.role)
        .join(User, User.id == Membership.user_id)
        .where(Membership.workspace_id == ctx.workspace.id)
        .order_by(Membership.created_at.asc())
    )
    rows = db.execute(stmt).all()
    return [MemberOut(user_id=r[0], email=r[1], role=r[2]) for r in rows]


@router.delete("/{workspace_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_member(
    user_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_MEMBER_REMOVE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Response:
    if user_id == ctx.user.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot remove self")

    stmt = select(Membership).where(
        Membership.workspace_id == ctx.workspace.id,
        Membership.user_id == user_id,
    )
    ms = db.execute(stmt).scalar_one_or_none()
    if ms is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    db.delete(ms)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberOut)
def change_member_role(
    user_id: UUID,  # noqa: B008
    payload: MemberRoleUpdateIn,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_MEMBER_CHANGE_ROLE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> MemberOut:
    ms = db.execute(
        select(Membership).where(
            Membership.workspace_id == ctx.workspace.id,
            Membership.user_id == user_id,
        )
    ).scalar_one_or_none()
    if ms is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    ms.role = payload.role
    db.commit()

    email = db.execute(select(User.email).where(User.id == user_id)).scalar_one()
    return MemberOut(user_id=user_id, email=email, role=ms.role)


@router.post(
    "/{workspace_id}/docs", response_model=DocumentOut, status_code=status.HTTP_201_CREATED
)
def create_document(
    payload: DocumentCreateIn,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_CREATE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    doc = Document(
        workspace_id=ctx.workspace.id,
        title=payload.title,
        body=payload.body,
        status="draft",
        tags=payload.tags,
        created_by=ctx.user.id,
        updated_by=ctx.user.id,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


@router.get("/{workspace_id}/docs/{doc_id}", response_model=DocumentOut)
def get_document(
    doc_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_READ)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    stmt = select(Document).where(
        Document.id == doc_id,
        Document.workspace_id == ctx.workspace.id,
    )
    doc = db.execute(stmt).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    return doc


@router.patch("/{workspace_id}/docs/{doc_id}", response_model=DocumentOut)
def update_document(
    doc_id: UUID,  # noqa: B008
    payload: DocumentUpdateIn,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_UPDATE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    doc = db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.workspace_id == ctx.workspace.id,
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    changed = False
    if payload.title is not None:
        doc.title = payload.title
        changed = True
    if payload.body is not None:
        doc.body = payload.body
        changed = True
    if payload.tags is not None:
        doc.tags = payload.tags
        changed = True

    if not changed:
        return doc

    doc.updated_by = ctx.user.id
    doc.updated_at = datetime.now(UTC)

    db.commit()
    db.refresh(doc)
    return doc


@router.delete("/{workspace_id}/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_DELETE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    doc = db.execute(
        select(Document.id).where(
            Document.id == doc_id,
            Document.workspace_id == ctx.workspace.id,
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    db.execute(
        delete(Document).where(
            Document.id == doc_id,
            Document.workspace_id == ctx.workspace.id,
        )
    )
    db.commit()
    return None


@router.get("/{workspace_id}/docs", response_model=DocumentListOut)
def list_documents(
    page: int = Query(1, ge=1),  # noqa: B008
    page_size: int = Query(20, ge=1, le=100),  # noqa: B008
    sort: str = Query("updated_at_desc", pattern="^updated_at_desc$"),  # noqa: B008
    status: str | None = Query(None, pattern="^(draft|published|archived)$"),  # noqa: B008
    tag: str | None = Query(None, min_length=1, max_length=50),  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_READ)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
    query: str | None = Query(None, min_length=1, max_length=200),  # noqa: B008
) -> DocumentListOut:
    filters = [Document.workspace_id == ctx.workspace.id]
    if status is not None:
        filters.append(Document.status == status)
    if tag is not None:
        filters.append(Document.tags.any(tag))
    if query is not None:
        filters.append(Document.title.ilike(f"%{query}%"))

    total = db.execute(
        select(func.count()).select_from(Document).where(and_(*filters))
    ).scalar_one()

    order_by = (Document.updated_at.desc(), Document.id.desc())

    stmt = (
        select(Document)
        .where(and_(*filters))
        .order_by(*order_by)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(stmt).scalars().all()

    return DocumentListOut(
        items=[DocumentOut.model_validate(d) for d in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{workspace_id}/docs/{doc_id}/publish", response_model=DocumentOut)
def publish_document(
    doc_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_PUBLISH)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    doc = db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.workspace_id == ctx.workspace.id,
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.status != "draft":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid transition")

    now = datetime.now(UTC)
    doc.status = "published"
    doc.published_at = now
    doc.archived_at = None
    doc.updated_by = ctx.user.id
    doc.updated_at = now

    db.commit()
    db.refresh(doc)
    return doc


@router.post("/{workspace_id}/docs/{doc_id}/archive", response_model=DocumentOut)
def archive_document(
    doc_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_ARCHIVE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    doc = db.execute(
        select(Document).where(
            Document.id == doc_id,
            Document.workspace_id == ctx.workspace.id,
        )
    ).scalar_one_or_none()
    if doc is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    if doc.status != "published":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Invalid transition")

    now = datetime.now(UTC)
    doc.status = "archived"
    doc.archived_at = now
    doc.updated_by = ctx.user.id
    doc.updated_at = now

    db.commit()
    db.refresh(doc)
    return doc
