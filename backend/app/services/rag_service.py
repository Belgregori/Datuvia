import json
from collections.abc import Iterator

import httpx

from app.core.config import settings
from app.services.retrieval import RetrievedChunk

_SYSTEM_PROMPT = (
    "Respondé en español. Usá solamente los fragmentos de los documentos proporcionados. "
    "Si la respuesta no está en esos fragmentos, decí claramente que la información no está en los documentos. "
    "Mencioná el título del documento cuando cites un dato."
)


def estimate_tokens(text: str) -> int:
    return max(1, (len(text) + 3) // 4)


def rewrite_query(question: str, history: list[tuple[str, str]]) -> str:
    if not history:
        return question
    provider = _chat_provider()
    if provider is None:
        return question

    url, api_key, model = provider
    transcript = "\n".join(f"{role}: {content[:500]}" for role, content in history)
    prompt = (
        "Reescribí la última pregunta para que se entienda sola, usando el historial si hace falta. "
        "Devolvé solo la pregunta reescrita, en español, sin comillas ni explicación.\n\n"
        f"Historial:\n{transcript}\n\nPregunta: {question}"
    )
    try:
        response = httpx.post(
            url,
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": model,
                "temperature": 0,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=30,
        )
        response.raise_for_status()
        rewritten = response.json()["choices"][0]["message"]["content"].strip().strip('"')
        return rewritten[:500] or question
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError):
        return question


def iter_answer(
    question: str,
    chunks: list[RetrievedChunk],
    history: list[tuple[str, str]] | None = None,
    usage: dict | None = None,
) -> Iterator[str]:
    if not chunks:
        yield "Todavía no hay documentos indexados para responder esa pregunta."
        return

    context = "\n\n".join(
        f"[{chunk.title} · fragmento {chunk.page_number or '?'}]\n{chunk.content}"
        for chunk in chunks
    )
    provider = _chat_provider()
    if provider is None:
        yield from _pieces(
            "No hay un modelo de chat configurado. Estos son los fragmentos más cercanos "
            f"a tu pregunta:\n\n{context}"
        )
        return

    url, api_key, model = provider
    try:
        yield from _stream_completion(url, api_key, model, question, context, history or [], usage)
    except (httpx.HTTPError, KeyError, IndexError, ValueError, json.JSONDecodeError):
        yield "El modelo de chat no pudo responder. Probá de nuevo en unos segundos."


def _chat_provider() -> tuple[str, str, str] | None:
    if settings.GEMINI_API_KEY.strip():
        return (
            "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
            settings.GEMINI_API_KEY.strip(),
            "gemini-3-flash-preview",
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


def _pieces(text: str, size: int = 24) -> Iterator[str]:
    for start in range(0, len(text), size):
        yield text[start : start + size]


def _stream_completion(
    url: str,
    api_key: str,
    model: str,
    question: str,
    context: str,
    history: list[tuple[str, str]],
    usage: dict | None,
) -> Iterator[str]:
    history_block = ""
    if history:
        history_block = "Conversación reciente:\n" + "\n".join(
            f"{role}: {content[:400]}" for role, content in history
        ) + "\n\n"
    payload = {
        "model": model,
        "temperature": 0.2,
        "stream": True,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"{history_block}Contexto:\n{context}\n\nPregunta:\n{question}",
            },
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60) as client:
        with client.stream("POST", url, headers=headers, json=payload) as response:
            response.raise_for_status()
            for line in response.iter_lines():
                if not line.startswith("data:"):
                    continue
                data = line[5:].strip()
                if not data or data == "[DONE]":
                    if data == "[DONE]":
                        break
                    continue
                chunk = json.loads(data)
                reported = (chunk.get("usage") or {}).get("total_tokens")
                if usage is not None and reported:
                    usage["tokens"] = int(reported)
                choices = chunk.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                text = delta.get("content")
                if text:
                    yield text


def generate_answer(question: str, chunks: list[RetrievedChunk]) -> str:
    return "".join(iter_answer(question, chunks))
