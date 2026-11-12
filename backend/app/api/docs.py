from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlmodel import Session, select

from app.core.security import get_current_user
from app.db.models import DocumentChunk, Document, User
from app.db.session import get_session
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts

router = APIRouter(prefix="/docs", tags=["docs"])

MAX_BYTES = 2_000_000
ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json"}


class DocumentRead(BaseModel):
    id: int
    title: str
    filename: str
    chunk_count: int


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


@router.get("", response_model=list[DocumentRead])
def list_documents(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    documents = session.exec(
        select(Document).where(Document.owner_id == user.id).order_by(Document.created_at.desc())
    ).all()
    result: list[DocumentRead] = []
    for document in documents:
        chunks = session.exec(select(Chunk).where(Chunk.document_id == document.id)).all()
        result.append(
            DocumentRead(
                id=document.id,
                title=document.title,
                filename=document.filename,
                chunk_count=len(chunks),
            )
        )
    return result


@router.post("", response_model=DocumentRead, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    title: str | None = Form(default=None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    filename = file.filename or "documento.txt"
    if _extension(filename) not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Solo se aceptan archivos .txt, .md, .csv o .json")

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="El archivo supera los 2 MB")

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="El archivo tiene que estar en UTF-8") from exc

    pieces = chunk_text(content)
    if not pieces:
        raise HTTPException(status_code=400, detail="El archivo no tiene texto para indexar")

    document = Document(
        owner_id=user.id,
        title=(title or filename).strip() or filename,
        filename=filename,
        content=content,
    )
    session.add(document)
    session.flush()

    vectors = embed_texts(pieces)
    for index, (piece, vector) in enumerate(zip(pieces, vectors, strict=True)):
        session.add(
            Chunk(
                document_id=document.id,
                content=piece,
                chunk_index=index,
                embedding=vector,
            )
        )
    session.commit()
    session.refresh(document)
    return DocumentRead(
        id=document.id,
        title=document.title,
        filename=document.filename,
        chunk_count=len(pieces),
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    document = session.get(Document, document_id)
    if document is None or document.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    chunks = session.exec(select(Chunk).where(Chunk.document_id == document.id)).all()
    for chunk in chunks:
        session.delete(chunk)
    session.delete(document)
    session.commit()
