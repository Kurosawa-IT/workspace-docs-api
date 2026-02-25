from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response, status
from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session
from starlette.responses import JSONResponse

from app.api.deps import WorkspaceContext, get_current_user, get_current_workspace, require
from app.core import rbac
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.document import Document
from app.models.job import Job
from app.models.membership import Membership
from app.models.user import User
from app.models.workspace import Workspace
from app.schemas.audit import AuditLogListOut, AuditLogOut
from app.schemas.document import DocumentCreateIn, DocumentListOut, DocumentOut, DocumentUpdateIn
from app.schemas.job import JobDetailOut, JobOut
from app.schemas.membership import MemberAddIn, MemberOut, MemberRoleUpdateIn
from app.schemas.workspace import WorkspaceCreateIn, WorkspaceOut
from app.services.documents import archive_document as svc_archive_document
from app.services.documents import create_document as svc_create_document
from app.services.documents import delete_document as svc_delete_document
from app.services.documents import publish_document as svc_publish_document
from app.services.documents import update_document as svc_update_document
from app.services.jobs import create_export_job
from app.services.memberships import add_member as svc_add_member
from app.services.memberships import change_role as svc_change_role
from app.services.memberships import remove_member as svc_remove_member
from app.tasks.export import run_export

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
        raise HTTPException(status_code=400, detail="Cannot remove yourself")

    try:
        svc_remove_member(
            db,
            workspace_id=ctx.workspace.id,
            actor_user_id=ctx.user.id,
            user_id=user_id,
        )
    except KeyError as err:
        raise HTTPException(status_code=404, detail="Member not found") from err

    return None


@router.patch("/{workspace_id}/members/{user_id}", response_model=MemberOut)
def change_member_role(
    user_id: UUID,  # noqa: B008
    payload: MemberRoleUpdateIn,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_MEMBER_CHANGE_ROLE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> MemberOut:
    try:
        ms = svc_change_role(
            db,
            workspace_id=ctx.workspace.id,
            actor_user_id=ctx.user.id,
            user_id=user_id,
            role=payload.role,
        )
    except KeyError as err:
        raise HTTPException(status_code=404, detail="Member not found") from err

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
    doc = svc_create_document(
        db,
        workspace_id=ctx.workspace.id,
        actor_user_id=ctx.user.id,
        title=payload.title,
        body=payload.body,
        tags=payload.tags,
    )
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
    try:
        doc = svc_update_document(
            db,
            workspace_id=ctx.workspace.id,
            actor_user_id=ctx.user.id,
            doc_id=doc_id,
            title=payload.title,
            body=payload.body,
            tags=payload.tags,
        )
    except KeyError as err:
        raise HTTPException(status_code=404, detail="Document not found") from err
    return doc


@router.delete("/{workspace_id}/docs/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    doc_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_DELETE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> None:
    try:
        svc_delete_document(
            db,
            workspace_id=ctx.workspace.id,
            actor_user_id=ctx.user.id,
            doc_id=doc_id,
        )
    except KeyError as err:
        raise HTTPException(status_code=404, detail="Document not found") from err
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
    try:
        doc = svc_publish_document(
            db,
            workspace_id=ctx.workspace.id,
            actor_user_id=ctx.user.id,
            doc_id=doc_id,
        )
    except KeyError as err:
        raise HTTPException(status_code=404, detail="Document not found") from err
    except ValueError as err:
        raise HTTPException(status_code=409, detail="Invalid transition") from err
    return doc


@router.post("/{workspace_id}/docs/{doc_id}/archive", response_model=DocumentOut)
def archive_document(
    doc_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_DOC_ARCHIVE)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> DocumentOut:
    try:
        doc = svc_archive_document(
            db,
            workspace_id=ctx.workspace.id,
            actor_user_id=ctx.user.id,
            doc_id=doc_id,
        )
    except KeyError as err:
        raise HTTPException(status_code=404, detail="Document not found") from err
    except ValueError as err:
        raise HTTPException(status_code=409, detail="Invalid transition") from err
    return doc


@router.post("/{workspace_id}/members", response_model=MemberOut, status_code=201)
def add_member(
    payload: MemberAddIn,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_MEMBER_ADD)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> MemberOut:
    try:
        ms = svc_add_member(
            db,
            workspace_id=ctx.workspace.id,
            actor_user_id=ctx.user.id,
            user_id=payload.user_id,
            role=payload.role,
        )
    except ValueError as err:
        raise HTTPException(status_code=409, detail="Already a member") from err

    email = db.execute(select(User.email).where(User.id == payload.user_id)).scalar_one()
    return MemberOut(user_id=payload.user_id, email=email, role=ms.role)


@router.get("/{workspace_id}/audit", response_model=AuditLogListOut)
def search_audit_logs(
    page: int = Query(1, ge=1),  # noqa: B008
    page_size: int = Query(20, ge=1, le=100),  # noqa: B008
    action: str | None = Query(None, max_length=100),  # noqa: B008
    actor: UUID | None = Query(None),  # noqa: B008
    from_: datetime | None = Query(None, alias="from"),  # noqa: B008
    to: datetime | None = Query(None),  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_AUDIT_READ)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> AuditLogListOut:
    filters = [AuditLog.workspace_id == ctx.workspace.id]

    if action is not None:
        filters.append(AuditLog.action == action)
    if actor is not None:
        filters.append(AuditLog.actor_user_id == actor)
    if from_ is not None:
        filters.append(AuditLog.created_at >= from_)
    if to is not None:
        filters.append(AuditLog.created_at <= to)

    where_clause = and_(*filters)

    total = db.execute(select(func.count()).select_from(AuditLog).where(where_clause)).scalar_one()

    stmt = (
        select(AuditLog)
        .where(where_clause)
        .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    items = db.execute(stmt).scalars().all()

    return AuditLogListOut(
        items=[AuditLogOut.model_validate(x) for x in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("/{workspace_id}/exports", response_model=JobOut)
def start_export(
    ctx: WorkspaceContext = Depends(require(rbac.A_EXPORT_CREATE)),  # noqa: B008
    idempotency_key: str = Header(..., alias="Idempotency-Key", min_length=1, max_length=200),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
):
    job, created = create_export_job(
        db,
        workspace_id=ctx.workspace.id,
        idempotency_key=idempotency_key,
        payload=None,
    )
    if created:
        run_export.delay(str(job.id))

    return JSONResponse(
        status_code=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        content=JobOut.model_validate(job).model_dump(mode="json"),
    )


@router.get("/{workspace_id}/jobs/{job_id}", response_model=JobDetailOut)
def get_job(
    job_id: UUID,  # noqa: B008
    ctx: WorkspaceContext = Depends(require(rbac.A_JOB_READ)),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> JobDetailOut:
    job = db.execute(
        select(Job).where(
            Job.id == job_id,
            Job.workspace_id == ctx.workspace.id,
        )
    ).scalar_one_or_none()

    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return job
