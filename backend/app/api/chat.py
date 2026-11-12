from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.models import User, Workspace
from app.db.session import get_session
from app.services.rag_service import generate_answer
from app.services.retrieval import search_chunks

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    workspace_id: UUID
    question: str = Field(min_length=1, max_length=4000)


class SourceRead(BaseModel):
    document_id: UUID
    title: str
    page_number: int | None
    score: float
    excerpt: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceRead]


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="La pregunta está vacía")

    workspace = session.get(Workspace, body.workspace_id)
    if workspace is None or workspace.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")

    chunks = search_chunks(session, body.workspace_id, question)
    answer = generate_answer(question, chunks)
    return ChatResponse(
        answer=answer,
        sources=[
            SourceRead(
                document_id=chunk.document_id,
                title=chunk.title,
                page_number=chunk.page_number,
                score=round(chunk.score, 4),
                excerpt=chunk.content[:280],
            )
            for chunk in chunks
        ],
    )
