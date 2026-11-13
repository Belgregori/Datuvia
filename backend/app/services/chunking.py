def chunk_text(text: str, size: int = 800, overlap: int = 120) -> list[str]:
    if overlap >= size:
        raise ValueError("El solapamiento tiene que ser menor que el tamaño del fragmento")

    cleaned = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not cleaned:
        return []

    def end_at(start: int) -> int:
        limit = min(start + size, len(cleaned))
        if limit >= len(cleaned):
            return len(cleaned)
        if cleaned[limit].isspace() or cleaned[limit - 1].isspace():
            return limit
        cut = max(cleaned.rfind(" ", start, limit), cleaned.rfind("\n", start, limit))
        if cut > start:
            return cut
        return limit

    chunks: list[str] = []
    start = 0
    while start < len(cleaned):
        while start < len(cleaned) and cleaned[start].isspace():
            start += 1
        if start >= len(cleaned):
            break
        end = end_at(start)
        piece = cleaned[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= len(cleaned):
            break
        next_start = end - overlap
        if next_start <= start:
            next_start = end
        elif not cleaned[next_start - 1].isspace() and not cleaned[next_start].isspace():
            boundary = cleaned.find(" ", next_start)
            newline = cleaned.find("\n", next_start)
            options = [index for index in (boundary, newline) if index != -1]
            if options and min(options) + 1 > start:
                next_start = min(options) + 1
        if next_start <= start:
            next_start = end
        start = next_start
    return chunks
