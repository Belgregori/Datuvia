import re
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import text
from sqlmodel import Session

from app.services.embeddings import embed_texts

_WORD = re.compile(r"\w+", re.UNICODE)


MIN_VECTOR_SCORE = 0.22


@dataclass
class RetrievedChunk:
    document_id: UUID
    title: str
    content: str
    page_number: int | None
    score: float
    vector_score: float


def _vector_literal(vector: list[float]) -> str:
    return "[" + ",".join(f"{value:.8f}" for value in vector) + "]"


def _tsquery(query: str) -> str:
    words = _WORD.findall(query.lower())
    return " & ".join(words[:16])


def search_chunks(
    session: Session,
    workspace_id: UUID,
    query: str,
    top_k: int = 4,
) -> list[RetrievedChunk]:
    query_vector = embed_texts([query])[0]
    rows = session.execute(
        text(
            """
            SELECT c.document_id,
                   d.title,
                   c.content,
                   c.page_number,
                   (1 - (c.embedding <=> CAST(:embedding AS vector))) AS vector_score,
                   (
                     0.75 * (1 - (c.embedding <=> CAST(:embedding AS vector)))
                     + 0.25 * CASE
                         WHEN :tsquery <> ''
                          AND to_tsvector('spanish', c.content) @@ to_tsquery('spanish', :tsquery)
                         THEN LEAST(ts_rank(to_tsvector('spanish', c.content), to_tsquery('spanish', :tsquery)), 1)
                         ELSE 0
                       END
                   ) AS score
            FROM document_chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE d.workspace_id = :workspace_id
              AND d.status = 'listo'
              AND c.embedding IS NOT NULL
            ORDER BY score DESC
            LIMIT :top_k
            """
        ),
        {
            "embedding": _vector_literal(query_vector),
            "tsquery": _tsquery(query),
            "workspace_id": str(workspace_id),
            "top_k": top_k,
        },
    ).all()
    return [
        RetrievedChunk(
            document_id=row.document_id,
            title=row.title,
            content=row.content,
            page_number=row.page_number,
            score=float(row.score),
            vector_score=float(row.vector_score),
        )
        for row in rows
    ]


def rerank_chunks(
    chunks: list[RetrievedChunk],
    min_vector_score: float = MIN_VECTOR_SCORE,
) -> list[RetrievedChunk]:
    return [chunk for chunk in chunks if chunk.vector_score >= min_vector_score]
