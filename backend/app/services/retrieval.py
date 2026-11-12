from dataclasses import dataclass
from uuid import UUID

from sqlmodel import Session, select

from app.db.models import Document, DocumentChunk
from app.services.embeddings import embed_texts


@dataclass
class RetrievedChunk:
    document_id: UUID
    title: str
    content: str
    page_number: int | None
    score: float


def search_chunks(
    session: Session,
    workspace_id: UUID,
    query: str,
    top_k: int = 4,
) -> list[RetrievedChunk]:
    query_vector = embed_texts([query])[0]
    distance = DocumentChunk.embedding.cosine_distance(query_vector)
    statement = (
        select(DocumentChunk, Document, distance.label("distance"))
        .join(Document, DocumentChunk.document_id == Document.id)
        .where(Document.workspace_id == workspace_id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(top_k)
    )
    rows = session.exec(statement).all()
    return [
        RetrievedChunk(
            document_id=document.id,
            title=document.title,
            content=chunk.content,
            page_number=chunk.page_number,
            score=float(1 - row_distance),
        )
        for chunk, document, row_distance in rows
    ]
