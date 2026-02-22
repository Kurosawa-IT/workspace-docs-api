from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import WorkspaceContext, get_current_user, get_current_workspace, require
from app.core import rbac
from app.db.session import get_db
from app.models.membership import Membership
from app.models.user import User
from app.models.workspace import Workspace
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
