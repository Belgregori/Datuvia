import json
import time
from collections.abc import Iterator
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlmodel import Session, select

from app.core.security import get_current_user
from app.db.models import ChatMessage, ChatSession, User, Workspace
from app.db.session import engine, get_session
from app.services.rag_service import estimate_tokens, iter_answer, rewrite_query
from app.services.retrieval import rerank_chunks, search_chunks

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatRequest(BaseModel):
    workspace_id: UUID
    question: str = Field(min_length=1, max_length=4000)
    session_id: UUID | None = None


class SourceRead(BaseModel):
    document_id: UUID
    title: str
    page_number: int | None
    score: float
    excerpt: str


class SessionRead(BaseModel):
    id: UUID
    title: str
    updated_at: datetime


class MessageRead(BaseModel):
    id: UUID
    role: str
    content: str
    tokens_used: int | None
    latency_ms: int | None
    created_at: datetime


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def _owned_workspace(session: Session, workspace_id: UUID, user: User) -> Workspace:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")
    return workspace


def _recent_history(session: Session, session_id: UUID) -> list[tuple[str, str]]:
    rows = session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(5)
    ).all()
    return [(row.role, row.content) for row in reversed(rows)]


def _save_turn(
    session_id: UUID,
    question: str,
    answer: str,
    latency_ms: int,
    tokens_used: int,
) -> None:
    with Session(engine) as db:
        chat_session = db.get(ChatSession, session_id)
        if chat_session is None:
            return
        now = datetime.utcnow()
        db.add(ChatMessage(
            session_id=session_id,
            role="user",
            content=question,
            tokens_used=estimate_tokens(question),
            created_at=now,
        ))
        db.add(ChatMessage(
            session_id=session_id,
            role="assistant",
            content=answer,
            tokens_used=tokens_used,
            latency_ms=latency_ms,
            created_at=now,
        ))
        chat_session.updated_at = now
        db.add(chat_session)
        db.commit()


@router.get("/sessions/{workspace_id}", response_model=list[SessionRead])
def list_sessions(
    workspace_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChatSession]:
    _owned_workspace(session, workspace_id, user)
    return list(session.exec(
        select(ChatSession)
        .where(ChatSession.workspace_id == workspace_id)
        .order_by(ChatSession.updated_at.desc())
    ).all())


@router.get("/sessions/{session_id}/messages", response_model=list[MessageRead])
def list_messages(
    session_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[ChatMessage]:
    chat_session = session.get(ChatSession, session_id)
    if chat_session is None:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    _owned_workspace(session, chat_session.workspace_id, user)
    return list(session.exec(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    ).all())


@router.post("")
def chat(
    body: ChatRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> StreamingResponse:
    question = body.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="La pregunta está vacía")

    _owned_workspace(session, body.workspace_id, user)
    if body.session_id is None:
        chat_session = ChatSession(workspace_id=body.workspace_id, title=question[:80])
        session.add(chat_session)
        session.commit()
        session.refresh(chat_session)
        history: list[tuple[str, str]] = []
    else:
        chat_session = session.get(ChatSession, body.session_id)
        if chat_session is None or chat_session.workspace_id != body.workspace_id:
            raise HTTPException(status_code=404, detail="Conversación no encontrada")
        history = _recent_history(session, chat_session.id)

    started = time.perf_counter()
    search_query = rewrite_query(question, history)
    raw_chunks = search_chunks(session, body.workspace_id, search_query, top_k=8)
    chunks = rerank_chunks(raw_chunks)[:4]
    sources = [
        SourceRead(
            document_id=chunk.document_id,
            title=chunk.title,
            page_number=chunk.page_number,
            score=round(chunk.score, 4),
            excerpt=chunk.content[:280],
        ).model_dump(mode="json")
        for chunk in chunks
    ]
    usage: dict = {"tokens": None}
    session_id = chat_session.id

    def events() -> Iterator[str]:
        yield _sse({"type": "session", "session_id": str(session_id)})
        yield _sse({"type": "sources", "sources": sources})
        parts: list[str] = []
        if raw_chunks and not chunks:
            parts.append("No encontré fragmentos con suficiente similitud para responder con evidencia.")
            yield _sse({"type": "token", "text": parts[0]})
        else:
            for token in iter_answer(question, chunks, history, usage):
                parts.append(token)
                yield _sse({"type": "token", "text": token})
        answer = "".join(parts)
        latency_ms = int((time.perf_counter() - started) * 1000)
        tokens_used = usage["tokens"] or (estimate_tokens(question) + estimate_tokens(answer))
        _save_turn(session_id, question, answer, latency_ms, tokens_used)
        yield _sse({"type": "done", "latency_ms": latency_ms, "tokens_used": tokens_used})

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
