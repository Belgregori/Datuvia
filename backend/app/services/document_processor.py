import os
from pypdf import PdfReader
from sqlmodel import Session
from app.db.models import Document, DocumentChunk
from app.services.chunking import chunk_text
from app.services.embeddings import get_embedding

def process_document(document_id: int, session: Session) -> None:
    doc = session.get(Document, document_id)
    if not doc or not os.path.exists(doc.file_path):
        return

    # 1. Extraer texto del PDF página por página
    reader = PdfReader(doc.file_path)
    full_text = ""
    page_texts = []
    
    for page_idx, page in enumerate(reader.pages):
        text = page.extract_text() or ""
        page_texts.append((page_idx + 1, text))
        full_text += text + "\n"

    # 2. Actualizar estado a procesando
    doc.status = "processing"
    session.add(doc)
    session.commit()

    try:
        # 3. Fragmentar y generar embeddings
        for page_num, page_text in page_texts:
            chunks = chunk_text(page_text)
            for chunk_content in chunks:
                if not chunk_content.strip():
                    continue
                
                vector = get_embedding(chunk_content)
                
                db_chunk = DocumentChunk(
                    document_id=doc.id,
                    content=chunk_content,
                    page_number=page_num,
                    embedding=vector
                )
                session.add(db_chunk)

        doc.status = "processed"
        session.add(doc)
        session.commit()
    except Exception as e:
        doc.status = "failed"
        session.add(doc)
        session.commit()
        raise e