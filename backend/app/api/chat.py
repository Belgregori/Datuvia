from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlmodel import Session

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_session
from app.services.retrieval import answer_from_chunks, search_chunks

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    top_k: int = Field(default=4, ge=1, le=10)


class SourceRead(BaseModel):
    document_id: int
    title: str
    chunk_index: int
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
    question = body.message.strip()
    if not question:
        raise HTTPException(status_code=400, detail="La pregunta está vacía")

    chunks = search_chunks(session, user.id, question, body.top_k)
    answer = answer_from_chunks(question, chunks)
    return ChatResponse(
        answer=answer,
        sources=[
            SourceRead(
                document_id=chunk.document_id,
                title=chunk.title,
                chunk_index=chunk.chunk_index,
                score=round(chunk.score, 4),
                excerpt=chunk.content[:280],
            )
            for chunk in chunks
        ],
    )
