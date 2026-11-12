from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.core.security import get_current_user
from app.db.models import User, Workspace
from app.db.session import get_session
from app.schemas.workspace import WorkspaceCreate, WorkspaceResponse

router = APIRouter(prefix="/workspaces", tags=["workspaces"])


@router.get("", response_model=list[WorkspaceResponse])
def list_workspaces(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    return session.exec(
        select(Workspace).where(Workspace.owner_id == user.id).order_by(Workspace.created_at.desc())
    ).all()


@router.post("", response_model=WorkspaceResponse, status_code=201)
def create_workspace(
    body: WorkspaceCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")

    workspace = Workspace(name=name, owner_id=user.id)
    session.add(workspace)
    session.commit()
    session.refresh(workspace)
    return workspace


@router.delete("/{workspace_id}", status_code=204)
def delete_workspace(
    workspace_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
):
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")

    session.delete(workspace)
    session.commit()