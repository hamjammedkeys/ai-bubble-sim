import fitz  # pymupdf
from app.ingestion import (
    Passage,
    chunk_document,
    extract_pdf_text,
    fetch_url_text,
    split_passages,
)


def test_fetch_url_text_prefixes_jina_and_truncates():
    seen = {}

    def fake(target: str) -> str:
        seen["target"] = target
        return "Z" * 100_000

    out = fetch_url_text("https://www.sec.gov/x.htm", max_chars=50, fetcher=fake)
    assert seen["target"] == "https://r.jina.ai/https://www.sec.gov/x.htm"
    assert out == "Z" * 50


def test_fetch_url_text_does_not_truncate_by_default():
    source = "A" * 130_000 + "DEEP DISCLOSURE"

    out = fetch_url_text("https://www.sec.gov/x.htm", fetcher=lambda _target: source)

    assert out.endswith("DEEP DISCLOSURE")


def test_fetch_url_text_rejects_ssrf_targets():
    import pytest

    called = {"n": 0}

    def fake(_target: str) -> str:
        called["n"] += 1
        return "should not be reached"

    for bad in [
        "http://localhost:8000/health",
        "http://127.0.0.1/",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.5/",
        "file:///etc/passwd",
        "ftp://example.com/x",
    ]:
        with pytest.raises(ValueError):
            fetch_url_text(bad, fetcher=fake)
    assert called["n"] == 0  # nothing was ever fetched


def test_extract_pdf_text_reads_page_text(tmp_path):
    pdf = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "OpenAI committed $11.9 billion to CoreWeave.")
    doc.save(str(pdf))
    doc.close()

    text = extract_pdf_text(str(pdf))
    assert "OpenAI committed $11.9 billion to CoreWeave." in text


def test_split_passages_preserves_offsets():
    text = "First passage about OpenAI.\n\nSecond passage about CoreWeave.\n\n   \n\nThird."
    passages = split_passages(text)

    assert [p.text for p in passages] == [
        "First passage about OpenAI.",
        "Second passage about CoreWeave.",
        "Third.",
    ]
    # Offsets must index back to the exact substring.
    for p in passages:
        assert isinstance(p, Passage)
        assert text[p.char_start:p.char_end] == p.text


def test_chunk_document_covers_long_document_with_bounded_chunks():
    text = "A" * 18 + "\n\n" + "B" * 18 + "\n\nDEEP DISCLOSURE"

    chunks = chunk_document(text, max_chars=20)

    assert all(len(chunk) <= 20 for chunk in chunks)
    assert "A" * 18 in chunks[0]
    assert "DEEP DISCLOSURE" in chunks[-1]


def test_chunk_document_slices_a_single_oversized_passage():
    chunks = chunk_document("A" * 45, max_chars=20)

    assert chunks == ["A" * 20, "A" * 20, "A" * 5]
