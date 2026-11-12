import httpx

from app.core.config import settings
from app.services.retrieval import RetrievedChunk


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "Todavía no hay documentos indexados para responder esa pregunta."

    context = "\n\n".join(
        f"[{chunk.title} · fragmento {chunk.page_number or '?'}]\n{chunk.content}"
        for chunk in chunks
    )
    if not settings.openai_api_key:
        return (
            "No hay un modelo de chat configurado. Estos son los fragmentos más cercanos "
            f"a tu pregunta:\n\n{context}"
        )
    return _openai_answer(question, context)


def _openai_answer(question: str, context: str) -> str:
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
