from pydantic import BaseModel

class WorkspaceCreate(BaseModel):
    name: str

class WorkspaceResponse(BaseModel):
    id: str
    name: str

    class Config:
        from_attributes = True