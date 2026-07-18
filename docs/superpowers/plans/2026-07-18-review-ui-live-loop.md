# Review-UI Live Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the ADR 0006 loop end-to-end — paste a filing, get typed cited candidates, see the mechanical checklist and highlighted passage, Approve one / Reject one, and have the approved edge visibly activate exposure in the OpenAI credit-event shock while the rejected edge stays out of the simulator.

**Architecture:** Add a deterministic, network-free `RelationshipProposer` implementation so "upload a filing → candidates" works offline in tests and on stage; expose the existing verifier/lifecycle/`promote_approved` backend through a thin FastAPI `/api/extraction/*` review router backed by an in-process `CandidateLifecycle`; add a `/api/scenario/credit-event` endpoint that runs `run_compound_shock` over a seeded hero graph **plus** promoted approved candidates; and add a React review panel plus tier-aware rendering that makes the approve/reject consequence visible on the map.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic v2, pytest, `fastapi.testclient.TestClient`, Ruff. Frontend: Vite + React 18 + TypeScript, Vitest, `@testing-library/react`, Cytoscape. No new dependencies; no LLM/network call anywhere in the test path.

## Global Constraints

- Governed by ADR 0006 (LLM proposes, code verifies, human gates) and ADRs 0001–0005. Code never promotes its own proposal; only an `APPROVED`/`EDITED` mechanically-valid candidate may enter the simulator via `promote_approved`.
- **Aggregate-shock guardrail (ADR 0004):** the OpenAI credit event is an aggregate compound shock and `run_compound_shock` intentionally skips `customer_concentration`. The edge whose activation the demo hinges on is therefore `take_or_pay` (OpenAI→CoreWeave). Do not "fix" this by making concentration quantify under the compound shock.
- **Impact vs Exposure (ADR 0005):** equity-method output is a solid-red *impact* (a forced loss); take-or-pay output is a solid-orange *exposure* (an amount placed at risk, never printed as a realized loss). The API and UI must keep these as distinct kinds and never sum orange into red.
- Every verification result keeps `semantic_interpretation == "pending_human_review"`; passing mechanical checks never implies semantic correctness.
- Reject/edit require a non-empty reviewer id and reason; every transition appends an immutable audit event.
- No network or filesystem I/O inside the proposer or verifier; the default proposer is deterministic.
- Money is expressed in USD millions everywhere in the engine (e.g. `245_000` = $245B, `10_000` = $10B, `11_900` = $11.9B, `ownership_share=0.27`).
- Python: `pyproject.toml` sets `pythonpath=["src"]`, `testpaths=["tests"]`; Ruff `line-length=100`, `target-version=py311`, lint select `["E","F","I","UP","B"]`. Run `make test` and `make lint`. Frontend: `npm --prefix frontend run test -- --run`.
- Existing endpoints (`/api/graph`, `/api/scenario/cloud-slowdown`) and all current tests remain green; new work is additive.
- Every task ends with its named focused test, the stated full suite/lint, and a commit.

---

### Task 1: Deterministic default proposer (network-free)

**Files:**
- Create: `src/fragility_map/extraction/proposers.py`
- Modify: `src/fragility_map/extraction/__init__.py`
- Create: `tests/fixtures/coreweave_s1a_excerpt.txt`
- Test: `tests/test_relationship_extraction.py` (append; leave existing tests unchanged)

**Interfaces:**
- Consumes: `RelationshipCandidateV2`, `CandidateStatus`, `RelationshipProposer` from `fragility_map.extraction.candidates`.
- Produces: `KeywordProposer` implementing `propose(self, source_id: str, filing_text: str) -> list[RelationshipCandidateV2]`, constructed as `KeywordProposer(source_accession: str, source_company_id: str, target_company_id: str)`. It scans `filing_text` and emits, when present:
  - a `take_or_pay` candidate for a `"$<n> billion"` purchase-commitment sentence (`value` in USD millions, `unit="USD"`), and
  - a `customer_concentration` candidate for a `"<nn>% of ... revenue"` sentence (`value` = the percent as a fraction, e.g. `0.62`, `unit=None`).
  Each candidate's `quoted_text` is the exact sentence it matched; `candidate_id` is `f"{source_id}-{relationship_type}"`; `unsupported_inference` holds a fixed over-reach template per type.

- [ ] **Step 1: Create the fixture**

Create `tests/fixtures/coreweave_s1a_excerpt.txt` with this exact content:

```text
Our business is concentrated among a limited number of customers. Microsoft accounted for 62% of our revenue in 2024. We have entered into purchase commitments of $11.9 billion through 2030 with OpenAI to secure dedicated compute capacity. These arrangements are described elsewhere in this prospectus.
```

- [ ] **Step 2: Write the failing test**

Append to `tests/test_relationship_extraction.py`:

```python
from fragility_map.extraction.proposers import KeywordProposer


def test_keyword_proposer_extracts_take_or_pay_and_concentration() -> None:
    text = Path("tests/fixtures/coreweave_s1a_excerpt.txt").read_text(encoding="utf-8")
    proposer = KeywordProposer(
        source_accession="0001640147-25-000001",
        source_company_id="openai",
        target_company_id="coreweave",
    )
    candidates = proposer.propose("coreweave-s1a", text)
    by_type = {c.relationship_type: c for c in candidates}

    top = by_type["take_or_pay"]
    assert top.value == 11_900
    assert top.unit == "USD"
    assert top.quoted_text in text
    assert top.status is CandidateStatus.PROPOSED

    conc = by_type["customer_concentration"]
    assert conc.value == 0.62
    assert conc.quoted_text == "Microsoft accounted for 62% of our revenue in 2024."
```

- [ ] **Step 3: Run the focused test to verify it fails**

Run: `pytest tests/test_relationship_extraction.py::test_keyword_proposer_extracts_take_or_pay_and_concentration -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map.extraction.proposers'`.

- [ ] **Step 4: Implement the proposer**

Create `src/fragility_map/extraction/proposers.py`:

```python
import re

from fragility_map.extraction.candidates import RelationshipCandidateV2

_SENTENCE = re.compile(r"[^.]*\.")
_BILLION = re.compile(r"\$([0-9]+(?:\.[0-9]+)?)\s*billion", re.IGNORECASE)
_PERCENT = re.compile(r"([0-9]+(?:\.[0-9]+)?)%\s+of\s+(?:our\s+)?revenue", re.IGNORECASE)


def _sentences(text: str) -> list[str]:
    return [match.group(0).strip() for match in _SENTENCE.finditer(text)]


class KeywordProposer:
    """Deterministic, network-free proposer. The seam where an LLM adapter can later
    be swapped in behind the RelationshipProposer protocol."""

    def __init__(
        self, source_accession: str, source_company_id: str, target_company_id: str
    ) -> None:
        self._accession = source_accession
        self._source_company_id = source_company_id
        self._target_company_id = target_company_id

    def _base(self, source_id: str, relationship_type: str, quoted_text: str) -> dict:
        return {
            "candidate_id": f"{source_id}-{relationship_type}",
            "source_id": source_id,
            "source_accession": self._accession,
            "source_company_id": self._source_company_id,
            "target_company_id": self._target_company_id,
            "relationship_type": relationship_type,
            "quoted_text": quoted_text,
        }

    def propose(self, source_id: str, filing_text: str) -> list[RelationshipCandidateV2]:
        candidates: list[RelationshipCandidateV2] = []
        for sentence in _sentences(filing_text):
            billion = _BILLION.search(sentence)
            if billion is not None:
                token = billion.group(0)
                value = float(billion.group(1)) * 1_000
                candidates.append(
                    RelationshipCandidateV2(
                        **self._base(source_id, "take_or_pay", sentence),
                        numeric_token=token,
                        value=value,
                        unit="USD",
                        period="through 2030" if "2030" in sentence else None,
                        supported_rule="disclosed purchase-commitment envelope",
                        unsupported_inference=(
                            "the full envelope becomes a realized loss on distress"
                        ),
                    )
                )
                continue
            percent = _PERCENT.search(sentence)
            if percent is not None:
                candidates.append(
                    RelationshipCandidateV2(
                        **self._base(source_id, "customer_concentration", sentence),
                        numeric_token=f"{percent.group(1)}%",
                        value=float(percent.group(1)) / 100,
                        unit=None,
                        period=None,
                        supported_rule="disclosed customer-concentration percentage",
                        unsupported_inference=(
                            "the buyer's own revenue drives this counterparty's purchases"
                        ),
                    )
                )
        return candidates
```

Add to `src/fragility_map/extraction/__init__.py` an export of `KeywordProposer` alongside the existing exports (do not import any network client).

- [ ] **Step 5: Run tests and lint**

Run: `pytest tests/test_relationship_extraction.py -v` then `make lint`.

Expected: all extraction tests PASS; Ruff clean.

- [ ] **Step 6: Commit**

```bash
git add src/fragility_map/extraction/proposers.py src/fragility_map/extraction/__init__.py tests/fixtures/coreweave_s1a_excerpt.txt tests/test_relationship_extraction.py
git commit -m "feat(extraction): add deterministic keyword proposer"
```

---

### Task 2: Extraction review API — propose, verify, highlight

**Files:**
- Create: `src/fragility_map/api/review.py`
- Modify: `src/fragility_map/api/server.py` (mount the router)
- Test: `tests/test_review_api.py`

**Interfaces:**
- Consumes: `KeywordProposer`, `verify_candidate`, `SourceManifestEntry`, `CandidateLifecycle`, `RelationshipCandidateV2`.
- Produces a module-level `SESSION` (a `ReviewSession` dataclass holding a `CandidateLifecycle`, a `dict[str, str]` of `source_id -> filing_text`, and a `dict[str, SourceManifestEntry]`), a `reset_session()` helper for tests, and a `router: APIRouter`.
- Endpoint `POST /api/extraction/propose` with body `{source_id, source_accession, source_company_id, target_company_id, filing_text}` returns `{"candidates": [CandidateView, ...]}` where `CandidateView` is `{candidate, verification: {checks: [{name, passed, detail}], mechanically_valid, semantic_interpretation}, highlight: {start, end} | null}`. `highlight` is the `[start, end)` character span of `quoted_text` inside `filing_text`, or `null` if not found. Every returned candidate is submitted to the lifecycle in `PROPOSED` state.
- `CandidateView` and the request model are defined here and reused unchanged by Task 3 and the frontend.

- [ ] **Step 1: Write the failing test**

Create `tests/test_review_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from fragility_map.api import review
from fragility_map.api.server import app

client = TestClient(app)


def _propose() -> dict:
    review.reset_session()
    text = Path("tests/fixtures/coreweave_s1a_excerpt.txt").read_text(encoding="utf-8")
    response = client.post(
        "/api/extraction/propose",
        json={
            "source_id": "coreweave-s1a",
            "source_accession": "0001640147-25-000001",
            "source_company_id": "openai",
            "target_company_id": "coreweave",
            "filing_text": text,
        },
    )
    assert response.status_code == 200
    return response.json()


def test_propose_returns_verified_blue_striped_candidates() -> None:
    body = _propose()
    views = {c["candidate"]["relationship_type"]: c for c in body["candidates"]}

    top = views["take_or_pay"]
    assert top["candidate"]["status"] == "proposed"
    assert top["verification"]["mechanically_valid"] is True
    assert top["verification"]["semantic_interpretation"] == "pending_human_review"
    assert {c["name"] for c in top["verification"]["checks"]} == {
        "quoted_text", "numeric_token", "entities", "period", "unit",
        "arithmetic", "accession", "supersession",
    }
    quote = top["candidate"]["quoted_text"]
    start, end = top["highlight"]["start"], top["highlight"]["end"]
    filing = _propose  # sanity: highlight indexes the submitted text
    assert end - start == len(quote)
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_review_api.py::test_propose_returns_verified_blue_striped_candidates -v`

Expected: FAIL with `ImportError`/404 because `fragility_map.api.review` and the route do not exist.

- [ ] **Step 3: Implement the router**

Create `src/fragility_map/api/review.py`:

```python
from dataclasses import dataclass, field

from fastapi import APIRouter
from pydantic import BaseModel, Field

from fragility_map.extraction.candidates import RelationshipCandidateV2
from fragility_map.extraction.lifecycle import CandidateLifecycle
from fragility_map.extraction.proposers import KeywordProposer
from fragility_map.extraction.verifier import (
    SourceManifestEntry,
    VerificationResult,
    verify_candidate,
)

router = APIRouter(prefix="/api/extraction")


@dataclass
class ReviewSession:
    lifecycle: CandidateLifecycle = field(default_factory=CandidateLifecycle)
    filings: dict[str, str] = field(default_factory=dict)
    manifest: dict[str, SourceManifestEntry] = field(default_factory=dict)


SESSION = ReviewSession()


def reset_session() -> None:
    global SESSION
    SESSION = ReviewSession()


class ProposeRequest(BaseModel):
    source_id: str = Field(min_length=1)
    source_accession: str = Field(min_length=1)
    source_company_id: str = Field(min_length=1)
    target_company_id: str = Field(min_length=1)
    filing_text: str = Field(min_length=1)


def _verification_view(result: VerificationResult) -> dict:
    return {
        "checks": [
            {"name": c.name, "passed": c.passed, "detail": c.detail} for c in result.checks
        ],
        "mechanically_valid": result.mechanically_valid,
        "semantic_interpretation": result.semantic_interpretation,
    }


def _highlight(filing_text: str, candidate: RelationshipCandidateV2) -> dict | None:
    start = filing_text.find(candidate.quoted_text)
    if start < 0:
        return None
    return {"start": start, "end": start + len(candidate.quoted_text)}


@router.post("/propose")
def propose(request: ProposeRequest) -> dict:
    entry = SourceManifestEntry(request.source_accession, request.source_id)
    SESSION.filings[request.source_id] = request.filing_text
    SESSION.manifest[request.source_accession] = entry
    proposer = KeywordProposer(
        request.source_accession, request.source_company_id, request.target_company_id
    )
    views = []
    for candidate in proposer.propose(request.source_id, request.filing_text):
        result = verify_candidate(request.filing_text, candidate, [entry])
        SESSION.lifecycle.submit(candidate, result)
        views.append(
            {
                "candidate": candidate.model_dump(mode="json"),
                "verification": _verification_view(result),
                "highlight": _highlight(request.filing_text, candidate),
            }
        )
    return {"candidates": views}
```

Mount it in `src/fragility_map/api/server.py` by adding after `app = FastAPI(...)`:

```python
from fragility_map.api.review import router as review_router

app.include_router(review_router)
```

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_review_api.py -v` then `make lint`.

Expected: PASS; Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/api/review.py src/fragility_map/api/server.py tests/test_review_api.py
git commit -m "feat(api): add extraction propose/verify review endpoint"
```

---

### Task 3: Approve / reject endpoints and audit exposure

**Files:**
- Modify: `src/fragility_map/api/review.py`
- Test: `tests/test_review_api.py` (append)

**Interfaces:**
- Consumes: the Task 2 `SESSION`, `CandidateLifecycle.approve/reject`, `lifecycle.get`, `lifecycle.audit_log`.
- Produces `DecisionRequest(candidate_id, reviewer_id, reason)` and two endpoints:
  - `POST /api/extraction/approve` → `{"candidate": <dump>, "audit": [ {candidate_id, from_status, to_status, reviewer_id, reason, verification_valid}, ... ]}`.
  - `POST /api/extraction/reject` → same shape.
  Both map `CandidateLifecycle`/`promote_approved` `ValueError` to HTTP 409 and unknown-candidate `KeyError` to HTTP 404.

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_review_api.py`:

```python
def test_approve_then_reject_updates_status_and_audit() -> None:
    _propose()

    approved = client.post(
        "/api/extraction/approve",
        json={
            "candidate_id": "coreweave-s1a-take_or_pay",
            "reviewer_id": "judge",
            "reason": "envelope and counterparty confirmed in the quoted passage",
        },
    )
    assert approved.status_code == 200
    assert approved.json()["candidate"]["status"] == "approved"
    assert approved.json()["audit"][-1]["to_status"] == "approved"

    rejected = client.post(
        "/api/extraction/reject",
        json={
            "candidate_id": "coreweave-s1a-customer_concentration",
            "reviewer_id": "judge",
            "reason": "concentration does not imply the buyer drives purchases",
        },
    )
    assert rejected.status_code == 200
    assert rejected.json()["candidate"]["status"] == "rejected"


def test_reject_requires_reason() -> None:
    _propose()
    response = client.post(
        "/api/extraction/reject",
        json={
            "candidate_id": "coreweave-s1a-take_or_pay",
            "reviewer_id": "judge",
            "reason": "   ",
        },
    )
    assert response.status_code == 409
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_review_api.py::test_approve_then_reject_updates_status_and_audit -v`

Expected: FAIL with 404/405 because the routes do not exist yet.

- [ ] **Step 3: Implement the endpoints**

Append to `src/fragility_map/api/review.py`:

```python
from fastapi import HTTPException


class DecisionRequest(BaseModel):
    candidate_id: str = Field(min_length=1)
    reviewer_id: str = Field(min_length=1)
    reason: str = Field(min_length=1)


def _audit_view() -> list[dict]:
    return [
        {
            "candidate_id": e.candidate_id,
            "from_status": e.from_status.value if e.from_status else None,
            "to_status": e.to_status.value,
            "reviewer_id": e.reviewer_id,
            "reason": e.reason,
            "verification_valid": e.verification_valid,
        }
        for e in SESSION.lifecycle.audit_log()
    ]


def _decide(request: DecisionRequest, approve: bool) -> dict:
    try:
        if approve:
            candidate = SESSION.lifecycle.approve(
                request.candidate_id, request.reviewer_id, request.reason
            )
        else:
            candidate = SESSION.lifecycle.reject(
                request.candidate_id, request.reviewer_id, request.reason
            )
    except KeyError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    return {"candidate": candidate.model_dump(mode="json"), "audit": _audit_view()}


@router.post("/approve")
def approve(request: DecisionRequest) -> dict:
    return _decide(request, approve=True)


@router.post("/reject")
def reject(request: DecisionRequest) -> dict:
    return _decide(request, approve=False)
```

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_review_api.py -v` then `make lint`.

Expected: PASS; Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/api/review.py tests/test_review_api.py
git commit -m "feat(api): add human approve/reject review endpoints"
```

---

### Task 4: Credit-event shock over seeded graph plus promoted candidates

**Files:**
- Create: `src/fragility_map/api/scenario.py`
- Modify: `src/fragility_map/api/server.py` (mount the router)
- Test: `tests/test_scenario_api.py`

**Interfaces:**
- Consumes: the Task 2 `SESSION` (to read approved candidates), `promote_approved`, `run_compound_shock`, `Shock`, `StructuralRelationship`, `EdgeProvenance`, `ProvenanceLabel`, `StructureType`, `CandidateStatus`.
- Produces `seed_hero_relationships() -> list[StructuralRelationship]` returning the seeded OpenAI→MSFT `equity_method` (`ownership_share=0.27`, quantifying propagation) and CoreWeave→NVDA `behavioural` edges (NOT the take-or-pay edge — that one only exists once approved).
- Produces `POST /api/scenario/credit-event` with body `{source_company_id="openai", incremental_gaap_loss=10_000, credit_status="severe_distress"}` (all defaulted) returning `{"edges": [{relationship_id, source, target, tier, result_kind, value, basis}], "nodes": {id: {quantified_impact, activated_exposure, epistemic_state}}}`. The structural graph passed to `run_compound_shock` is `seed_hero_relationships()` plus `promote_approved(candidate, verification)` for every lifecycle candidate whose status is `APPROVED` or `EDITED`.

- [ ] **Step 1: Write the failing tests**

Create `tests/test_scenario_api.py`:

```python
from pathlib import Path

from fastapi.testclient import TestClient

from fragility_map.api import review
from fragility_map.api.server import app

client = TestClient(app)


def _propose_and(approve: bool) -> None:
    review.reset_session()
    text = Path("tests/fixtures/coreweave_s1a_excerpt.txt").read_text(encoding="utf-8")
    client.post(
        "/api/extraction/propose",
        json={
            "source_id": "coreweave-s1a",
            "source_accession": "0001640147-25-000001",
            "source_company_id": "openai",
            "target_company_id": "coreweave",
            "filing_text": text,
        },
    )
    if approve:
        client.post(
            "/api/extraction/approve",
            json={
                "candidate_id": "coreweave-s1a-take_or_pay",
                "reviewer_id": "judge",
                "reason": "confirmed",
            },
        )


def test_seeded_equity_impact_is_always_present() -> None:
    review.reset_session()
    result = client.post("/api/scenario/credit-event", json={}).json()
    assert result["nodes"]["msft"]["quantified_impact"] == -2_700
    msft_edge = next(e for e in result["edges"] if e["target"] == "msft")
    assert msft_edge["tier"] == "solid_red"
    assert msft_edge["result_kind"] == "impact"


def test_approved_take_or_pay_activates_orange_exposure() -> None:
    _propose_and(approve=True)
    result = client.post("/api/scenario/credit-event", json={}).json()
    assert result["nodes"]["coreweave"]["activated_exposure"] == 11_900
    cw_edge = next(e for e in result["edges"] if e["target"] == "coreweave")
    assert cw_edge["tier"] == "solid_orange"
    assert cw_edge["result_kind"] == "exposure"


def test_without_approval_no_coreweave_exposure() -> None:
    _propose_and(approve=False)
    result = client.post("/api/scenario/credit-event", json={}).json()
    assert "coreweave" not in result["nodes"] or (
        result["nodes"]["coreweave"]["activated_exposure"] is None
    )
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_scenario_api.py::test_seeded_equity_impact_is_always_present -v`

Expected: FAIL (404) because `/api/scenario/credit-event` does not exist.

- [ ] **Step 3: Implement the endpoint**

Create `src/fragility_map/api/scenario.py`:

```python
from fastapi import APIRouter
from pydantic import BaseModel, Field

from fragility_map.api.review import SESSION
from fragility_map.extraction.candidates import CandidateStatus
from fragility_map.extraction.lifecycle import promote_approved
from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel, StructureType
from fragility_map.model.propagation import (
    ShockResult,
    Shock,
    StructuralRelationship,
    run_compound_shock,
)

router = APIRouter(prefix="/api/scenario")

_QUANTIFYING = EdgeProvenance(
    ProvenanceLabel.REPORTED,
    ProvenanceLabel.REPORTED,
    ProvenanceLabel.CALCULATED,
    ProvenanceLabel.CONSTRAINED,
)
_BEHAVIOURAL = EdgeProvenance(
    ProvenanceLabel.REPORTED,
    ProvenanceLabel.ASSUMED,
    ProvenanceLabel.ASSUMED,
    ProvenanceLabel.ASSUMED,
)


def seed_hero_relationships() -> list[StructuralRelationship]:
    return [
        StructuralRelationship(
            "openai-msft-equity", "openai", "msft", StructureType.EQUITY_METHOD,
            _QUANTIFYING, ownership_share=0.27,
        ),
        StructuralRelationship(
            "coreweave-nvda-behavioural", "openai", "nvda", StructureType.BEHAVIOURAL,
            _BEHAVIOURAL,
        ),
    ]


def _promoted() -> list[StructuralRelationship]:
    promoted: list[StructuralRelationship] = []
    for candidate_id in list(SESSION.lifecycle._items):  # noqa: SLF001
        candidate, verification = SESSION.lifecycle._items[candidate_id]  # noqa: SLF001
        if candidate.status in {CandidateStatus.APPROVED, CandidateStatus.EDITED}:
            promoted.append(promote_approved(candidate, verification))
    return promoted


class CreditEventRequest(BaseModel):
    source_company_id: str = Field(default="openai", min_length=1)
    incremental_gaap_loss: float = Field(default=10_000)
    credit_status: str = Field(default="severe_distress", min_length=1)


def _serialize(result: ShockResult) -> dict:
    return {
        "edges": [
            {
                "relationship_id": e.relationship_id,
                "source": e.source_company_id,
                "target": e.target_company_id,
                "tier": e.tier.value,
                "result_kind": e.result_kind,
                "value": e.value,
                "basis": e.basis,
            }
            for e in result.edges
        ],
        "nodes": {
            company_id: {
                "quantified_impact": node.quantified_impact,
                "activated_exposure": node.activated_exposure,
                "epistemic_state": node.epistemic_state,
            }
            for company_id, node in result.nodes.items()
        },
    }


@router.post("/credit-event")
def credit_event(request: CreditEventRequest) -> dict:
    relationships = seed_hero_relationships() + _promoted()
    shock = Shock(
        request.source_company_id,
        incremental_gaap_loss=request.incremental_gaap_loss,
        credit_status=request.credit_status,
    )
    return _serialize(run_compound_shock(relationships, shock))
```

> Note: `SESSION.lifecycle._items` is the in-process store from Task 2. It is read here rather than through a new public accessor to keep this plan additive; if a later refactor adds `CandidateLifecycle.approved_items()`, switch `_promoted()` to it.

Mount it in `src/fragility_map/api/server.py`:

```python
from fragility_map.api.scenario import router as scenario_router

app.include_router(scenario_router)
```

- [ ] **Step 4: Run focused tests, full suite, and lint**

Run: `pytest tests/test_scenario_api.py -v`, then `make test`, then `make lint`.

Expected: new tests and the entire existing Python suite PASS; Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/api/scenario.py src/fragility_map/api/server.py tests/test_scenario_api.py
git commit -m "feat(api): credit-event shock over seeded graph plus promoted edges"
```

---

### Task 5: Frontend review panel — propose, checklist, highlight, approve/reject

**Files:**
- Create: `frontend/src/reviewApi.ts`
- Create: `frontend/src/components/ReviewPanel.tsx`
- Modify: `frontend/src/App.tsx` (render the panel in the left rail)
- Modify: `frontend/src/styles.css` (blue-striped + checklist styles)
- Test: `frontend/tests/ReviewPanel.test.tsx`

**Interfaces:**
- Consumes: the Task 2/3 endpoints.
- Produces `reviewApi.ts` exporting `propose(req)`, `approve(body)`, `reject(body)` and the `CandidateView`, `VerificationCheck` TypeScript types matching the backend `CandidateView` shape.
- Produces `<ReviewPanel onDecision={() => void} />`: a textarea (default value = the CoreWeave excerpt), a "Analyze filing" button that calls `propose`, and one blue-striped card per candidate showing the relationship line, the `quoted_text` with the highlighted span emphasised, the eight-check list with ✓/✗, a "Semantic: pending human review" line, and Approve/Reject buttons that call the endpoints and then invoke `onDecision`.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/ReviewPanel.test.tsx`:

```tsx
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ReviewPanel } from "../src/components/ReviewPanel";

const takeOrPayView = {
  candidate: {
    candidate_id: "coreweave-s1a-take_or_pay",
    relationship_type: "take_or_pay",
    source_company_id: "openai",
    target_company_id: "coreweave",
    quoted_text: "We have purchase commitments of $11.9 billion.",
    status: "proposed"
  },
  verification: {
    checks: [{ name: "quoted_text", passed: true, detail: "quote present" }],
    mechanically_valid: true,
    semantic_interpretation: "pending_human_review"
  },
  highlight: { start: 0, end: 44 }
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => ({ candidates: [takeOrPayView] }) }))
  );
});
afterEach(() => vi.unstubAllGlobals());

test("analyze renders a blue-striped candidate with its checklist", async () => {
  render(<ReviewPanel onDecision={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: /analyze filing/i }));
  await waitFor(() => screen.getByText(/openai/i));
  expect(screen.getByText(/pending human review/i)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /approve/i })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /reject/i })).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `npm --prefix frontend run test -- --run ReviewPanel`

Expected: FAIL — `ReviewPanel` module not found.

- [ ] **Step 3: Implement the API module**

Create `frontend/src/reviewApi.ts`:

```ts
export interface VerificationCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface CandidateView {
  candidate: {
    candidate_id: string;
    relationship_type: string;
    source_company_id: string;
    target_company_id: string;
    quoted_text: string;
    status: string;
  };
  verification: {
    checks: VerificationCheck[];
    mechanically_valid: boolean;
    semantic_interpretation: string;
  };
  highlight: { start: number; end: number } | null;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function propose(req: {
  source_id: string;
  source_accession: string;
  source_company_id: string;
  target_company_id: string;
  filing_text: string;
}): Promise<{ candidates: CandidateView[] }> {
  return postJson("/api/extraction/propose", req);
}

export function approve(body: { candidate_id: string; reviewer_id: string; reason: string }) {
  return postJson("/api/extraction/approve", body);
}

export function reject(body: { candidate_id: string; reviewer_id: string; reason: string }) {
  return postJson("/api/extraction/reject", body);
}
```

- [ ] **Step 4: Implement the panel**

Create `frontend/src/components/ReviewPanel.tsx`:

```tsx
import { useState } from "react";
import { approve, propose, reject, type CandidateView } from "../reviewApi";

const DEFAULT_FILING =
  "Microsoft accounted for 62% of our revenue in 2024. " +
  "We have entered into purchase commitments of $11.9 billion through 2030 with OpenAI " +
  "to secure dedicated compute capacity.";

function Highlighted({ view }: { view: CandidateView }) {
  const quote = view.candidate.quoted_text;
  return <mark className="evidence-quote">{quote}</mark>;
}

export function ReviewPanel({ onDecision }: { onDecision: () => void }) {
  const [filing, setFiling] = useState(DEFAULT_FILING);
  const [views, setViews] = useState<CandidateView[]>([]);

  async function analyze() {
    const body = await propose({
      source_id: "coreweave-s1a",
      source_accession: "0001640147-25-000001",
      source_company_id: "openai",
      target_company_id: "coreweave",
      filing_text: filing
    });
    setViews(body.candidates);
  }

  async function decide(view: CandidateView, ok: boolean) {
    const body = {
      candidate_id: view.candidate.candidate_id,
      reviewer_id: "judge",
      reason: ok ? "confirmed in the quoted passage" : "over-interpretation beyond the disclosure"
    };
    await (ok ? approve(body) : reject(body));
    setViews((current) =>
      current.map((v) =>
        v.candidate.candidate_id === view.candidate.candidate_id
          ? { ...v, candidate: { ...v.candidate, status: ok ? "approved" : "rejected" } }
          : v
      )
    );
    onDecision();
  }

  return (
    <section className="review-panel">
      <h2>Live filing extraction</h2>
      <textarea value={filing} onChange={(e) => setFiling(e.target.value)} rows={5} />
      <button type="button" onClick={analyze}>Analyze filing</button>
      {views.map((view) => (
        <article className="candidate-card" key={view.candidate.candidate_id}>
          <p className="candidate-line">
            {view.candidate.source_company_id} → {view.candidate.target_company_id} ·{" "}
            {view.candidate.relationship_type} · <em>{view.candidate.status}</em>
          </p>
          <p className="candidate-quote"><Highlighted view={view} /></p>
          <ul className="check-list">
            {view.verification.checks.map((check) => (
              <li key={check.name} data-passed={check.passed}>
                {check.passed ? "✓" : "✗"} {check.name}
              </li>
            ))}
          </ul>
          <p className="semantic-pending">Semantic: pending human review</p>
          <div className="decision-row">
            <button type="button" onClick={() => decide(view, true)}>Approve</button>
            <button type="button" onClick={() => decide(view, false)}>Reject</button>
          </div>
        </article>
      ))}
    </section>
  );
}
```

- [ ] **Step 5: Wire into App and style**

In `frontend/src/App.tsx`, import `ReviewPanel` and render it in the left rail after `<ResultsPanel graph={graph} />`, passing `onDecision={() => void runScenario()}` (Task 6 replaces this callback with the credit-event runner).

Append to `frontend/src/styles.css`:

```css
.candidate-card {
  border-left: 4px solid #2f6df6;
  background: repeating-linear-gradient(
    -45deg, rgba(47, 109, 246, 0.06), rgba(47, 109, 246, 0.06) 8px,
    transparent 8px, transparent 16px
  );
  padding: 8px 10px;
  margin-top: 8px;
}
.evidence-quote { background: #fff2a8; }
.check-list { list-style: none; padding: 0; font-size: 12px; }
.check-list li[data-passed="false"] { color: #b72d3a; }
.semantic-pending { font-size: 12px; color: #6b5b00; }
.decision-row { display: flex; gap: 8px; }
```

- [ ] **Step 6: Run the focused test and lint**

Run: `npm --prefix frontend run test -- --run ReviewPanel`

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/reviewApi.ts frontend/src/components/ReviewPanel.tsx frontend/src/App.tsx frontend/src/styles.css frontend/tests/ReviewPanel.test.tsx
git commit -m "feat(ui): add live extraction review panel"
```

---

### Task 6: Credit-event preset and tier-aware map rendering

**Files:**
- Modify: `frontend/src/reviewApi.ts` (add `runCreditEvent`)
- Create: `frontend/src/components/CreditEventResults.tsx`
- Modify: `frontend/src/App.tsx` (state + preset button + wire `onDecision`)
- Test: `frontend/tests/CreditEventResults.test.tsx`

**Interfaces:**
- Consumes: `POST /api/scenario/credit-event`.
- Produces `runCreditEvent(): Promise<CreditEventResult>` and the `CreditEventResult` type `{ edges: {relationship_id,source,target,tier,result_kind,value,basis}[]; nodes: Record<string,{quantified_impact:number|null;activated_exposure:number|null;epistemic_state:string}> }`.
- Produces `<CreditEventResults result={...} />` rendering, per edge, a row with the tier as a coloured class (`tier-solid_red` / `tier-solid_orange` / `tier-dashed_amber` / `tier-diffuse_amber`), the `result_kind`, and either `impact -$X` (red) or `exposure up to $X (not a realized loss)` (orange) or `not identifiable` for null values.

- [ ] **Step 1: Write the failing test**

Create `frontend/tests/CreditEventResults.test.tsx`:

```tsx
import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { CreditEventResults } from "../src/components/CreditEventResults";

const result = {
  edges: [
    { relationship_id: "openai-msft-equity", source: "openai", target: "msft",
      tier: "solid_red", result_kind: "impact", value: -2700, basis: "equity-method" },
    { relationship_id: "coreweave-s1a-take_or_pay", source: "openai", target: "coreweave",
      tier: "solid_orange", result_kind: "exposure", value: 11900, basis: "take-or-pay" }
  ],
  nodes: {
    msft: { quantified_impact: -2700, activated_exposure: null, epistemic_state: "quantified_impact" },
    coreweave: { quantified_impact: null, activated_exposure: 11900, epistemic_state: "exposure_detected" }
  }
};

test("renders impact in red and exposure as not-a-loss in orange", () => {
  render(<CreditEventResults result={result} />);
  expect(screen.getByText(/not a realized loss/i)).toBeInTheDocument();
  const orange = screen.getByText(/take-or-pay/i).closest(".tier-solid_orange");
  expect(orange).not.toBeNull();
});
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `npm --prefix frontend run test -- --run CreditEventResults`

Expected: FAIL — module not found.

- [ ] **Step 3: Add the API call**

Append to `frontend/src/reviewApi.ts`:

```ts
export interface CreditEventEdge {
  relationship_id: string;
  source: string;
  target: string;
  tier: string;
  result_kind: string;
  value: number | null;
  basis: string;
}

export interface CreditEventResult {
  edges: CreditEventEdge[];
  nodes: Record<
    string,
    { quantified_impact: number | null; activated_exposure: number | null; epistemic_state: string }
  >;
}

export function runCreditEvent(): Promise<CreditEventResult> {
  return postJson("/api/scenario/credit-event", {});
}
```

- [ ] **Step 4: Implement the results component**

Create `frontend/src/components/CreditEventResults.tsx`:

```tsx
import type { CreditEventEdge, CreditEventResult } from "../reviewApi";

function describe(edge: CreditEventEdge): string {
  if (edge.value === null) return "not identifiable from evidence";
  if (edge.result_kind === "impact") return `impact -$${Math.abs(edge.value)}M (forced loss)`;
  if (edge.result_kind === "exposure")
    return `exposure up to $${edge.value}M (not a realized loss)`;
  return edge.basis;
}

export function CreditEventResults({ result }: { result: CreditEventResult }) {
  if (result.edges.length === 0) return null;
  return (
    <section className="credit-event-results">
      <h2>OpenAI credit event</h2>
      <ul>
        {result.edges.map((edge) => (
          <li key={edge.relationship_id} className={`tier-${edge.tier}`}>
            <strong>
              {edge.source} → {edge.target}
            </strong>{" "}
            · {edge.basis} — {describe(edge)}
          </li>
        ))}
      </ul>
    </section>
  );
}
```

Append to `frontend/src/styles.css`:

```css
.tier-solid_red { border-left: 4px solid #b72d3a; padding-left: 8px; }
.tier-solid_orange { border-left: 4px solid #d66a2a; padding-left: 8px; }
.tier-dashed_amber { border-left: 4px dashed #e0a423; padding-left: 8px; }
.tier-diffuse_amber { border-left: 4px dotted #e0a423; padding-left: 8px; opacity: 0.8; }
.credit-event-results ul { list-style: none; padding: 0; }
.credit-event-results li { margin: 6px 0; }
```

- [ ] **Step 5: Wire the preset into App**

In `frontend/src/App.tsx`:
- Import `runCreditEvent`, `type CreditEventResult`, and `CreditEventResults`.
- Add state: `const [creditEvent, setCreditEvent] = useState<CreditEventResult | null>(null);`.
- Add `const runEvent = useCallback(async () => { setCreditEvent(await runCreditEvent()); }, []);`.
- Change the `ReviewPanel` prop to `onDecision={() => void runEvent()}` so approving/rejecting re-runs the shock and the CoreWeave exposure appears or stays absent live.
- Add a `<button type="button" onClick={() => void runEvent()}>Run OpenAI credit event</button>` in the left rail and render `{creditEvent && <CreditEventResults result={creditEvent} />}` beneath it.

- [ ] **Step 6: Run the focused test, the full frontend suite, and lint**

Run: `npm --prefix frontend run test -- --run`, then `make lint`.

Expected: all frontend tests PASS; Ruff clean (no Python changed here, but keep the gate).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/reviewApi.ts frontend/src/components/CreditEventResults.tsx frontend/src/App.tsx frontend/src/styles.css frontend/tests/CreditEventResults.test.tsx
git commit -m "feat(ui): credit-event preset with impact vs exposure tiers"
```

---

## Self-Review

**Spec coverage (against the user's five-step demo + ADR 0006 scope boundary):**
1. *Upload/paste filing* → Task 5 textarea + `propose`.
2. *LLM proposes typed cited candidates* → Task 1 `KeywordProposer` behind the `RelationshipProposer` protocol (deterministic stand-in; real LLM adapter is a documented later swap at the same seam).
3. *Code verifies (citation/token/entities/period/unit/arithmetic/accession), semantic pending* → existing `verify_candidate`, surfaced in Task 2 with highlight offsets and rendered in Task 5.
4. *Human approves one, rejects one; only approved enters the simulator* → Tasks 3 (endpoints) + 5 (buttons) + 4 (`promote_approved` gate).
5. *Run shock: MSFT solid-red impact, CoreWeave solid-orange exposure, NVDA amber* → Task 4 endpoint + Task 6 rendering, with approval visibly toggling CoreWeave exposure.

**Placeholder scan:** no TBD/TODO; every code step shows complete code, exact commands, and expected results. The one non-obvious access (`SESSION.lifecycle._items` in Task 4) is called out with a `noqa` and a refactor note rather than left implicit.

**Type consistency:** `CandidateView`/`VerificationCheck` shapes match between the Task 2 backend serializer and the Task 5 `reviewApi.ts` types; `CreditEventEdge`/`CreditEventResult` match the Task 4 serializer and the Task 6 types; `relationship_type` strings (`take_or_pay`, `customer_concentration`) map to `StructureType` members consumed by `promote_approved`; money units are USD-millions throughout (`11_900`, `10_000`, `2_700`, `0.27`).

**Scope boundary (deferred, not built here):** a real network LLM adapter (the protocol seam exists; no network call is added or tested); live EDGAR accession fetch/supersession resolution (the manifest is built from the request); DuckDB persistence of the *API* session (the in-process `CandidateLifecycle` is used; the already-tested repository methods remain available for a later wiring); and edge-flow-shock UI for concentration edges. The verification debt in `CONTEXT.md` (the seeded 0.27 / $11.9B figures) is a data-accuracy task, not a code task, and stays outstanding.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-18-review-ui-live-loop.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks.
2. **Inline Execution** — execute tasks in this session using executing-plans, with checkpoints.

Which approach?
