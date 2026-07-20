# Full-filing Chunked Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract candidates from every part of a filing instead of truncating or sending one oversized model request.

**Architecture:** Fetch complete source text by default, split it into bounded paragraph-aware chunks, and add a document-level extraction orchestrator that calls the existing single-chunk adapter and deduplicates overlap results. REST and chat ingestion use that orchestrator while persistence and whole-document verification stay unchanged.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, SQLAlchemy, pytest.

## Global Constraints

- Preserve the existing candidate and database schemas.
- Keep extraction synchronous and sequential.
- Do not add embeddings, background jobs, retries, UI work, or SEC-specific parsing.
- Use test-first red-green cycles for every behavior change.

---

### Task 1: Complete fetching and bounded paragraph chunks

**Files:**
- Modify: `revamp/backend/app/ingestion.py:45-78`
- Test: `revamp/backend/tests/test_ingestion.py`

**Interfaces:**
- Produces: `fetch_url_text(url: str, *, max_chars: int | None = None, fetcher=None) -> str`
- Produces: `chunk_document(text: str, *, max_chars: int = 30000) -> list[str]`

- [ ] **Step 1: Write failing fetch and chunk tests**

Add tests proving default fetch retains a marker after 120,000 characters, explicit limits still truncate, long paragraphs are sliced, paragraph chunks stay within the budget, and the final disclosure remains present.

```python
def test_fetch_url_text_does_not_truncate_by_default():
    source = "A" * 130_000 + "DEEP DISCLOSURE"
    assert fetch_url_text("https://www.sec.gov/x.htm", fetcher=lambda _: source).endswith("DEEP DISCLOSURE")


def test_chunk_document_covers_long_document_with_bounded_chunks():
    text = "A" * 18 + "\n\n" + "B" * 18 + "\n\nDEEP DISCLOSURE"
    chunks = chunk_document(text, max_chars=20)
    assert all(len(chunk) <= 20 for chunk in chunks)
    assert "DEEP DISCLOSURE" in chunks[-1]
    assert "A" * 18 in chunks[0]


def test_chunk_document_slices_a_single_oversized_passage():
    chunks = chunk_document("A" * 45, max_chars=20)
    assert chunks == ["A" * 20, "A" * 20, "A" * 5]
```

- [ ] **Step 2: Run tests and verify RED**

Run: `cd revamp/backend && uv run pytest tests/test_ingestion.py -v`

Expected: failure because default fetching truncates and `chunk_document` does not exist.

- [ ] **Step 3: Implement complete fetch and chunking**

Change default truncation to `None`, slice only for an explicit integer, and implement a pure paragraph packer. Split passages larger than the budget before packing; join packed passages with `"\n\n"`. Reject non-positive budgets with `ValueError`. Keep chunks bounded; overlap is omitted for an oversized single passage and otherwise may repeat the preceding final passage only when it fits alongside new content.

- [ ] **Step 4: Run tests and verify GREEN**

Run: `cd revamp/backend && uv run pytest tests/test_ingestion.py -v`

Expected: all ingestion tests pass.

### Task 2: Document-level extraction and overlap deduplication

**Files:**
- Modify: `revamp/backend/app/extraction/adapter.py`
- Test: `revamp/backend/tests/test_extraction_adapter.py`

**Interfaces:**
- Consumes: `chunk_document(text: str, *, max_chars: int = 30000) -> list[str]`
- Produces: `extract_document_candidates(document_text: str, known_entities: list[str], document_id: str = "doc", *, client=None, provider: str | None = None, chunk_chars: int = 30000) -> ExtractionResult`

- [ ] **Step 1: Write a failing deep-disclosure regression test**

Monkeypatch `extract_candidates` with a deterministic function that records every chunk and emits the same candidate whenever the deep disclosure is present. Use a document longer than the former cutoff and assert the last marker was scanned and the duplicate candidate appears once.

```python
def test_document_extraction_scans_deep_chunks_and_deduplicates(monkeypatch):
    seen = []
    candidate = ExtractionResult.model_validate({"candidates": [CANDIDATE_PAYLOAD]})

    def fake_extract(text, known_entities, document_id="doc", **kwargs):
        seen.append(text)
        return candidate if "DEEP DISCLOSURE" in text else ExtractionResult(candidates=[])

    monkeypatch.setattr(adapter, "extract_candidates", fake_extract)
    result = adapter.extract_document_candidates(
        "A" * 40 + "\n\nDEEP DISCLOSURE\n\nDEEP DISCLOSURE",
        ["Amazon", "Anthropic"],
        document_id="amazon-10k",
        chunk_chars=25,
    )
    assert any("DEEP DISCLOSURE" in chunk for chunk in seen)
    assert len(result.candidates) == 1
```

- [ ] **Step 2: Run test and verify RED**

Run: `cd revamp/backend && uv run pytest tests/test_extraction_adapter.py::test_document_extraction_scans_deep_chunks_and_deduplicates -v`

Expected: failure because `extract_document_candidates` does not exist.

- [ ] **Step 3: Implement minimal orchestrator**

Import `chunk_document`, call the existing `extract_candidates` sequentially for each chunk, and retain the first candidate for each deterministic key made from all structured claim fields, including `tuple(missing_information)`, but excluding `exact_passage`, `document_id`, and `confidence_note`. Return `ExtractionResult(candidates=merged)`.

- [ ] **Step 4: Run adapter tests and verify GREEN**

Run: `cd revamp/backend && uv run pytest tests/test_extraction_adapter.py -v`

Expected: all adapter tests pass.

### Task 3: Route REST and chat ingestion through full-document extraction

**Files:**
- Modify: `revamp/backend/app/routers/documents.py:6,63-68`
- Modify: `revamp/backend/app/chat/agent.py:13,115`
- Test: `revamp/backend/tests/test_documents_api.py`
- Test: `revamp/backend/tests/test_chat_agent.py`

**Interfaces:**
- Consumes: `extract_document_candidates(...) -> ExtractionResult`

- [ ] **Step 1: Write failing wiring tests**

Monkeypatch `extract_document_candidates` in each consumer, invoke the endpoint/tool, and assert it receives the stored full text, entity names, document id, and chosen provider. Return an empty `ExtractionResult` so the tests remain offline.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd revamp/backend && uv run pytest tests/test_documents_api.py tests/test_chat_agent.py -v`

Expected: the new monkeypatch targets are absent or never called.

- [ ] **Step 3: Switch both consumers to the orchestrator**

Replace only the adapter import and function call in each file. Keep response shapes, persistence, provider choice, and transaction behavior unchanged.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd revamp/backend && uv run pytest tests/test_documents_api.py tests/test_chat_agent.py -v`

Expected: all document API and chat agent tests pass.

### Task 4: Full regression verification

**Files:**
- Verify all modified backend files.

**Interfaces:** None.

- [ ] **Step 1: Run formatting/static checks available in the project**

Run: `cd revamp/backend && uv run ruff check app tests`

Expected: exit 0.

- [ ] **Step 2: Run the complete backend suite**

Run: `cd revamp/backend && uv run pytest -v`

Expected: all tests pass.

- [ ] **Step 3: Inspect the final diff**

Run: `git diff --check && git diff -- revamp/backend/app revamp/backend/tests`

Expected: no whitespace errors; every changed production line traces to full-filing fetching, chunking, extraction, or consumer wiring.
