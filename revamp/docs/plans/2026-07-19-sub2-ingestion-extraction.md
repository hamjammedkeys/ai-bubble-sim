# Sub-project 2: Ingestion + Extraction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a filing (PDF or raw text) into typed, cited `CandidateEdge` rows — via PDF text extraction, a provider-agnostic `extract_candidates` adapter (live OpenAI structured output + an offline deterministic fallback), and the plan §6 extraction schema.

**Architecture:** New `app/ingestion.py` (pymupdf text extraction + passage splitting) and an `app/extraction/` package: `schema.py` (Pydantic §6 models), `fallback.py` (deterministic offline proposer), `adapter.py` (`extract_candidates` dispatching on `settings.llm_provider`). The OpenAI branch takes an **injectable client** so tests run offline with a fake; live calls need `OPENAI_API_KEY`. Everything downstream stays provider-blind: both branches return the same `ExtractionResult`.

**Tech Stack:** Python 3.11+ (uv), pymupdf (`fitz`), Pydantic v2, openai SDK. Builds on Sub-project 1 (`app/config.py`, `app/db.py`, `app/models.py`).

## Global Constraints

- Work only inside `revamp/backend/`. Never touch files outside `revamp/`.
- The extraction schema is **plan §6 verbatim**: `CandidateEdge` fields `source_entity, target_entity, relationship_type, metric, value, unit, period, exact_passage, document_id, permitted_operation, unsupported_operation, missing_information, evidence_class, confidence_note`; `ExtractionResult` = `candidates: list[CandidateEdge]`.
- `relationship_type` ∈ {`investment_exposure, equity_method, customer_concentration, purchase_obligation, take_or_pay, counterparty_credit_exposure, commercial_spending, operational_dependency, behavioural_response, supplier_dependency`}. `evidence_class` ∈ {`reported, calculated, constrained, assumed, unknown`}.
- `extract_candidates(document_text: str, known_entities: list[str]) -> ExtractionResult` is the ONLY function that produces candidates. It dispatches on `settings.llm_provider`: `"openai"` (live) and `"fallback"` (offline deterministic). Unknown provider raises `ValueError`.
- The OpenAI branch must accept an injectable `client` (default lazily constructs `openai.OpenAI()`), so tests never hit the network and need no key.
- `exact_passage` on any produced candidate must be a verbatim substring of `document_text` (the fallback proposer must guarantee this; the verifier in Sub-project 3 will re-check it for the OpenAI branch).
- Low temperature (0) for the live model. Model id from `settings.openai_model`.
- Run commands from `revamp/backend/`. Test command: `uv run pytest`. TDD: failing test first, commit after each green task.

---

### Task 1: PDF text extraction + passage splitting

**Files:**
- Create: `revamp/backend/app/ingestion.py`
- Create: `revamp/backend/tests/test_ingestion.py`

**Interfaces:**
- Consumes: nothing from this sub-project (pymupdf only).
- Produces:
  - `app.ingestion.extract_pdf_text(path: str) -> str` — concatenated page text, pages joined by `"\n"` (matches plan §12).
  - `app.ingestion.Passage` — a `dataclass(frozen=True)` with `text: str`, `char_start: int`, `char_end: int`.
  - `app.ingestion.split_passages(text: str) -> list[Passage]` — split on blank lines (`\n\n`+), preserving exact char offsets so `text[p.char_start:p.char_end] == p.text` for every passage; empty/whitespace-only chunks dropped.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_ingestion.py`:

```python
import fitz  # pymupdf

from app.ingestion import Passage, extract_pdf_text, split_passages


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_ingestion.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.ingestion'`.

- [ ] **Step 3: Write the implementation**

Create `revamp/backend/app/ingestion.py`:

```python
import re
from dataclasses import dataclass

import fitz  # pymupdf


def extract_pdf_text(path: str) -> str:
    doc = fitz.open(path)
    try:
        return "\n".join(page.get_text() for page in doc)
    finally:
        doc.close()


@dataclass(frozen=True)
class Passage:
    text: str
    char_start: int
    char_end: int


def split_passages(text: str) -> list[Passage]:
    passages: list[Passage] = []
    pos = 0
    for block in re.split(r"\n\s*\n", text):
        start = text.index(block, pos)
        pos = start + len(block)
        stripped = block.strip()
        if not stripped:
            continue
        lead = len(block) - len(block.lstrip())
        char_start = start + lead
        char_end = char_start + len(stripped)
        passages.append(Passage(text=stripped, char_start=char_start, char_end=char_end))
    return passages
```

Logic: split on blank lines with `re.split`, locate each block's offset with `text.index(block, pos)` (advancing `pos` so repeated blocks resolve to distinct positions), then trim leading/trailing whitespace while adjusting offsets so `text[char_start:char_end] == p.text` holds exactly. `re.split` may yield empty/whitespace blocks (dropped by the `if not stripped` guard).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_ingestion.py -v`
Expected: PASS (both tests).

- [ ] **Step 5: Commit**

```bash
git add app/ingestion.py tests/test_ingestion.py
git commit -m "feat(revamp/backend): add PDF text extraction and passage splitting"
```

---

### Task 2: Extraction schema (plan §6)

**Files:**
- Create: `revamp/backend/app/extraction/__init__.py`
- Create: `revamp/backend/app/extraction/schema.py`
- Create: `revamp/backend/tests/test_extraction_schema.py`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `app.extraction.schema.RelationshipType` — `Literal[...]` of the 10 relationship types.
  - `app.extraction.schema.EvidenceClass` — `Literal[...]` of the 5 evidence classes.
  - `app.extraction.schema.CandidateEdge` — Pydantic v2 model with the §6 fields.
  - `app.extraction.schema.ExtractionResult` — `candidates: list[CandidateEdge]`.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_extraction_schema.py`:

```python
import pytest
from pydantic import ValidationError

from app.extraction.schema import CandidateEdge, ExtractionResult


def _valid_candidate() -> dict:
    return {
        "source_entity": "OpenAI",
        "target_entity": "CoreWeave",
        "relationship_type": "purchase_obligation",
        "metric": "contract_value",
        "value": 11.9,
        "unit": "usd_billions",
        "period": "through_2030",
        "exact_passage": "OpenAI committed $11.9 billion to CoreWeave.",
        "document_id": "doc-1",
        "permitted_operation": "report disclosed ceiling as exposure",
        "unsupported_operation": "treat as realized loss",
        "missing_information": ["PD", "LGD"],
        "evidence_class": "reported",
        "confidence_note": "verbatim from S-1",
    }


def test_candidate_edge_accepts_valid():
    c = CandidateEdge(**_valid_candidate())
    assert c.value == 11.9
    assert c.missing_information == ["PD", "LGD"]


def test_value_optional_and_missing_info_defaults():
    data = _valid_candidate()
    data["value"] = None
    data["missing_information"] = []
    c = CandidateEdge(**data)
    assert c.value is None


def test_rejects_bad_relationship_type():
    data = _valid_candidate()
    data["relationship_type"] = "made_up_type"
    with pytest.raises(ValidationError):
        CandidateEdge(**data)


def test_rejects_bad_evidence_class():
    data = _valid_candidate()
    data["evidence_class"] = "guessed"
    with pytest.raises(ValidationError):
        CandidateEdge(**data)


def test_extraction_result_wraps_candidates():
    r = ExtractionResult(candidates=[CandidateEdge(**_valid_candidate())])
    assert len(r.candidates) == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_extraction_schema.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.extraction'`.

- [ ] **Step 3: Write the schema**

Create empty `revamp/backend/app/extraction/__init__.py`.

Create `revamp/backend/app/extraction/schema.py`:

```python
from typing import Literal

from pydantic import BaseModel

RelationshipType = Literal[
    "investment_exposure",
    "equity_method",
    "customer_concentration",
    "purchase_obligation",
    "take_or_pay",
    "counterparty_credit_exposure",
    "commercial_spending",
    "operational_dependency",
    "behavioural_response",
    "supplier_dependency",
]

EvidenceClass = Literal[
    "reported",
    "calculated",
    "constrained",
    "assumed",
    "unknown",
]


class CandidateEdge(BaseModel):
    source_entity: str
    target_entity: str
    relationship_type: RelationshipType
    metric: str
    value: float | None
    unit: str | None
    period: str | None
    exact_passage: str
    document_id: str
    permitted_operation: str
    unsupported_operation: str
    missing_information: list[str]
    evidence_class: EvidenceClass
    confidence_note: str


class ExtractionResult(BaseModel):
    candidates: list[CandidateEdge]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_extraction_schema.py -v`
Expected: PASS (all five tests).

- [ ] **Step 5: Commit**

```bash
git add app/extraction/__init__.py app/extraction/schema.py tests/test_extraction_schema.py
git commit -m "feat(revamp/backend): add extraction schema (CandidateEdge/ExtractionResult)"
```

---

### Task 3: Deterministic fallback proposer (offline)

**Files:**
- Create: `revamp/backend/app/extraction/fallback.py`
- Create: `revamp/backend/tests/test_extraction_fallback.py`

**Interfaces:**
- Consumes: `app.extraction.schema.CandidateEdge`, `ExtractionResult`.
- Produces:
  - `app.extraction.fallback.propose_candidates(document_text: str, known_entities: list[str], document_id: str = "doc") -> ExtractionResult`
  - Deterministic, no network. For each passage (split on blank lines) that mentions **two or more** known entities, emit one `CandidateEdge`: `source_entity`/`target_entity` = the first two matched entities in order of appearance; `exact_passage` = the verbatim passage text; `value`/`unit` parsed from a `$<number> billion/million` pattern if present else `None`; `relationship_type="operational_dependency"`; `evidence_class="reported"` if a value was found else `"unknown"`; `metric="mentioned_relationship"`; `missing_information=["propagation"]`; `permitted_operation`/`unsupported_operation`/`confidence_note` fixed strings; `period=None`.
  - This is intentionally conservative structure-detection, not semantics — it exists so the pipeline runs offline. Guarantee: every `exact_passage` is a verbatim substring of `document_text`.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_extraction_fallback.py`:

```python
from app.extraction.fallback import propose_candidates


def test_emits_candidate_for_passage_with_two_entities_and_value():
    text = "OpenAI committed $11.9 billion to CoreWeave through 2030."
    result = propose_candidates(text, known_entities=["OpenAI", "CoreWeave", "Nvidia"], document_id="s1")

    assert len(result.candidates) == 1
    c = result.candidates[0]
    assert {c.source_entity, c.target_entity} == {"OpenAI", "CoreWeave"}
    assert c.source_entity == "OpenAI"  # first in appearance order
    assert c.value == 11.9
    assert c.unit == "usd_billions"
    assert c.evidence_class == "reported"
    assert c.document_id == "s1"
    # exact_passage must be a verbatim substring of the input
    assert c.exact_passage in text


def test_no_value_yields_unknown_evidence_class():
    text = "OpenAI and CoreWeave have a commercial relationship."
    result = propose_candidates(text, known_entities=["OpenAI", "CoreWeave"])
    assert result.candidates[0].value is None
    assert result.candidates[0].evidence_class == "unknown"


def test_passage_with_one_entity_is_skipped():
    text = "OpenAI reported strong revenue growth this year."
    result = propose_candidates(text, known_entities=["OpenAI", "CoreWeave"])
    assert result.candidates == []


def test_is_deterministic():
    text = "OpenAI committed $11.9 billion to CoreWeave."
    a = propose_candidates(text, ["OpenAI", "CoreWeave"])
    b = propose_candidates(text, ["OpenAI", "CoreWeave"])
    assert a.model_dump() == b.model_dump()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_extraction_fallback.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.extraction.fallback'`.

- [ ] **Step 3: Write the proposer**

Create `revamp/backend/app/extraction/fallback.py`:

```python
import re

from app.extraction.schema import CandidateEdge, ExtractionResult
from app.ingestion import split_passages

_VALUE_RE = re.compile(r"\$\s*([\d,]+(?:\.\d+)?)\s*(billion|million)", re.IGNORECASE)


def _parse_value(passage: str) -> tuple[float | None, str | None]:
    m = _VALUE_RE.search(passage)
    if not m:
        return None, None
    number = float(m.group(1).replace(",", ""))
    unit = "usd_billions" if m.group(2).lower() == "billion" else "usd_millions"
    return number, unit


def _entities_in_order(passage: str, known_entities: list[str]) -> list[str]:
    found = [(passage.find(e), e) for e in known_entities if e in passage]
    return [e for _, e in sorted(found)]


def propose_candidates(
    document_text: str, known_entities: list[str], document_id: str = "doc"
) -> ExtractionResult:
    candidates: list[CandidateEdge] = []
    for passage in split_passages(document_text):
        matched = _entities_in_order(passage.text, known_entities)
        if len(matched) < 2:
            continue
        value, unit = _parse_value(passage.text)
        candidates.append(
            CandidateEdge(
                source_entity=matched[0],
                target_entity=matched[1],
                relationship_type="operational_dependency",
                metric="mentioned_relationship",
                value=value,
                unit=unit,
                period=None,
                exact_passage=passage.text,
                document_id=document_id,
                permitted_operation="record the disclosed relationship for human review",
                unsupported_operation="treat as a quantified propagation without evidence",
                missing_information=["propagation"],
                evidence_class="reported" if value is not None else "unknown",
                confidence_note="deterministic keyword proposer (offline fallback)",
            )
        )
    return ExtractionResult(candidates=candidates)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_extraction_fallback.py -v`
Expected: PASS (all four tests).

- [ ] **Step 5: Commit**

```bash
git add app/extraction/fallback.py tests/test_extraction_fallback.py
git commit -m "feat(revamp/backend): add deterministic offline extraction fallback"
```

---

### Task 4: Provider-agnostic adapter + OpenAI branch

**Files:**
- Create: `revamp/backend/app/extraction/adapter.py`
- Modify: `revamp/backend/app/config.py` (add `openai_model`)
- Create: `revamp/backend/tests/test_extraction_adapter.py`

**Interfaces:**
- Consumes: `app.config.settings`, `app.extraction.schema.ExtractionResult`, `app.extraction.fallback.propose_candidates`.
- Produces:
  - `app.extraction.adapter.extract_candidates(document_text, known_entities, document_id="doc", *, client=None, provider=None) -> ExtractionResult` — dispatch on `provider or settings.llm_provider`. `"fallback"` → `propose_candidates`. `"openai"` → `_extract_openai`. Anything else → `ValueError`.
  - `app.extraction.adapter.build_messages(document_text, known_entities) -> list[dict]` — system prompt (§6 core instructions) + user message with the document text and known-entity list.
  - `app.extraction.adapter._extract_openai(document_text, known_entities, document_id, client=None) -> ExtractionResult` — `client = client or OpenAI()`; call `client.chat.completions.create(model=settings.openai_model, temperature=0, response_format={json_schema, strict}, messages=build_messages(...))`; parse `resp.choices[0].message.content` via `ExtractionResult.model_validate_json`.
- Config addition: `settings.openai_model: str = "gpt-4o-2024-08-06"`.

- [ ] **Step 1: Add config field**

Modify `revamp/backend/app/config.py` — add one field to `Settings` (below `openai_api_key`):

```python
    openai_model: str = "gpt-4o-2024-08-06"
```

- [ ] **Step 2: Write the failing test**

Create `revamp/backend/tests/test_extraction_adapter.py`:

```python
import types

import pytest

from app.extraction.adapter import build_messages, extract_candidates


def _fake_openai_client(json_payload: str):
    """A stand-in with the minimal .chat.completions.create surface we call."""
    message = types.SimpleNamespace(content=json_payload)
    choice = types.SimpleNamespace(message=message)
    response = types.SimpleNamespace(choices=[choice])

    class _Completions:
        def create(self, **kwargs):
            self.last_kwargs = kwargs
            return response

    completions = _Completions()
    chat = types.SimpleNamespace(completions=completions)
    return types.SimpleNamespace(chat=chat), completions


def test_fallback_provider_routes_to_proposer():
    text = "OpenAI committed $11.9 billion to CoreWeave."
    result = extract_candidates(text, ["OpenAI", "CoreWeave"], provider="fallback")
    assert len(result.candidates) == 1
    assert result.candidates[0].value == 11.9


def test_unknown_provider_raises():
    with pytest.raises(ValueError):
        extract_candidates("x", [], provider="does_not_exist")


def test_openai_branch_maps_response_from_injected_client():
    payload = (
        '{"candidates": [{"source_entity": "OpenAI", "target_entity": "CoreWeave",'
        ' "relationship_type": "purchase_obligation", "metric": "contract_value",'
        ' "value": 11.9, "unit": "usd_billions", "period": "through_2030",'
        ' "exact_passage": "OpenAI committed $11.9 billion to CoreWeave.",'
        ' "document_id": "s1", "permitted_operation": "x", "unsupported_operation": "y",'
        ' "missing_information": ["PD"], "evidence_class": "reported", "confidence_note": "z"}]}'
    )
    client, completions = _fake_openai_client(payload)
    result = extract_candidates(
        "OpenAI committed $11.9 billion to CoreWeave.",
        ["OpenAI", "CoreWeave"],
        document_id="s1",
        provider="openai",
        client=client,
    )
    assert len(result.candidates) == 1
    assert result.candidates[0].relationship_type == "purchase_obligation"
    # The request used temperature 0 and a structured response_format.
    assert completions.last_kwargs["temperature"] == 0
    assert completions.last_kwargs["response_format"]["type"] == "json_schema"


def test_build_messages_includes_entities_and_text():
    msgs = build_messages("SOME DOC TEXT", ["OpenAI", "CoreWeave"])
    assert msgs[0]["role"] == "system"
    joined = " ".join(m["content"] for m in msgs)
    assert "SOME DOC TEXT" in joined
    assert "OpenAI" in joined
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_extraction_adapter.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.extraction.adapter'`.

- [ ] **Step 4: Write the adapter**

Create `revamp/backend/app/extraction/adapter.py`:

```python
from app.config import settings
from app.extraction.fallback import propose_candidates
from app.extraction.schema import ExtractionResult

SYSTEM_PROMPT = (
    "You extract structured financial-relationship claims from filings. You never "
    "estimate, infer, or calculate a number that is not explicitly stated in the passage "
    "you cite. exact_passage must be copied verbatim from the provided document text — if "
    "you cannot find a verbatim supporting passage, do not emit the candidate. Every "
    "relationship must map to exactly one relationship_type from the provided enum. Set "
    'evidence_class to "calculated" only if every input number is itself quoted in '
    "exact_passage, and show the operation in permitted_operation. Never propose a "
    "behavioural_response edge with a value — those must have value null and evidence_class "
    '"unknown" unless the filing explicitly states an elasticity or ratio. When uncertain, '
    "prefer fewer, well-evidenced candidates over many speculative ones."
)


def build_messages(document_text: str, known_entities: list[str]) -> list[dict]:
    entities = ", ".join(known_entities) if known_entities else "(none provided)"
    user = (
        f"Known entities: {entities}\n\n"
        f"Extract candidate relationship edges from this document text:\n\n{document_text}"
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user},
    ]


def _extract_openai(
    document_text: str, known_entities: list[str], document_id: str, client=None
) -> ExtractionResult:
    if client is None:
        from openai import OpenAI

        client = OpenAI(api_key=settings.openai_api_key)
    response = client.chat.completions.create(
        model=settings.openai_model,
        temperature=0,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "extraction_result",
                "strict": True,
                "schema": ExtractionResult.model_json_schema(),
            },
        },
        messages=build_messages(document_text, known_entities),
    )
    return ExtractionResult.model_validate_json(response.choices[0].message.content)


def extract_candidates(
    document_text: str,
    known_entities: list[str],
    document_id: str = "doc",
    *,
    client=None,
    provider: str | None = None,
) -> ExtractionResult:
    provider = provider or settings.llm_provider
    if provider == "fallback":
        return propose_candidates(document_text, known_entities, document_id)
    if provider == "openai":
        return _extract_openai(document_text, known_entities, document_id, client=client)
    raise ValueError(f"unknown LLM provider: {provider}")
```

Note on live use: `ExtractionResult.model_json_schema()` may need `additionalProperties: false` / all-fields-required massaging for OpenAI strict mode; that is a live-integration detail (plan §17) exercised only with a real key, out of scope for these offline tests. The injectable-client seam keeps the tests deterministic.

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run pytest tests/test_extraction_adapter.py -v`
Expected: PASS (all four tests).

- [ ] **Step 6: Run the full suite and commit**

Run: `uv run pytest`
Expected: all Sub-project 1 + Sub-project 2 tests green.

```bash
git add app/extraction/adapter.py app/config.py tests/test_extraction_adapter.py
git commit -m "feat(revamp/backend): add provider-agnostic extract_candidates adapter"
```

---

## Acceptance (whole sub-project)

- `extract_pdf_text` reads a real generated PDF; `split_passages` offsets round-trip.
- `CandidateEdge`/`ExtractionResult` enforce the §6 enums and field set.
- `extract_candidates(..., provider="fallback")` runs fully offline and returns verbatim-cited candidates.
- `extract_candidates(..., provider="openai", client=fake)` maps a structured response to `ExtractionResult` with temperature 0 and json_schema response_format — no network/key needed in tests.
- Unknown provider raises `ValueError`.
- `uv run pytest` — all green.
- Live OpenAI path (real key) is wired but validated manually later, not in the offline suite.
