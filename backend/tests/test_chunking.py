from app.services.chunking import chunk_text


def test_chunk_text_splits_with_overlap():
    text = "a" * 1000
    chunks = chunk_text(text, size=400, overlap=50)
    assert len(chunks) == 3
    assert all(len(chunk) <= 400 for chunk in chunks)


def test_chunk_text_empty():
    assert chunk_text("   \n") == []
