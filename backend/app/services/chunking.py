def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    if overlap >= size:
        raise ValueError("El solapamiento tiene que ser menor que el tamaño del fragmento")

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return []

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        end = min(start + size, len(cleaned))
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end == len(cleaned):
            break
        start = end - overlap
    return chunks
