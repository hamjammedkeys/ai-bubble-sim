# Sub-project 3: Verification + Approval + Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn extracted candidates into a reviewable, gated graph: a pure-code verifier (§7), a persistence service that writes candidates as `status='candidate'` edges with verification attached, a candidate→approved/rejected/edited state machine, and the REST endpoints (§11) to ingest documents, extract candidates, list the graph, and approve/reject/edit.

**Architecture:** New pure modules `app/verification.py` (§7 checks over text — no LLM, no DB) and services `app/services/candidates.py` (ExtractionResult → edge rows) and `app/services/review.py` (state transitions). Two FastAPI routers `app/routers/documents.py` and `app/routers/edges.py`, wired into `app/main.py`, using a `get_session` DB dependency. Everything reads/writes the Sub-project 1 ORM and consumes Sub-project 2's `extract_candidates`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 (SQLite), Pydantic v2, rapidfuzz. Builds on SP1 (models, db, schemas) and SP2 (extraction adapter, ingestion).

## Global Constraints

- Work only inside `revamp/backend/`. Never touch files outside `revamp/`.
- The verifier is **pure code, no LLM** (plan §7): passage existence (rapidfuzz `partial_ratio` ≥ 92), number presence, entity presence, unit consistency, arithmetic (only when `evidence_class=="calculated"`), source validity. It returns a `dict` stored as `edges.verification` JSON; a failing check **flags** (does not auto-reject).
- Only `status='approved'` edges are ever treated as evidence-backed (plan §4). Candidates are never auto-approved. Approve/Reject/Edit is the human semantic gate (CONTEXT: mechanical-check-vs-semantic-review).
- State machine: a `candidate` edge may become `approved` or `rejected`; `edit` updates fields, **re-runs the verifier**, and keeps status `candidate`. Approving/rejecting a non-`candidate` edge is a `409`. Editing a non-`candidate` edge is a `409`.
- Endpoints (plan §11 subset for this sub-project): `GET /entities`, `POST /documents`, `POST /documents/{id}/extract`, `GET /edges`, `GET /edges/{id}`, `GET /edges/candidates`, `POST /edges/{id}/approve`, `POST /edges/{id}/reject`, `POST /edges/{id}/edit`.
- `POST /documents` accepts JSON (`title` + `raw_text` + optional metadata) — no PDF parsing in this sub-project's tests; PDF upload is a thin later addition. Extraction uses `settings.llm_provider` (default `openai`); tests force `provider="fallback"` by passing it through, so no network/key is needed.
- Tests use an isolated SQLite DB per test via a `get_session` dependency override (fixture in `tests/conftest.py`); never write the app's real `fragilitygraph.db`.
- Run commands from `revamp/backend/`. Test command: `uv run pytest`. TDD: failing test first, commit after each green task.

---

### Task 1: Verifier (§7 mechanical checks)

**Files:**
- Create: `revamp/backend/app/verification.py`
- Create: `revamp/backend/tests/test_verification.py`

**Interfaces:**
- Consumes: `app.extraction.schema.CandidateEdge`.
- Produces:
  - `app.verification.ALLOWED_UNITS: set[str | None]`.
  - `app.verification.verify_candidate(candidate: CandidateEdge, document_text: str, document_exists: bool) -> dict` — returns a dict with keys `passage_found: bool`, `match_score: float`, `number_found: bool | None`, `entities_found: bool`, `unit_allowed: bool`, `arithmetic_ok: bool | None`, `source_valid: bool`, `overall: "pass" | "flag"`. `overall` is `"pass"` only when every non-`None` hard check passes (hard checks: passage_found, entities_found, unit_allowed, source_valid, and number_found when the candidate has a value).

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_verification.py`:

```python
from app.extraction.schema import CandidateEdge
from app.verification import verify_candidate


def _candidate(**over) -> CandidateEdge:
    base = dict(
        source_entity="OpenAI",
        target_entity="CoreWeave",
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through_2030",
        exact_passage="OpenAI committed $11.9 billion to CoreWeave through 2030.",
        document_id="doc-1",
        permitted_operation="report ceiling as exposure",
        unsupported_operation="treat as realized loss",
        missing_information=["PD", "LGD"],
        evidence_class="reported",
        confidence_note="verbatim",
    )
    base.update(over)
    return CandidateEdge(**base)


DOC = "In 2024, OpenAI committed $11.9 billion to CoreWeave through 2030 for compute."


def test_valid_candidate_passes():
    v = verify_candidate(_candidate(), DOC, document_exists=True)
    assert v["passage_found"] is True
    assert v["match_score"] >= 92
    assert v["number_found"] is True
    assert v["entities_found"] is True
    assert v["unit_allowed"] is True
    assert v["source_valid"] is True
    assert v["overall"] == "pass"


def test_fabricated_number_flags():
    # value not present in the passage
    v = verify_candidate(_candidate(value=99.9), DOC, document_exists=True)
    assert v["number_found"] is False
    assert v["overall"] == "flag"


def test_passage_not_in_document_flags():
    v = verify_candidate(_candidate(exact_passage="OpenAI acquired CoreWeave outright."), DOC, document_exists=True)
    assert v["passage_found"] is False
    assert v["overall"] == "flag"


def test_missing_document_flags():
    v = verify_candidate(_candidate(), DOC, document_exists=False)
    assert v["source_valid"] is False
    assert v["overall"] == "flag"


def test_null_value_skips_number_check():
    v = verify_candidate(_candidate(value=None, unit=None, evidence_class="unknown"), DOC, document_exists=True)
    assert v["number_found"] is None
    assert v["overall"] == "pass"


def test_bad_unit_flags():
    v = verify_candidate(_candidate(unit="bananas"), DOC, document_exists=True)
    assert v["unit_allowed"] is False
    assert v["overall"] == "flag"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_verification.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.verification'`.

- [ ] **Step 3: Write the verifier**

Create `revamp/backend/app/verification.py`:

```python
import re

from rapidfuzz import fuzz

from app.extraction.schema import CandidateEdge

ALLOWED_UNITS: set[str | None] = {
    "usd_billions",
    "usd_millions",
    "usd",
    "percent",
    "shares",
    "ownership_pct",
    None,
}

_PASSAGE_MATCH_THRESHOLD = 92


def _value_forms(value: float) -> list[str]:
    """String forms of a number to search for in a passage."""
    forms = {repr(value), str(value)}
    if value == int(value):
        forms.add(str(int(value)))
    # 11.9 -> "11.9"; strip trailing ".0" already handled by int form
    forms.add(f"{value:.1f}")
    forms.add(f"{value:,.1f}")
    return [f for f in forms if f]


def _value_in_text(value: float, text: str) -> bool:
    return any(form in text for form in _value_forms(value))


def verify_candidate(candidate: CandidateEdge, document_text: str, document_exists: bool) -> dict:
    score = fuzz.partial_ratio(candidate.exact_passage, document_text)
    passage_found = score >= _PASSAGE_MATCH_THRESHOLD

    if candidate.value is None:
        number_found: bool | None = None
    else:
        number_found = _value_in_text(candidate.value, candidate.exact_passage)

    entities_found = (
        candidate.source_entity in candidate.exact_passage
        and candidate.target_entity in candidate.exact_passage
    )
    unit_allowed = candidate.unit in ALLOWED_UNITS

    # Arithmetic re-derivation is only defined when the candidate claims a calculation.
    # Without the quoted input operands we cannot re-derive here, so we do not assert it
    # as a hard pass/fail: report None (not applicable) rather than fabricate a verdict.
    arithmetic_ok: bool | None = None

    hard_checks = [passage_found, entities_found, unit_allowed, document_exists]
    if number_found is not None:
        hard_checks.append(number_found)

    return {
        "passage_found": passage_found,
        "match_score": round(float(score), 1),
        "number_found": number_found,
        "entities_found": entities_found,
        "unit_allowed": unit_allowed,
        "arithmetic_ok": arithmetic_ok,
        "source_valid": document_exists,
        "overall": "pass" if all(hard_checks) else "flag",
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_verification.py -v`
Expected: PASS (all six tests).

- [ ] **Step 5: Commit**

```bash
git add app/verification.py tests/test_verification.py
git commit -m "feat(revamp/backend): add pure-code candidate verifier (section 7)"
```

---

### Task 2: Candidate persistence service

**Files:**
- Create: `revamp/backend/app/services/__init__.py`
- Create: `revamp/backend/app/services/candidates.py`
- Create: `revamp/backend/tests/conftest.py`
- Create: `revamp/backend/tests/test_candidates_service.py`

**Interfaces:**
- Consumes: `app.models` (Entity, Document, Passage, Edge), `app.extraction.schema.ExtractionResult`, `app.verification.verify_candidate`.
- Produces:
  - `app.services.candidates.get_or_create_entity(session, name) -> Entity` — upsert by unique `name` (default `entity_type=None`).
  - `app.services.candidates.persist_candidates(session, result: ExtractionResult, document: Document) -> list[Edge]` — for each candidate: upsert source/target entities, create a `Passage` (text = `exact_passage`), create an `Edge` with `status='candidate'`, fields copied from the candidate, `passage_id`/`document_id` set, and `verification` = `verify_candidate(candidate, document.raw_text, document_exists=True)`. Commits and returns the created edges.
- Test fixture (`conftest.py`):
  - `db_session` — a function-scoped fixture yielding a SQLAlchemy `Session` bound to a fresh temp-file SQLite engine with all tables created (via `Base.metadata.create_all`), so no test writes the app's real DB.

- [ ] **Step 1: Write the conftest fixture**

Create `revamp/backend/tests/conftest.py`:

```python
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app import models  # noqa: F401  # register tables on Base.metadata


@pytest.fixture
def db_engine(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path/'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_session(db_engine):
    session = Session(db_engine)
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 2: Write the failing test**

Create `revamp/backend/tests/test_candidates_service.py`:

```python
from app.extraction.schema import CandidateEdge, ExtractionResult
from app.models import Document, Edge, Entity
from app.services.candidates import persist_candidates


def _result() -> ExtractionResult:
    c = CandidateEdge(
        source_entity="OpenAI",
        target_entity="CoreWeave",
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through_2030",
        exact_passage="OpenAI committed $11.9 billion to CoreWeave through 2030.",
        document_id="doc-1",
        permitted_operation="report ceiling as exposure",
        unsupported_operation="treat as realized loss",
        missing_information=["PD"],
        evidence_class="reported",
        confidence_note="verbatim",
    )
    return ExtractionResult(candidates=[c])


def test_persist_creates_candidate_edge_with_verification(db_session):
    doc = Document(title="CoreWeave S-1", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    db_session.add(doc)
    db_session.flush()

    edges = persist_candidates(db_session, _result(), doc)

    assert len(edges) == 1
    e = db_session.get(Edge, edges[0].id)
    assert e.status == "candidate"
    assert e.relationship_type == "purchase_obligation"
    assert e.value == 11.9
    assert e.document_id == doc.id
    assert e.passage_id is not None
    assert e.verification["overall"] == "pass"
    # entities were created and linked
    assert e.source_entity_id is not None
    assert e.target_entity_id is not None


def test_entities_are_deduplicated(db_session):
    doc = Document(title="d", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    db_session.add(doc)
    db_session.flush()

    persist_candidates(db_session, _result(), doc)
    persist_candidates(db_session, _result(), doc)

    assert db_session.query(Entity).filter_by(name="OpenAI").count() == 1
    assert db_session.query(Edge).count() == 2
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_candidates_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services'`.

- [ ] **Step 4: Write the service**

Create empty `revamp/backend/app/services/__init__.py`.

Create `revamp/backend/app/services/candidates.py`:

```python
from sqlalchemy.orm import Session

from app.extraction.schema import ExtractionResult
from app.models import Document, Edge, Entity, Passage
from app.verification import verify_candidate


def get_or_create_entity(session: Session, name: str) -> Entity:
    entity = session.query(Entity).filter_by(name=name).one_or_none()
    if entity is None:
        entity = Entity(name=name, aliases=[])
        session.add(entity)
        session.flush()
    return entity


def persist_candidates(session: Session, result: ExtractionResult, document: Document) -> list[Edge]:
    created: list[Edge] = []
    for candidate in result.candidates:
        source = get_or_create_entity(session, candidate.source_entity)
        target = get_or_create_entity(session, candidate.target_entity)

        passage = Passage(document_id=document.id, text=candidate.exact_passage)
        session.add(passage)
        session.flush()

        verification = verify_candidate(candidate, document.raw_text, document_exists=True)
        edge = Edge(
            source_entity_id=source.id,
            target_entity_id=target.id,
            relationship_type=candidate.relationship_type,
            metric=candidate.metric,
            value=candidate.value,
            unit=candidate.unit,
            period=candidate.period,
            evidence_class=candidate.evidence_class,
            permitted_operation=candidate.permitted_operation,
            unsupported_operation=candidate.unsupported_operation,
            passage_id=passage.id,
            document_id=document.id,
            status="candidate",
            verification=verification,
        )
        session.add(edge)
        created.append(edge)

    session.commit()
    for edge in created:
        session.refresh(edge)
    return created
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_candidates_service.py -v`
Expected: PASS (both tests).

- [ ] **Step 6: Commit**

```bash
git add app/services/__init__.py app/services/candidates.py tests/conftest.py tests/test_candidates_service.py
git commit -m "feat(revamp/backend): persist extraction candidates as verified candidate edges"
```

---

### Task 3: Approval state machine service

**Files:**
- Create: `revamp/backend/app/services/review.py`
- Create: `revamp/backend/tests/test_review_service.py`

**Interfaces:**
- Consumes: `app.models.Edge`, `app.models.Document`, `app.verification.verify_candidate`, `app.extraction.schema.CandidateEdge`.
- Produces (each raises `app.services.review.InvalidTransition` — subclass of `ValueError` — when the edge is not in status `candidate`):
  - `approve_edge(session, edge_id, reviewed_by=None) -> Edge` — sets `status="approved"`, `reviewed_by`, `reviewed_at=now`.
  - `reject_edge(session, edge_id, reviewed_by=None) -> Edge` — sets `status="rejected"`, `reviewed_by`, `reviewed_at=now`.
  - `edit_edge(session, edge_id, updates: dict) -> Edge` — updates the given mutable fields (`metric, value, unit, period, relationship_type, evidence_class, permitted_operation, unsupported_operation`), re-runs the verifier against the edge's document `raw_text`, updates `verification`, and keeps `status="candidate"`.
  - `EDITABLE_FIELDS: frozenset[str]`.
  - Looking up a missing edge id raises `KeyError`.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_review_service.py`:

```python
import pytest

from app.models import Document, Edge, Entity
from app.services.review import InvalidTransition, approve_edge, edit_edge, reject_edge


def _candidate_edge(session) -> Edge:
    src = Entity(name="OpenAI", aliases=[])
    tgt = Entity(name="CoreWeave", aliases=[])
    doc = Document(title="d", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    session.add_all([src, tgt, doc])
    session.flush()
    edge = Edge(
        source_entity_id=src.id,
        target_entity_id=tgt.id,
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through_2030",
        evidence_class="reported",
        document_id=doc.id,
        status="candidate",
        verification={"overall": "pass"},
    )
    session.add(edge)
    session.commit()
    return edge


def test_approve_sets_status_and_reviewer(db_session):
    edge = _candidate_edge(db_session)
    result = approve_edge(db_session, edge.id, reviewed_by="dawn")
    assert result.status == "approved"
    assert result.reviewed_by == "dawn"
    assert result.reviewed_at is not None


def test_reject_sets_status(db_session):
    edge = _candidate_edge(db_session)
    result = reject_edge(db_session, edge.id)
    assert result.status == "rejected"


def test_cannot_approve_already_approved(db_session):
    edge = _candidate_edge(db_session)
    approve_edge(db_session, edge.id)
    with pytest.raises(InvalidTransition):
        approve_edge(db_session, edge.id)


def test_edit_updates_fields_reruns_verifier_and_stays_candidate(db_session):
    edge = _candidate_edge(db_session)
    # change value to one NOT present in the passage -> verifier should flag
    result = edit_edge(db_session, edge.id, {"value": 99.9})
    assert result.status == "candidate"
    assert result.value == 99.9
    assert result.verification["number_found"] is False
    assert result.verification["overall"] == "flag"


def test_edit_rejected_edge_raises(db_session):
    edge = _candidate_edge(db_session)
    reject_edge(db_session, edge.id)
    with pytest.raises(InvalidTransition):
        edit_edge(db_session, edge.id, {"value": 5.0})


def test_missing_edge_raises_keyerror(db_session):
    with pytest.raises(KeyError):
        approve_edge(db_session, "does-not-exist")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_review_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.review'`.

- [ ] **Step 3: Write the service**

Create `revamp/backend/app/services/review.py` (note: the ORM defines FK columns only — no `relationship()` attributes — so `edit_edge` resolves entity names and passage text via explicit `session.get(...)` lookups, never `edge.source_entity`/`edge.passage`):

```python
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.extraction.schema import CandidateEdge
from app.models import Document, Edge, Entity, Passage
from app.verification import verify_candidate

EDITABLE_FIELDS: frozenset[str] = frozenset(
    {
        "metric",
        "value",
        "unit",
        "period",
        "relationship_type",
        "evidence_class",
        "permitted_operation",
        "unsupported_operation",
    }
)


class InvalidTransition(ValueError):
    """Raised when an edge is not in a state that permits the requested transition."""


def _get_edge(session: Session, edge_id: str) -> Edge:
    edge = session.get(Edge, edge_id)
    if edge is None:
        raise KeyError(edge_id)
    return edge


def _require_candidate(edge: Edge) -> None:
    if edge.status != "candidate":
        raise InvalidTransition(f"edge {edge.id} is '{edge.status}', not 'candidate'")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def approve_edge(session: Session, edge_id: str, reviewed_by: str | None = None) -> Edge:
    edge = _get_edge(session, edge_id)
    _require_candidate(edge)
    edge.status = "approved"
    edge.reviewed_by = reviewed_by
    edge.reviewed_at = _now()
    session.commit()
    session.refresh(edge)
    return edge


def reject_edge(session: Session, edge_id: str, reviewed_by: str | None = None) -> Edge:
    edge = _get_edge(session, edge_id)
    _require_candidate(edge)
    edge.status = "rejected"
    edge.reviewed_by = reviewed_by
    edge.reviewed_at = _now()
    session.commit()
    session.refresh(edge)
    return edge


def _rebuild_candidate(edge: Edge, source_name: str, target_name: str, passage_text: str) -> CandidateEdge:
    return CandidateEdge(
        source_entity=source_name,
        target_entity=target_name,
        relationship_type=edge.relationship_type,
        metric=edge.metric or "",
        value=edge.value,
        unit=edge.unit,
        period=edge.period,
        exact_passage=passage_text,
        document_id=edge.document_id or "",
        permitted_operation=edge.permitted_operation or "",
        unsupported_operation=edge.unsupported_operation or "",
        missing_information=[],
        evidence_class=edge.evidence_class,
        confidence_note="",
    )


def edit_edge(session: Session, edge_id: str, updates: dict) -> Edge:
    edge = _get_edge(session, edge_id)
    _require_candidate(edge)
    for field, value in updates.items():
        if field in EDITABLE_FIELDS:
            setattr(edge, field, value)
    session.flush()

    src = session.get(Entity, edge.source_entity_id) if edge.source_entity_id else None
    tgt = session.get(Entity, edge.target_entity_id) if edge.target_entity_id else None
    psg = session.get(Passage, edge.passage_id) if edge.passage_id else None
    document = session.get(Document, edge.document_id) if edge.document_id else None

    edge.verification = verify_candidate(
        _rebuild_candidate(
            edge,
            source_name=src.name if src else "",
            target_name=tgt.name if tgt else "",
            passage_text=psg.text if psg else "",
        ),
        document.raw_text if document else "",
        document_exists=document is not None,
    )
    edge.status = "candidate"
    session.commit()
    session.refresh(edge)
    return edge
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_review_service.py -v`
Expected: PASS (all six tests).

- [ ] **Step 5: Commit**

```bash
git add app/services/review.py tests/test_review_service.py
git commit -m "feat(revamp/backend): add candidate approve/reject/edit state machine"
```

---

### Task 4: Document + entity endpoints + app wiring

**Files:**
- Modify: `revamp/backend/app/schemas.py` (add request/response models)
- Create: `revamp/backend/app/routers/__init__.py`
- Create: `revamp/backend/app/routers/documents.py`
- Modify: `revamp/backend/app/main.py` (init_db on startup + include routers)
- Create: `revamp/backend/tests/test_documents_api.py`

**Interfaces:**
- Consumes: `app.db.get_session`, `app.services.candidates.persist_candidates`, `app.extraction.adapter.extract_candidates`, `app.models`.
- Produces schemas in `app.schemas`:
  - `DocumentIn(title: str, raw_text: str, filing_type: str | None = None, company: str | None = None, url: str | None = None, period: str | None = None)`
  - `DocumentOut(id, title, filing_type, company, period)` with `from_attributes=True`.
  - `ExtractResponse(document_id: str, candidates_created: int, provider: str)`
- Produces endpoints:
  - `GET /entities -> list[EntityOut]`
  - `POST /documents` (body `DocumentIn`) → `DocumentOut` (201), creates a `Document` row.
  - `POST /documents/{document_id}/extract?provider=...` → `ExtractResponse`; loads the document, calls `extract_candidates(document.raw_text, known_entities=[all entity names], document_id=document.id, provider=provider or settings.llm_provider)`, persists via `persist_candidates`. `404` if the document id is unknown.
- Wires `app/main.py` to call `init_db()` on startup and `include_router` both routers.

- [ ] **Step 1: Add schemas**

Add to `revamp/backend/app/schemas.py` (keep existing `EntityOut`/`EdgeOut`):

```python
class DocumentIn(BaseModel):
    title: str
    raw_text: str
    filing_type: str | None = None
    company: str | None = None
    url: str | None = None
    period: str | None = None


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    filing_type: str | None = None
    company: str | None = None
    period: str | None = None


class ExtractResponse(BaseModel):
    document_id: str
    candidates_created: int
    provider: str
```

- [ ] **Step 2: Write the failing test**

Create `revamp/backend/tests/test_documents_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app
from app.models import Entity
from app import models  # noqa: F401


@pytest.fixture
def client(db_engine):
    def _override():
        session = Session(db_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_entities(db_engine, *names):
    s = Session(db_engine)
    s.add_all([Entity(name=n, aliases=[]) for n in names])
    s.commit()
    s.close()


def test_create_document_and_extract_with_fallback(client, db_engine):
    # Seed the two entities so the fallback proposer (which only matches known
    # entity names) can emit a candidate for the passage that mentions both.
    _seed_entities(db_engine, "OpenAI", "CoreWeave")

    doc_resp = client.post(
        "/documents",
        json={"title": "CoreWeave S-1", "raw_text": "OpenAI committed $11.9 billion to CoreWeave through 2030."},
    )
    assert doc_resp.status_code == 201
    doc_id = doc_resp.json()["id"]

    extract_resp = client.post(f"/documents/{doc_id}/extract", params={"provider": "fallback"})
    assert extract_resp.status_code == 200
    body = extract_resp.json()
    assert body["provider"] == "fallback"
    assert body["document_id"] == doc_id
    assert body["candidates_created"] == 1

    # verify the candidate landed in the DB (queried directly — the /edges review
    # endpoints are added in Task 5; this task's edges router is still a placeholder)
    from app.models import Edge

    s = Session(db_engine)
    try:
        edges = s.query(Edge).all()
        assert len(edges) == 1
        assert edges[0].status == "candidate"
        assert edges[0].value == 11.9
    finally:
        s.close()


def test_extract_unknown_document_404(client):
    resp = client.post("/documents/nope/extract", params={"provider": "fallback"})
    assert resp.status_code == 404


def test_list_entities_empty(client):
    resp = client.get("/entities")
    assert resp.status_code == 200
    assert resp.json() == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_documents_api.py -v`
Expected: FAIL — `ImportError`/`404` because routers/endpoints don't exist yet.

- [ ] **Step 4: Write the router**

Create empty `revamp/backend/app/routers/__init__.py`.

Create `revamp/backend/app/routers/documents.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.extraction.adapter import extract_candidates
from app.models import Document, Entity
from app.schemas import DocumentIn, DocumentOut, EntityOut, ExtractResponse
from app.services.candidates import persist_candidates

router = APIRouter()


@router.get("/entities", response_model=list[EntityOut])
def list_entities(session: Session = Depends(get_session)):
    return session.query(Entity).order_by(Entity.name).all()


@router.post("/documents", response_model=DocumentOut, status_code=201)
def create_document(payload: DocumentIn, session: Session = Depends(get_session)):
    document = Document(
        title=payload.title,
        raw_text=payload.raw_text,
        filing_type=payload.filing_type,
        company=payload.company,
        url=payload.url,
        period=payload.period,
    )
    session.add(document)
    session.commit()
    session.refresh(document)
    return document


@router.post("/documents/{document_id}/extract", response_model=ExtractResponse)
def extract_document(
    document_id: str,
    provider: str | None = None,
    session: Session = Depends(get_session),
):
    document = session.get(Document, document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="document not found")

    known_entities = [name for (name,) in session.query(Entity.name).all()]
    chosen_provider = provider or settings.llm_provider
    result = extract_candidates(
        document.raw_text,
        known_entities,
        document_id=document.id,
        provider=chosen_provider,
    )
    edges = persist_candidates(session, result, document)
    return ExtractResponse(
        document_id=document.id,
        candidates_created=len(edges),
        provider=chosen_provider,
    )
```

- [ ] **Step 5: Wire app/main.py**

Replace `revamp/backend/app/main.py` with (use a `lifespan` context manager, not the deprecated `@app.on_event("startup")`, to avoid a deprecation warning):

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import documents, edges


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="FragilityGraph API", lifespan=lifespan)

app.include_router(documents.router)
app.include_router(edges.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

Two notes:
- `app.routers.edges` is created in Task 5. To keep Task 4's suite green, create a **minimal placeholder** `revamp/backend/app/routers/edges.py` now containing just `from fastapi import APIRouter` and `router = APIRouter()`; Task 5 fills it in. (This keeps the import in `main.py` valid.)
- The test fixtures construct `TestClient(app)` **without** using it as a context manager (`with ...`), so Starlette does **not** run the `lifespan` startup — `init_db()` never fires in tests, so no real `fragilitygraph.db` is created. Tables come solely from the `db_engine` fixture's `create_all`. Do not wrap the TestClient in `with` in these tests.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest tests/test_documents_api.py -v`
Expected: PASS (all three tests).

- [ ] **Step 7: Run the full suite and commit**

Run: `uv run pytest`
Expected: all prior + new tests green.

```bash
git add app/schemas.py app/routers/__init__.py app/routers/documents.py app/routers/edges.py app/main.py tests/test_documents_api.py
git commit -m "feat(revamp/backend): document + entity endpoints, init_db on startup"
```

---

### Task 5: Edge review endpoints

**Files:**
- Modify: `revamp/backend/app/schemas.py` (add `EditEdgeIn`, `ReviewIn`)
- Modify: `revamp/backend/app/routers/edges.py` (replace placeholder with real endpoints)
- Create: `revamp/backend/tests/test_edges_api.py`

**Interfaces:**
- Consumes: `app.db.get_session`, `app.services.review` (approve/reject/edit + `InvalidTransition`), `app.models.Edge`, `app.schemas.EdgeOut`.
- Produces schemas:
  - `ReviewIn(reviewed_by: str | None = None)`
  - `EditEdgeIn` — all-optional editable fields (`metric, value, unit, period, relationship_type, evidence_class, permitted_operation, unsupported_operation`) plus `reviewed_by`. `.model_dump(exclude_unset=True)` yields the update dict.
- Produces endpoints:
  - `GET /edges?status=...` → `list[EdgeOut]` (filter by status when provided).
  - `GET /edges/candidates` → `list[EdgeOut]` where `status='candidate'`, newest first.
  - `GET /edges/{edge_id}` → `EdgeOut` (404 if unknown).
  - `POST /edges/{edge_id}/approve` (body `ReviewIn`) → `EdgeOut`; `409` on `InvalidTransition`, `404` on missing.
  - `POST /edges/{edge_id}/reject` (body `ReviewIn`) → `EdgeOut`; same error mapping.
  - `POST /edges/{edge_id}/edit` (body `EditEdgeIn`) → `EdgeOut`; re-verifies, stays candidate; `409`/`404` mapping.
  - Route ordering: declare `/edges/candidates` **before** `/edges/{edge_id}` so the literal path wins.

- [ ] **Step 1: Add schemas**

Add to `revamp/backend/app/schemas.py`:

```python
class ReviewIn(BaseModel):
    reviewed_by: str | None = None


class EditEdgeIn(BaseModel):
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    relationship_type: str | None = None
    evidence_class: str | None = None
    permitted_operation: str | None = None
    unsupported_operation: str | None = None
```

- [ ] **Step 2: Write the failing test**

Create `revamp/backend/tests/test_edges_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app
from app.models import Document, Edge, Entity
from app import models  # noqa: F401


@pytest.fixture
def client(db_engine):
    def _override():
        session = Session(db_engine)
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = _override
    yield TestClient(app)
    app.dependency_overrides.clear()


def _seed_candidate(db_engine) -> str:
    s = Session(db_engine)
    src = Entity(name="OpenAI", aliases=[])
    tgt = Entity(name="CoreWeave", aliases=[])
    doc = Document(title="d", raw_text="OpenAI committed $11.9 billion to CoreWeave through 2030.")
    s.add_all([src, tgt, doc])
    s.flush()
    edge = Edge(
        source_entity_id=src.id,
        target_entity_id=tgt.id,
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through_2030",
        evidence_class="reported",
        document_id=doc.id,
        status="candidate",
        verification={"overall": "pass"},
    )
    s.add(edge)
    s.commit()
    edge_id = edge.id
    s.close()
    return edge_id


def test_candidates_list_and_approve(client, db_engine):
    edge_id = _seed_candidate(db_engine)

    cand = client.get("/edges/candidates")
    assert cand.status_code == 200
    assert len(cand.json()) == 1
    assert cand.json()[0]["id"] == edge_id

    approve = client.post(f"/edges/{edge_id}/approve", json={"reviewed_by": "dawn"})
    assert approve.status_code == 200
    assert approve.json()["status"] == "approved"

    # now it is no longer a candidate
    assert client.get("/edges/candidates").json() == []
    # and re-approving is a conflict
    assert client.post(f"/edges/{edge_id}/approve", json={}).status_code == 409


def test_get_edge_and_filter_by_status(client, db_engine):
    edge_id = _seed_candidate(db_engine)
    assert client.get(f"/edges/{edge_id}").json()["id"] == edge_id
    assert client.get("/edges", params={"status": "approved"}).json() == []
    assert len(client.get("/edges", params={"status": "candidate"}).json()) == 1


def test_reject_and_missing(client, db_engine):
    edge_id = _seed_candidate(db_engine)
    assert client.post(f"/edges/{edge_id}/reject", json={}).json()["status"] == "rejected"
    assert client.get("/edges/does-not-exist").status_code == 404
    assert client.post("/edges/does-not-exist/approve", json={}).status_code == 404


def test_edit_reruns_verification(client, db_engine):
    edge_id = _seed_candidate(db_engine)
    resp = client.post(f"/edges/{edge_id}/edit", json={"value": 99.9})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "candidate"
    assert body["value"] == 99.9
    assert body["verification"]["overall"] == "flag"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_edges_api.py -v`
Expected: FAIL — endpoints return 404/405 (placeholder router has no routes).

- [ ] **Step 4: Write the router**

Replace `revamp/backend/app/routers/edges.py` with:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Edge
from app.schemas import EditEdgeIn, EdgeOut, ReviewIn
from app.services.review import InvalidTransition, approve_edge, edit_edge, reject_edge

router = APIRouter()


@router.get("/edges", response_model=list[EdgeOut])
def list_edges(status: str | None = None, session: Session = Depends(get_session)):
    query = session.query(Edge)
    if status is not None:
        query = query.filter(Edge.status == status)
    return query.order_by(Edge.created_at.desc()).all()


@router.get("/edges/candidates", response_model=list[EdgeOut])
def list_candidates(session: Session = Depends(get_session)):
    return (
        session.query(Edge)
        .filter(Edge.status == "candidate")
        .order_by(Edge.created_at.desc())
        .all()
    )


@router.get("/edges/{edge_id}", response_model=EdgeOut)
def get_edge(edge_id: str, session: Session = Depends(get_session)):
    edge = session.get(Edge, edge_id)
    if edge is None:
        raise HTTPException(status_code=404, detail="edge not found")
    return edge


def _apply(action, session, edge_id, **kwargs) -> Edge:
    try:
        return action(session, edge_id, **kwargs)
    except KeyError:
        raise HTTPException(status_code=404, detail="edge not found")
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))


@router.post("/edges/{edge_id}/approve", response_model=EdgeOut)
def approve(edge_id: str, payload: ReviewIn, session: Session = Depends(get_session)):
    return _apply(approve_edge, session, edge_id, reviewed_by=payload.reviewed_by)


@router.post("/edges/{edge_id}/reject", response_model=EdgeOut)
def reject(edge_id: str, payload: ReviewIn, session: Session = Depends(get_session)):
    return _apply(reject_edge, session, edge_id, reviewed_by=payload.reviewed_by)


@router.post("/edges/{edge_id}/edit", response_model=EdgeOut)
def edit(edge_id: str, payload: EditEdgeIn, session: Session = Depends(get_session)):
    updates = payload.model_dump(exclude_unset=True)
    try:
        return edit_edge(session, edge_id, updates)
    except KeyError:
        raise HTTPException(status_code=404, detail="edge not found")
    except InvalidTransition as exc:
        raise HTTPException(status_code=409, detail=str(exc))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `uv run pytest tests/test_edges_api.py -v`
Expected: PASS (all four tests).

- [ ] **Step 6: Run the full suite and commit**

Run: `uv run pytest`
Expected: all green.

```bash
git add app/schemas.py app/routers/edges.py tests/test_edges_api.py
git commit -m "feat(revamp/backend): edge review endpoints (list/get/candidates/approve/reject/edit)"
```

---

## Acceptance (whole sub-project)

- Verifier flags fabricated numbers, missing passages, bad units, and missing source documents; passes clean candidates; never auto-rejects.
- `persist_candidates` writes candidate edges with verification attached and deduplicates entities.
- Approve/reject/edit enforce the candidate-only transition (`409` otherwise); edit re-runs the verifier and stays candidate.
- Endpoints: create a document, extract (fallback, offline), list entities/edges/candidates, get one edge, approve/reject/edit — all wired and status-mapped (`404`/`409`).
- `uv run pytest` — all green, offline (no network/key).
