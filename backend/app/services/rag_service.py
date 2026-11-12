import httpx

from app.core.config import settings
from app.services.retrieval import RetrievedChunk

_SYSTEM_PROMPT = (
    "Respondé en español. Usá solamente los fragmentos de los documentos proporcionados. "
    "Si la respuesta no está en esos fragmentos, decí claramente que la información no está en los documentos. "
    "Mencioná el título del documento cuando cites un dato."
)


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    if not chunks:
        return "Todavía no hay documentos indexados para responder esa pregunta."

    context = "\n\n".join(
        f"[{chunk.title} · fragmento {chunk.page_number or '?'}]\n{chunk.content}"
        for chunk in chunks
    )
    provider = _chat_provider()
    if provider is None:
        return (
            "No hay un modelo de chat configurado. Estos son los fragmentos más cercanos "
            f"a tu pregunta:\n\n{context}"
        )
    url, api_key, model = provider
    return _chat_completion(url, api_key, model, question, context)


def _chat_provider() -> tuple[str, str, str] | None:
    if settings.GEMINI_API_KEY.strip():
        return (
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            settings.GEMINI_API_KEY.strip(),
            "gemini-2.5-flash",
        )
    if settings.GROQ_API_KEY.strip():
        return (
            "https://api.groq.com/openai/v1/chat/completions",
            settings.GROQ_API_KEY.strip(),
            "llama-3.3-70b-versatile",
        )
    if settings.openai_api_key.strip():
        return (
            "https://api.openai.com/v1/chat/completions",
            settings.openai_api_key.strip(),
            settings.chat_model,
        )
    return None


def _chat_completion(url: str, api_key: str, model: str, question: str, context: str) -> str:
    response = httpx.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
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
