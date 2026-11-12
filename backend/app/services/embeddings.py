import hashlib
import math
import re

import httpx

from app.core.config import settings

_TOKEN = re.compile(r"\w+", re.UNICODE)


def embed_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if settings.openai_api_key:
        return _openai_embeddings(texts)
    return [_local_embedding(text) for text in texts]


def _local_embedding(text: str) -> list[float]:
    dim = settings.embedding_dim
    vector = [0.0] * dim
    tokens = _TOKEN.findall(text.lower())
    for token in tokens:
        digest = hashlib.sha256(token.encode()).digest()
        index = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _openai_embeddings(texts: list[str]) -> list[list[float]]:
    vectors: list[list[float]] = []
    headers = {
        "Authorization": f"Bearer {settings.openai_api_key}",
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60) as client:
        for start in range(0, len(texts), 64):
            batch = texts[start : start + 64]
            response = client.post(
                "https://api.openai.com/v1/embeddings",
                headers=headers,
                json={"model": settings.embedding_model, "input": batch},
            )
            response.raise_for_status()
            data = response.json()["data"]
            data.sort(key=lambda item: item["index"])
            for item in data:
                embedding = item["embedding"]
                if len(embedding) != settings.embedding_dim:
                    raise RuntimeError(
                        "La dimensión del embedding no coincide con EMBEDDING_DIM"
                    )
                vectors.append(embedding)
    return vectors
