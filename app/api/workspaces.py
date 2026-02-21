from fastapi import APIRouter, Depends, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.membership import Membership
from app.models.user import User
from app.models.workspace import Workspace
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
