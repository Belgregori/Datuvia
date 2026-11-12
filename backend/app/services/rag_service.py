from sqlmodel import Session, select
from app.db.models import Chunk, Document
from app.services.embeddings import embed_texts
import openai

def query_rag(question: str, user_id: int, session: Session, top_k: int = 4) -> dict:
    # 1. Generar embedding para la pregunta del usuario
    query_vector = embed_texts([question])[0]

    # 2. Búsqueda de similitud vectorial usando pgvector (ordenado por distancia de coseno)
    # Filtramos por los documentos que pertenecen al usuario (aislamiento de datos)
    statement = (
        select(Chunk, Document)
        .join(Document, Chunk.document_id == Document.id)
        .where(Document.owner_id == user_id)
        .order_by(Chunk.embedding.cosine_distance(query_vector))
        .limit(top_k)
    )
    
    results = session.exec(statement).all()

    if not results:
        return {
            "answer": "No encontré documentos relevantes en tu biblioteca para responder a esta pregunta.",
            "sources": []
        }

    # 3. Construir el contexto y recopilar las fuentes
    context_parts = []
    sources = []

    for chunk, doc in results:
        context_parts.append(f"--- Documento: {doc.title} ---\n{chunk.content}")
        sources.append({
            "document_id": doc.id,
            "title": doc.title,
            "chunk_id": chunk.id,
            "content": chunk.content
        })

    context = "\n\n".join(context_parts)

    # 4. Prompt estricto para evitar alucinaciones y asegurar respuestas basadas en evidencia
    prompt = f"""Eres un asistente de IA experto en gestión de conocimiento empresarial. 
Responde a la pregunta del usuario utilizando **únicamente** el contexto provisto a continuación. 
Si la información no está en el contexto, di claramente que no la sabes y no inventes respuestas.

Contexto:
{context}

Pregunta: {question}
Respuesta:"""

    # 5. Llamada al LLM de OpenAI para generar la respuesta final
    response = openai.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0
    )

    answer_text = response.choices[0].message.content

    return {
        "answer": answer_text,
        "sources": sources
    }