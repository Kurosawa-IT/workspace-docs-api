from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, HTTPException, Path, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import rbac
from app.core.log_context import user_id_var, workspace_id_var
from app.core.tokens import decode_access_token
from app.db.session import get_db
from app.models.membership import Membership
from app.models.user import User
from app.models.workspace import Workspace

_bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,  # noqa: B008
    cred: HTTPAuthorizationCredentials | None = Depends(_bearer),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> User:
    if cred is None or cred.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(cred.credentials)
    except ValueError as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from err

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    stmt = select(User).where(User.id == UUID(user_id))
    user = db.execute(stmt).scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_var.set(str(user.id))
    request.state.user_id = str(user.id)

    return user


def get_current_workspace(
    workspace_id: UUID = Path(...),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> Workspace:
    ws = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    membership = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user.id,
        )
    ).scalar_one_or_none()
    if membership is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    workspace_id_var.set(str(workspace_id))

    return ws


@dataclass(frozen=True)
class WorkspaceContext:
    user: User
    workspace: Workspace
    membership: Membership


def get_workspace_context(
    request: Request,  # noqa: B008
    workspace_id: UUID = Path(...),  # noqa: B008
    user: User = Depends(get_current_user),  # noqa: B008
    db: Session = Depends(get_db),  # noqa: B008
) -> WorkspaceContext:
    ws = db.execute(select(Workspace).where(Workspace.id == workspace_id)).scalar_one_or_none()
    if ws is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    ms = db.execute(
        select(Membership).where(
            Membership.workspace_id == workspace_id,
            Membership.user_id == user.id,
        )
    ).scalar_one_or_none()
    if ms is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")

    workspace_id_var.set(str(workspace_id))
    request.state.workspace_id = str(workspace_id)

    return WorkspaceContext(user=user, workspace=ws, membership=ms)


def require(action: str):
    def _dep(ctx: WorkspaceContext = Depends(get_workspace_context)) -> WorkspaceContext:  # noqa: B008
        if not rbac.can(ctx.membership.role, action):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return ctx

    return _dep
