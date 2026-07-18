# Live Extraction and Mechanical Verifier Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the ADR 0006 live-extraction seam where an LLM proposes typed, cited relationship candidates, deterministic code verifies evidence tokens, and a human-controlled lifecycle is the only path to an engine-ready relationship.

**Architecture:** Keep proposal generation behind a stubbable `RelationshipProposer` protocol so tests and the demo can inject an LLM adapter without making network calls in the domain layer. Store a typed proposal separately from its mechanical verification result; verification is pure and reports individual checks while leaving semantic interpretation as `pending_human_review`. Persist proposal status and every approve/edit/reject decision in DuckDB, and expose an explicit promotion function that refuses to create an evidence-backed structural relationship unless a verified candidate is approved.

**Tech Stack:** Python 3.11+, Pydantic v2, `dataclasses`, `typing.Protocol`, DuckDB, pytest, Ruff. No new dependencies and no LLM/network call from tests.

## Global Constraints

- Governed by ADR 0006 and ADRs 0001–0005; the LLM may find and type candidate structure but must never promote its own proposal or create unsupported load-bearing numbers.
- Mechanical checks must be code-owned: quoted text exists verbatim; numeric token appears in the cited passage; named entities, period, and unit are present; declared arithmetic is valid; accession/source resolves; no superseding amendment is present in the supplied corpus.
- Every verification result uses the exact string `semantic_interpretation="pending_human_review"`; passing mechanical checks does not prove semantic correctness.
- Candidate lifecycle states are exactly `proposed`, `approved`, `edited`, and `rejected`; only `approved` candidates may be promoted to the engine.
- Rejection and edit decisions require a non-empty reviewer ID and reason; every transition appends an immutable audit event.
- A candidate is never written into the existing `relationships` table until promotion; existing legacy extraction behavior and tests remain green.
- Use existing `tests/test_relationship_extraction.py` as the seam and add dedicated fixtures under `tests/fixtures/`.
- Python: `pyproject.toml` sets `pythonpath=["src"]`, `testpaths=["tests"]`; Ruff uses `line-length=100`, `target-version=py311`, lint select `["E","F","I","UP","B"]`. Run `make test` and `make lint`.
- Every task ends with the named focused test, full suite/lint where stated, and a commit.

---

### Task 1: Typed candidate model and stubbable proposer boundary

**Files:**
- Create: `src/fragility_map/extraction/candidates.py`
- Modify: `src/fragility_map/extraction/__init__.py`
- Test: `tests/test_relationship_extraction.py` (append; leave existing tests unchanged)

**Interfaces:**
- Produces `CandidateStatus` (`PROPOSED`, `APPROVED`, `EDITED`, `REJECTED`), `RelationshipCandidateV2`, `RelationshipProposer` protocol, and `propose_candidates(proposer, source_id, filing_text)`.
- `RelationshipCandidateV2` fields: `candidate_id`, `source_id`, `source_accession`, `source_company_id`, `target_company_id | None`, `relationship_type`, `quoted_text`, `numeric_token | None`, `value | None`, `unit | None`, `period | None`, `supported_rule`, `unsupported_inference`, `status=CandidateStatus.PROPOSED`.
- `RelationshipProposer.propose(source_id: str, filing_text: str) -> list[RelationshipCandidateV2]` is the only proposal boundary; the implementation is injected by callers.

- [ ] **Step 1: Write the failing tests**

Append:

```python
from fragility_map.extraction.candidates import (
    CandidateStatus,
    RelationshipCandidateV2,
    propose_candidates,
)


class StubProposer:
    def propose(self, source_id: str, filing_text: str) -> list[RelationshipCandidateV2]:
        return [
            RelationshipCandidateV2(
                candidate_id="cand-1",
                source_id=source_id,
                source_accession="0000123456-25-000001",
                source_company_id="msft",
                target_company_id="coreweave",
                relationship_type="take_or_pay",
                quoted_text="Microsoft has purchase commitments of $4 billion through 2030 with CoreWeave.",
                numeric_token="$4 billion",
                value=4_000_000_000,
                unit="USD",
                period="through 2030",
                supported_rule="reported purchase commitment envelope",
                unsupported_inference="the commitment is specifically with CoreWeave",
            )
        ]


def test_candidate_is_typed_and_starts_proposed() -> None:
    candidate = StubProposer().propose("msft-filing", "filing text")[0]
    assert candidate.status is CandidateStatus.PROPOSED
    assert candidate.value == 4_000_000_000
    assert candidate.unsupported_inference.startswith("the commitment")


def test_proposal_boundary_is_stubbable() -> None:
    candidates = propose_candidates(StubProposer(), "msft-filing", "filing text")
    assert [candidate.candidate_id for candidate in candidates] == ["cand-1"]
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `pytest tests/test_relationship_extraction.py::test_candidate_is_typed_and_starts_proposed -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map.extraction.candidates'`.

- [ ] **Step 3: Implement the model and boundary**

Create `src/fragility_map/extraction/candidates.py`:

```python
from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class CandidateStatus(StrEnum):
    PROPOSED = "proposed"
    APPROVED = "approved"
    EDITED = "edited"
    REJECTED = "rejected"


class RelationshipCandidateV2(BaseModel):
    candidate_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_accession: str = Field(min_length=1)
    source_company_id: str = Field(min_length=1)
    target_company_id: str | None = None
    relationship_type: str = Field(min_length=1)
    quoted_text: str = Field(min_length=1)
    numeric_token: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    supported_rule: str = Field(min_length=1)
    unsupported_inference: str = Field(min_length=1)
    status: CandidateStatus = CandidateStatus.PROPOSED


class RelationshipProposer(Protocol):
    def propose(self, source_id: str, filing_text: str) -> list[RelationshipCandidateV2]: ...


def propose_candidates(
    proposer: RelationshipProposer,
    source_id: str,
    filing_text: str,
) -> list[RelationshipCandidateV2]:
    return proposer.propose(source_id, filing_text)
```

Export the public names from `src/fragility_map/extraction/__init__.py` without importing any network client.

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_relationship_extraction.py -v` then `make lint`.

Expected: all extraction tests PASS and Ruff reports no errors.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/extraction/candidates.py src/fragility_map/extraction/__init__.py tests/test_relationship_extraction.py
git commit -m "feat(extraction): add typed candidate and proposer boundary"
```

---

### Task 2: Pure mechanical verification with per-check evidence

**Files:**
- Create: `src/fragility_map/extraction/verifier.py`
- Test: `tests/test_relationship_extraction.py` (append)
- Create: `tests/fixtures/filing_with_candidate.txt`

**Interfaces:**
- Produces `SourceManifestEntry(accession: str, source_id: str, supersedes: tuple[str, ...] = ())`.
- Produces frozen `VerificationCheck(name: str, passed: bool, detail: str)` and `VerificationResult(candidate_id: str, checks: tuple[VerificationCheck, ...], semantic_interpretation: str, mechanically_valid: bool)`.
- Produces pure `verify_candidate(filing_text: str, candidate: RelationshipCandidateV2, source_manifest: Sequence[SourceManifestEntry], superseded_accessions: Collection[str] = ()) -> VerificationResult`.
- Check names are exactly `quoted_text`, `numeric_token`, `entities`, `period`, `unit`, `arithmetic`, `accession`, `supersession`.

- [ ] **Step 1: Write failing tests for pass and failure cases**

Append:

```python
from fragility_map.extraction.verifier import SourceManifestEntry, verify_candidate


def test_verifier_reports_each_check_and_keeps_semantics_pending() -> None:
    text = Path("tests/fixtures/filing_with_candidate.txt").read_text(encoding="utf-8")
    candidate = StubProposer().propose("msft-filing", text)[0]
    result = verify_candidate(
        text,
        candidate,
        [SourceManifestEntry("0000123456-25-000001", "msft-filing")],
    )
    assert result.mechanically_valid is True
    assert result.semantic_interpretation == "pending_human_review"
    assert {check.name for check in result.checks} == {
        "quoted_text", "numeric_token", "entities", "period", "unit",
        "arithmetic", "accession", "supersession",
    }
    assert all(check.passed for check in result.checks)


def test_verifier_blocks_missing_quote_and_superseded_accession() -> None:
    text = "Microsoft has purchase commitments of $4 billion through 2030 with CoreWeave."
    candidate = StubProposer().propose("msft-filing", text)[0].model_copy(
        update={"quoted_text": "Microsoft has no such commitment."}
    )
    result = verify_candidate(
        text,
        candidate,
        [SourceManifestEntry("0000123456-25-000001", "msft-filing")],
        superseded_accessions={"0000123456-25-000001"},
    )
    failed = {check.name for check in result.checks if not check.passed}
    assert failed == {"quoted_text", "supersession"}
    assert result.mechanically_valid is False
    assert result.semantic_interpretation == "pending_human_review"
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run: `pytest tests/test_relationship_extraction.py::test_verifier_reports_each_check_and_keeps_semantics_pending -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map.extraction.verifier'`.

- [ ] **Step 3: Implement deterministic checks**

Create `tests/fixtures/filing_with_candidate.txt` with this exact content:

```text
Microsoft has purchase commitments of $4 billion through 2030 with CoreWeave.
```

Implement `verify_candidate` with no HTTP or filesystem calls: use substring checks for quote/token/entities/period/unit, require `candidate.value` to be numeric when `numeric_token` is supplied, require the accession to match one manifest entry, and fail supersession when the accession is in `superseded_accessions`. Return all eight checks even after an earlier failure, set `mechanically_valid = all(check.passed ...)`, and always set `semantic_interpretation = "pending_human_review"`.

Use this arithmetic rule in the implementation: if a numeric token and value are present, parse the token's first number and scale (`million`, `billion`, or no scale); pass when the absolute difference from `value` is below `max(0.01, abs(value) * 1e-6)`. If no numeric token/value exists, pass the arithmetic check as `not applicable`.

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_relationship_extraction.py -v` then `make lint`.

Expected: all extraction tests PASS; Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/extraction/verifier.py tests/fixtures/filing_with_candidate.txt tests/test_relationship_extraction.py
git commit -m "feat(extraction): add pure mechanical candidate verifier"
```

---

### Task 3: Human-gated lifecycle, promotion, and immutable audit events

**Files:**
- Create: `src/fragility_map/extraction/lifecycle.py`
- Test: `tests/test_relationship_extraction.py` (append)

**Interfaces:**
- Produces frozen `AuditEvent(candidate_id: str, from_status: CandidateStatus | None, to_status: CandidateStatus, reviewer_id: str, reason: str, verification_valid: bool)`.
- Produces `CandidateLifecycle` with `submit(candidate, verification)`, `approve(candidate_id, reviewer_id, reason)`, `edit(candidate_id, edited_candidate, reviewer_id, reason, verification)`, `reject(candidate_id, reviewer_id, reason)`, `get(candidate_id)`, and `audit_log() -> tuple[AuditEvent, ...]`.
- Produces `promote_approved(candidate: RelationshipCandidateV2, verification: VerificationResult) -> StructuralRelationship`; it raises `ValueError` unless status is `APPROVED` or `EDITED` and verification is mechanically valid. Map `relationship_type="take_or_pay"` to `StructureType.TAKE_OR_PAY`, `customer_concentration` to `CUSTOMER_CONCENTRATION`, and `equity_method` to `EQUITY_METHOD`; leave unsupported types rejected.

- [ ] **Step 1: Write failing lifecycle tests**

Append:

```python
from fragility_map.extraction.lifecycle import CandidateLifecycle, promote_approved


def test_approval_requires_mechanical_verification_and_writes_audit() -> None:
    text = Path("tests/fixtures/filing_with_candidate.txt").read_text(encoding="utf-8")
    candidate = StubProposer().propose("msft-filing", text)[0]
    verification = verify_candidate(
        text, candidate, [SourceManifestEntry("0000123456-25-000001", "msft-filing")]
    )
    lifecycle = CandidateLifecycle()
    lifecycle.submit(candidate, verification)
    approved = lifecycle.approve("cand-1", "reviewer-1", "quote and amount confirmed")
    assert approved.status is CandidateStatus.APPROVED
    assert lifecycle.audit_log()[-1].to_status is CandidateStatus.APPROVED
    assert promote_approved(approved, verification).structure_type.value == "take_or_pay"


def test_rejection_is_terminal_for_promotion_and_is_logged() -> None:
    candidate = StubProposer().propose("msft-filing", "filing text")[0]
    invalid = VerificationResult(
        candidate_id="cand-1", checks=(),
        semantic_interpretation="pending_human_review", mechanically_valid=False,
    )
    lifecycle = CandidateLifecycle()
    lifecycle.submit(candidate, invalid)
    rejected = lifecycle.reject("cand-1", "reviewer-1", "portfolio language does not name buyer")
    assert rejected.status is CandidateStatus.REJECTED
    assert lifecycle.audit_log()[-1].reason.startswith("portfolio language")
    try:
        promote_approved(rejected, invalid)
    except ValueError as error:
        assert "approved" in str(error)
    else:
        raise AssertionError("rejected candidate was promoted")
```

- [ ] **Step 2: Run focused test to verify it fails**

Run: `pytest tests/test_relationship_extraction.py::test_approval_requires_mechanical_verification_and_writes_audit -v`

Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map.extraction.lifecycle'`.

- [ ] **Step 3: Implement lifecycle transitions**

Use a private dictionary of candidate IDs to `(candidate, verification)` and a private list of `AuditEvent`. `submit` accepts only `PROPOSED` candidates and records no fake approval. `approve` requires `mechanically_valid`; `edit` re-runs the caller-supplied verification and writes `EDITED`; `reject` accepts any submitted state but requires non-empty reviewer/reason and prevents later transitions. Every mutating method returns a new Pydantic model via `model_copy(update={"status": ...})`. `promote_approved` constructs the Plan 1 `StructuralRelationship` with an `EdgeProvenance` whose relationship/magnitude/propagation/timing labels are `REPORTED`, `REPORTED`, `CALCULATED`, `CONSTRAINED`; use candidate `value` as `committed_envelope` for take-or-pay and as the disclosed `concentration` fraction for customer-concentration candidates. Reject promotion when the required typed value is absent.

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_relationship_extraction.py -v` then `make lint`.

Expected: all extraction tests PASS; Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/extraction/lifecycle.py tests/test_relationship_extraction.py
git commit -m "feat(extraction): gate promotion behind review lifecycle"
```

---

### Task 4: Persist candidates, verification state, and audit log in DuckDB

**Files:**
- Modify: `src/fragility_map/db/schema.sql`
- Modify: `src/fragility_map/db/repository.py`
- Modify: `tests/test_repository.py` (append)

**Interfaces:**
- Add tables `relationship_candidates` and `candidate_audit_log` with primary keys, JSON-encoded candidate/verification payloads, status, reviewer metadata, and timestamps; use `CREATE TABLE IF NOT EXISTS` so existing databases remain readable.
- Add `FragilityRepository.save_candidate(candidate, verification) -> None`, `get_candidate(candidate_id) -> dict[str, Any] | None`, `record_candidate_audit(event) -> None`, and `list_candidate_audit(candidate_id) -> list[dict[str, Any]]`.
- Do not modify `insert_relationship_candidates`; legacy parser candidates still use the existing tables until the explicit promotion workflow is wired in Plan 3.

- [ ] **Step 1: Write failing persistence tests**

Append:

```python
from fragility_map.extraction.lifecycle import AuditEvent
from fragility_map.extraction.verifier import VerificationCheck, VerificationResult


def test_repository_round_trips_candidate_verification_and_audit(tmp_path: Path) -> None:
    repo = FragilityRepository(tmp_path / "review.duckdb")
    repo.create_schema()
    candidate = StubProposer().propose("msft-filing", "filing text")[0]
    verification = VerificationResult(
        candidate_id="cand-1",
        checks=(VerificationCheck("quoted_text", True, "found"),),
        semantic_interpretation="pending_human_review",
        mechanically_valid=True,
    )
    repo.save_candidate(candidate, verification)
    repo.record_candidate_audit(
        AuditEvent("cand-1", CandidateStatus.PROPOSED, CandidateStatus.APPROVED,
                   "reviewer-1", "confirmed", True)
    )
    stored = repo.get_candidate("cand-1")
    assert stored is not None
    assert stored["verification"]["mechanically_valid"] is True
    assert repo.list_candidate_audit("cand-1")[0]["to_status"] == "approved"
```

- [ ] **Step 2: Run focused test to verify it fails**

Run: `pytest tests/test_repository.py::test_repository_round_trips_candidate_verification_and_audit -v`

Expected: FAIL because the new repository methods/tables do not exist.

- [ ] **Step 3: Add schema and repository methods**

Add these tables to `schema.sql`:

```sql
CREATE TABLE IF NOT EXISTS relationship_candidates (
    candidate_id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL,
    status TEXT NOT NULL,
    candidate_json TEXT NOT NULL,
    verification_json TEXT NOT NULL,
    mechanically_valid BOOLEAN NOT NULL,
    saved_at TIMESTAMP NOT NULL
);

CREATE TABLE IF NOT EXISTS candidate_audit_log (
    audit_id TEXT PRIMARY KEY,
    candidate_id TEXT NOT NULL,
    from_status TEXT,
    to_status TEXT NOT NULL,
    reviewer_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    verification_valid BOOLEAN NOT NULL,
    created_at TIMESTAMP NOT NULL
);
```

Store the candidate and verification as JSON using `model_dump(mode="json")`; store `status`, `candidate_id`, `source_id`, `saved_at`, and `mechanically_valid` in typed columns. Store audit fields `audit_id`, `candidate_id`, `from_status`, `to_status`, `reviewer_id`, `reason`, `verification_valid`, and `created_at`. Generate IDs with `uuid.uuid4()` and timestamps with `datetime.now(timezone.utc).isoformat()`; never overwrite an audit row.

- [ ] **Step 4: Run repository tests, full suite, and lint**

Run: `pytest tests/test_repository.py -v`, then `make test`, then `make lint`.

Expected: repository tests and the entire existing suite PASS; Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/db/schema.sql src/fragility_map/db/repository.py tests/test_repository.py
git commit -m "feat(db): persist candidate review state and audit events"
```

---

### Task 5: Signature-integrity integration fixture and regression guard

**Files:**
- Create: `tests/fixtures/invalid_portfolio_candidate.json`
- Modify: `tests/test_relationship_extraction.py` (append)
- Modify: `README.md` (add a short review-flow section)

**Interfaces:**
- Consumes the proposer, verifier, lifecycle, and repository interfaces from Tasks 1–4.
- Produces an executable regression test proving a plausible-but-invalid proposal is rejected, cannot be promoted, and leaves an audit record containing the reviewer’s reason.

- [ ] **Step 1: Write the failing integration test**

Append:

```python
def test_signature_integrity_rejects_generic_portfolio_language() -> None:
    text = Path("tests/fixtures/filing_with_candidate.txt").read_text(encoding="utf-8")
    candidate = StubProposer().propose("msft-filing", text)[0].model_copy(
        update={"unsupported_inference": "CoreWeave is the named counterparty"}
    )
    verification = verify_candidate(
        text, candidate, [SourceManifestEntry("0000123456-25-000001", "msft-filing")]
    )
    lifecycle = CandidateLifecycle()
    lifecycle.submit(candidate, verification)
    rejected = lifecycle.reject(
        "cand-1", "judge", "general portfolio language does not identify CoreWeave"
    )
    assert rejected.status is CandidateStatus.REJECTED
    assert lifecycle.audit_log()[-1].reason == (
        "general portfolio language does not identify CoreWeave"
    )
```

- [ ] **Step 2: Run the integration test**

Run: `pytest tests/test_relationship_extraction.py::test_signature_integrity_rejects_generic_portfolio_language -v`.

Expected: PASS once Tasks 1–3 are implemented; if it fails, fix lifecycle/fixture integration without weakening the rejection assertion.

- [ ] **Step 3: Add fixture and concise documentation**

Create `tests/fixtures/invalid_portfolio_candidate.json` with:

```json
{
  "candidate_id": "cand-1",
  "relationship_type": "take_or_pay",
  "quoted_text": "Microsoft has purchase commitments of $4 billion through 2030 with CoreWeave.",
  "unsupported_inference": "CoreWeave is the named counterparty",
  "expected_rejection_reason": "general portfolio language does not identify CoreWeave"
}
```

Add a README paragraph stating that proposals are blue-striped/pending, mechanical checks are evidence checks only, and approval/edit/rejection is human-gated and audited.

- [ ] **Step 4: Run complete verification**

Run: `make test` then `make lint`.

Expected: entire Python suite PASS and Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add tests/fixtures/invalid_portfolio_candidate.json tests/test_relationship_extraction.py README.md
git commit -m "test(extraction): add signature-integrity rejection scenario"
```

---

## Self-Review

**Spec coverage:** ADR 0006 typed LLM proposal boundary → Task 1; verbatim quote/token/entity/period/unit/arithmetic/accession/supersession checks → Task 2; semantic interpretation remains pending → Task 2; proposed/approved/edited/rejected lifecycle and real engine promotion gate → Task 3; audit log persistence → Task 4; blue-striped invalid proposal and visible rejection reason → Task 5. Existing parser extraction and legacy relationship storage remain covered by the untouched tests plus the full-suite checks.

**Placeholder scan:** no TBD/TODO instructions; each task gives concrete files, signatures, test code, commands, expected results, and commit messages.

**Type consistency:** `RelationshipCandidateV2`, `VerificationResult`, `CandidateLifecycle`, `AuditEvent`, and repository method signatures are defined once and reused unchanged across Tasks 1–5. `promote_approved` depends on the `StructuralRelationship`, `StructureType`, `EdgeProvenance`, and `ProvenanceLabel` interfaces created by the evidence-honest engine plan.

**Scope boundary:** API review UI, blue-striped frontend rendering, live EDGAR accession resolution, and wiring promoted candidates into the scenario endpoint remain Plan 3 work; this plan supplies the backend contract and persistence needed by that UI without introducing network-dependent tests.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-18-live-extraction-mechanical-verifier.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, with review between tasks.
2. **Inline Execution** — execute tasks in this session using executing-plans, with checkpoints.

Which approach?
