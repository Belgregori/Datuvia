from uuid import UUID
from pydantic import BaseModel

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceResponse(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True