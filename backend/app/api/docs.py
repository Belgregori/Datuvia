import os
from io import BytesIO
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile
from pydantic import BaseModel
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from sqlmodel import Session, select

from app.core.security import get_current_user
from app.db.models import Document, DocumentChunk, User, Workspace
from app.db.session import engine, get_session
from app.services.chunking import chunk_text
from app.services.embeddings import embed_texts

router = APIRouter(prefix="/docs", tags=["docs"])

MAX_BYTES = 20_000_000
ALLOWED_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".pdf"}
UPLOAD_DIR = "uploads"


class DocumentRead(BaseModel):
    id: UUID
    title: str
    file_type: str
    chunk_count: int
    status: str


def _extension(filename: str) -> str:
    dot = filename.rfind(".")
    return filename[dot:].lower() if dot >= 0 else ""


def _extract_pieces(raw: bytes, ext: str) -> list[tuple[str, int]]:
    if ext == ".pdf":
        try:
            reader = PdfReader(BytesIO(raw))
        except PdfReadError as exc:
            raise ValueError("El PDF no contiene texto extraíble") from exc

        pieces: list[tuple[str, int]] = []
        for page_number, page in enumerate(reader.pages, start=1):
            text = page.extract_text() or ""
            for piece in chunk_text(text):
                pieces.append((piece, page_number))
        if not pieces:
            raise ValueError("El PDF no contiene texto extraíble")
        return pieces

    try:
        content = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("El archivo tiene que estar en UTF-8") from exc

    text_pieces = chunk_text(content)
    if not text_pieces:
        raise ValueError("El archivo no tiene texto para indexar")
    return [(piece, index + 1) for index, piece in enumerate(text_pieces)]


def process_document(document_id: UUID) -> None:
    with Session(engine) as session:
        document = session.get(Document, document_id)
        if document is None:
            return
        try:
            with open(document.file_path, "rb") as handle:
                raw = handle.read()
            pieces = _extract_pieces(raw, document.file_type)
            vectors = embed_texts([piece for piece, _page in pieces])
            for (piece, page_number), vector in zip(pieces, vectors, strict=True):
                session.add(
                    DocumentChunk(
                        document_id=document.id,
                        content=piece,
                        page_number=page_number,
                        embedding=vector,
                    )
                )
            document.status = "listo"
            session.add(document)
            session.commit()
        except Exception:
            session.rollback()
            failed = session.get(Document, document_id)
            if failed is not None:
                failed.status = "error"
                session.add(failed)
                session.commit()


@router.get("", response_model=list[DocumentRead])
def list_documents(
    workspace_id: UUID = Query(...),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[DocumentRead]:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")

    documents = session.exec(
        select(Document)
        .where(Document.workspace_id == workspace_id)
        .order_by(Document.created_at.desc())
    ).all()

    result: list[DocumentRead] = []
    for document in documents:
        chunks = session.exec(
            select(DocumentChunk).where(DocumentChunk.document_id == document.id)
        ).all()
        result.append(
            DocumentRead(
                id=document.id,
                title=document.title,
                file_type=document.file_type,
                chunk_count=len(chunks),
                status=document.status or "listo",
            )
        )
    return result


@router.post("", response_model=DocumentRead, status_code=201)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    workspace_id: UUID = Form(...),
    title: str | None = Form(default=None),
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> DocumentRead:
    workspace = session.get(Workspace, workspace_id)
    if workspace is None or workspace.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Workspace no encontrado")

    filename = file.filename or "documento.txt"
    ext = _extension(filename)
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail="Solo se aceptan archivos .pdf, .txt, .md, .csv o .json",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(status_code=400, detail="El archivo está vacío")
    if len(raw) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="El archivo supera los 20 MB")

    workspace_folder = os.path.join(UPLOAD_DIR, str(workspace_id))
    os.makedirs(workspace_folder, exist_ok=True)
    file_path = os.path.join(workspace_folder, filename)
    with open(file_path, "wb") as handle:
        handle.write(raw)

    document = Document(
        title=(title or filename).strip() or filename,
        file_path=file_path,
        file_type=ext,
        workspace_id=workspace_id,
        status="procesando",
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    background_tasks.add_task(process_document, document.id)

    return DocumentRead(
        id=document.id,
        title=document.title,
        file_type=document.file_type,
        chunk_count=0,
        status=document.status,
    )


@router.delete("/{document_id}", status_code=204)
def delete_document(
    document_id: UUID,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    workspace = session.get(Workspace, document.workspace_id)
    if workspace is None or workspace.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Documento no encontrado")

    session.delete(document)
    session.commit()
