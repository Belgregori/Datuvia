from dataclasses import dataclass

from sqlalchemy import text
from sqlmodel import Session

from app.services.embeddings import embed_texts


@dataclass
class RetrievedChunk:
    document_id: int
    title: str
    content: str
    chunk_index: int
    score: float


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def search_chunks(session: Session, owner_id: int, query: str, top_k: int = 4) -> list[RetrievedChunk]:
    embedding = embed_texts([query])[0]
    rows = session.execute(
        text(
            """
            SELECT c.document_id, d.title, c.content, c.chunk_index,
                   1 - (c.embedding <=> CAST(:embedding AS vector)) AS score
            FROM chunk c
            JOIN document d ON d.id = c.document_id
            WHERE d.owner_id = :owner_id
            ORDER BY c.embedding <=> CAST(:embedding AS vector)
            LIMIT :top_k
            """
        ),
        {
            "embedding": _vector_literal(embedding),
            "owner_id": owner_id,
            "top_k": top_k,
        },
    ).all()
    return [
        RetrievedChunk(
            document_id=row.document_id,
            title=row.title,
            content=row.content,
            chunk_index=row.chunk_index,
            score=float(row.score),
        )
        for row in rows
    ]


def answer_from_chunks(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "Todavía no hay documentos indexados para responder esa pregunta."

    context = "\n\n".join(
        f"[{chunk.title} · fragmento {chunk.chunk_index + 1}]\n{chunk.content}" for chunk in chunks
    )
    if not settings_has_chat_key():
        return (
            "No hay un modelo de chat configurado. Estos son los fragmentos más cercanos "
            f"a tu pregunta:\n\n{context}"
        )
    return _openai_answer(question, context)


def settings_has_chat_key() -> bool:
    from app.core.config import settings

    return bool(settings.openai_api_key)


def _openai_answer(question: str, context: str) -> str:
    import httpx

    from app.core.config import settings

    response = httpx.post(
        "https://api.openai.com/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openai_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": settings.chat_model,
            "temperature": 0.2,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Respondé en español. Usá solamente el contexto de los documentos. "
                        "Si la respuesta no está en el contexto, decí que no hay información suficiente. "
                        "Mencioná el título del documento cuando cites un dato."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Contexto:\n{context}\n\nPregunta:\n{question}",
                },
            ],
        },
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]
