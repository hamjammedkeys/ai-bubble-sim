# Evidence-Honest API, Hero Seed, and Review UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the legacy cloud-slowdown dashboard path with an evidence-honest compound-credit-event API and frontend that render Impact, Exposure, unidentifiable realized loss, behavioural dissolve, and blue-striped review candidates from one verified MSFT/OpenAI/CoreWeave seed.

**Architecture:** Keep the existing pure propagation engine as the source of truth and add a typed v2 payload adapter that serializes `ShockResult`, provenance, evidence citations, candidate review state, and four rendering tiers without inventing values. A deterministic hero seed supplies only disclosed/verified structural relationships and accession references; the API accepts explicit observed shock states and exposes review decisions through the existing lifecycle. The React app consumes the v2 payload, renders the four-tier graph and result panel, and provides Approve/Edit/Reject controls that call review endpoints and refresh the scenario.

**Tech Stack:** Python 3.11+, FastAPI/Pydantic v2, dataclasses, DuckDB, pytest, React 18, TypeScript, Vite, Cytoscape, Vitest, Testing Library. No new dependencies.

## Global Constraints

- Use ADRs 0001–0006 vocabulary verbatim: Shock, Structural propagation, Behavioural propagation, Impact, Exposure, Provenance label, Propagation mode, Tier.
- The only four rendering tiers are `solid_red`, `solid_orange`, `dashed_amber`, and `diffuse_amber`; candidate edges use a separate `blue_striped` visual state and never enter quantified engine output before approval.
- The hero preset is exactly: OpenAI incremental GAAP loss `$10_000_000_000`, `credit_status="severe_distress"`, `default_status="not_defaulted"`; Microsoft equity-method Impact is `-(0.27 * loss)`, CoreWeave take-or-pay Exposure is `11_900_000_000`, and no realized-loss point estimate is emitted.
- Every numeric relationship in the hero seed carries a source accession and evidence quote; no generic portfolio statement may be attached to the OpenAI/CoreWeave edge.
- API responses must label `Impact` and `Exposure` separately. Exposure must never populate `quantified_impact`, and ranking must exclude `exposure_detected` and `not_identifiable` nodes.
- Review actions must use the Plan 2 lifecycle and audit log; the frontend cannot locally mark a proposal approved without a successful API response.
- Existing Python tests and frontend tests remain green. Run `make test`, `make lint`, and `npm --prefix frontend test -- --run` plus `npm --prefix frontend run build`.
- Do not delete unrelated in-progress modifications in `src/fragility_map/api/server.py`, `src/fragility_map/model/propagation.py`, or tests; integrate carefully.

---

### Task 1: Typed v2 evidence payload and scenario serialization

**Files:**
- Create: `src/fragility_map/api/v2_payload.py`
- Modify: `src/fragility_map/model/propagation.py` (add realized-loss and sensitivity result types only if needed by the serializer)
- Test: `tests/test_api_v2_payload.py`

**Interfaces:**
- Produces `build_evidence_payload(companies: Mapping[str, CompanyFinancials], relationships: Sequence[StructuralRelationship], shock_result: ShockResult, candidates: Sequence[RelationshipCandidateV2] = ()) -> dict[str, object]`.
- Each node contains `companyId`, `label`, `quantifiedImpact`, `activatedExposure`, `epistemicState`, `rankingEligible`, and `tierSummary`.
- Each edge contains `relationshipId`, `source`, `target`, `structureType`, `tier`, `resultKind`, `value`, `basis`, `provenance`, and `sourceAccession`.
- Payload top level contains `scenario` (`incrementalGaapLoss`, `creditStatus`, `defaultStatus`, `language`), `nodes`, `edges`, `reviewCandidates`, `auditLog`, and `ranking`.

- [ ] **Step 1: Write failing serialization tests**

```python
from fragility_map.api.v2_payload import build_evidence_payload
from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel, StructureType
from fragility_map.model.propagation import Shock, StructuralRelationship, run_compound_shock


def _reported() -> EdgeProvenance:
    return EdgeProvenance(ProvenanceLabel.REPORTED, ProvenanceLabel.REPORTED,
                          ProvenanceLabel.CALCULATED, ProvenanceLabel.CONSTRAINED)


def test_payload_keeps_impact_and_exposure_separate() -> None:
    relationships = [
        StructuralRelationship("openai-msft", "openai", "msft", StructureType.EQUITY_METHOD, _reported(), ownership_share=0.27, source_accession="openai-10k-2025"),
        StructuralRelationship("openai-coreweave", "openai", "coreweave", StructureType.TAKE_OR_PAY, _reported(), committed_envelope=11_900_000_000, source_accession="coreweave-s1a-2025"),
    ]
    shock = Shock("openai", incremental_gaap_loss=10_000_000_000, credit_status="severe_distress")
    payload = build_evidence_payload({}, relationships, run_compound_shock(relationships, shock))
    msft = next(node for node in payload["nodes"] if node["companyId"] == "msft")
    coreweave = next(node for node in payload["nodes"] if node["companyId"] == "coreweave")
    assert msft["quantifiedImpact"] == -2_700_000_000
    assert coreweave["activatedExposure"] == 11_900_000_000
    assert coreweave["quantifiedImpact"] is None
    assert all(edge["resultKind"] != "realized_loss" for edge in payload["edges"])


def test_payload_marks_unidentifiable_nodes_ineligible_for_ranking() -> None:
    relationship = StructuralRelationship("coreweave-nvda", "coreweave", "nvda", StructureType.BEHAVIOURAL, _reported())
    payload = build_evidence_payload({}, relationship and [relationship], run_compound_shock([relationship], Shock("coreweave", credit_status="severe_distress")))
    node = next(node for node in payload["nodes"] if node["companyId"] == "nvda")
    assert node["epistemicState"] == "not_identifiable"
    assert node["rankingEligible"] is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_api_v2_payload.py -v`.

Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map.api.v2_payload'`.

- [ ] **Step 3: Implement the pure adapter**

Iterate only over `ShockResult.edges` and `ShockResult.nodes`; use `dataclasses.asdict`-equivalent explicit fields so the JSON names are stable camelCase. Serialize provenance as the four labels (`relationship`, `magnitude`, `propagation`, `timing`). Compute `rankingEligible` only when `epistemicState == "quantified_impact"` and `quantifiedImpact is not None`; do not infer tiers from magnitude. Include an empty `reviewCandidates` and `auditLog` when no candidates are supplied.

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_api_v2_payload.py -v && make lint`.

Expected: PASS and Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/api/v2_payload.py tests/test_api_v2_payload.py
git commit -m "feat(api): serialize evidence-honest v2 payload"
```

---

### Task 2: Verified MSFT/OpenAI/CoreWeave hero seed and explicit shock request

**Files:**
- Create: `src/fragility_map/seed/hero.py`
- Create: `src/fragility_map/seed/__init__.py`
- Create: `tests/test_hero_seed.py`

**Interfaces:**
- Produces `hero_relationships() -> list[StructuralRelationship]`, `hero_companies() -> dict[str, CompanyFinancials]`, and `hero_shock() -> Shock`.
- Seed relationships are exactly `openai-msft` (equity method, ownership `0.27`, accession `openai-10k-2025`), `openai-coreweave` (take-or-pay, envelope `11_900_000_000`, accession `coreweave-s1a-2025`), and `coreweave-nvda` (behavioural, accession `coreweave-s1a-2025`).
- `hero_shock()` returns `Shock("openai", 10_000_000_000, "severe_distress", "not_defaulted")`.

- [ ] **Step 1: Write failing seed tests**

```python
from fragility_map.seed.hero import hero_companies, hero_relationships, hero_shock
from fragility_map.model.evidence import StructureType


def test_hero_seed_has_three_accessioned_structural_edges() -> None:
    relationships = hero_relationships()
    assert {relationship.relationship_id for relationship in relationships} == {
        "openai-msft", "openai-coreweave", "coreweave-nvda"
    }
    assert all(relationship.source_accession for relationship in relationships)
    assert next(r for r in relationships if r.relationship_id == "openai-msft").ownership_share == 0.27
    assert next(r for r in relationships if r.relationship_id == "openai-coreweave").committed_envelope == 11_900_000_000
    assert next(r for r in relationships if r.relationship_id == "coreweave-nvda").structure_type is StructureType.BEHAVIOURAL


def test_hero_shock_has_explicit_observed_states() -> None:
    shock = hero_shock()
    assert (shock.source_company_id, shock.incremental_gaap_loss, shock.credit_status, shock.default_status) == (
        "openai", 10_000_000_000, "severe_distress", "not_defaulted"
    )
    assert set(hero_companies()) >= {"openai", "msft", "coreweave", "nvda"}
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `pytest tests/test_hero_seed.py -v`.

Expected: FAIL because `fragility_map.seed.hero` does not exist.

- [ ] **Step 3: Implement the deterministic seed**

Use `CompanyFinancials` for the four companies and the existing `EdgeProvenance` with `REPORTED`, `REPORTED`, `CALCULATED`, `CONSTRAINED`. Do not add invented annual flows or inferred multipliers. Keep the source accession strings in the relationship objects and add a module docstring explaining that the seed is illustrative and accession verification debt is tracked in the evidence fields.

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_hero_seed.py -v && make lint`.

Expected: PASS and Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/seed tests/test_hero_seed.py
git commit -m "feat(seed): add accessioned compound-credit-event hero triangle"
```

---

### Task 3: API v2 compound-credit-event and review endpoints

**Files:**
- Modify: `src/fragility_map/api/server.py`
- Create: `tests/test_api_v2.py`

**Interfaces:**
- Add `POST /api/v2/scenario/compound-credit-event` accepting `CompoundCreditEventRequest(incremental_gaap_loss: float, credit_status: Literal["normal","severe_distress"], default_status: Literal["not_defaulted","defaulted"])` and returning the v2 evidence payload.
- Add `GET /api/v2/review/candidates` returning pending candidates plus verification checks and audit entries.
- Add `POST /api/v2/review/{candidate_id}/approve`, `/edit`, and `/reject`; each delegates to `CandidateLifecycle`, persists the decision through `FragilityRepository`, and returns the refreshed v2 payload. `/edit` accepts a full typed candidate and reruns `verify_candidate` against the stored filing text.
- Keep `/api/graph` and `/api/scenario/cloud-slowdown` available for one compatibility release, but remove their frontend usage in Task 5.

- [ ] **Step 1: Write failing API tests**

```python
from fastapi.testclient import TestClient
from fragility_map.api.server import app


def test_compound_credit_event_returns_impact_exposure_and_dissolve() -> None:
    response = TestClient(app).post(
        "/api/v2/scenario/compound-credit-event",
        json={"incremental_gaap_loss": 10_000_000_000, "credit_status": "severe_distress", "default_status": "not_defaulted"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["scenario"]["language"] == "calculated Impact plus activated Exposure; downstream loss not identifiable"
    assert next(edge for edge in payload["edges"] if edge["relationshipId"] == "openai-msft")["tier"] == "solid_red"
    assert next(edge for edge in payload["edges"] if edge["relationshipId"] == "openai-coreweave")["resultKind"] == "exposure"
    assert next(edge for edge in payload["edges"] if edge["relationshipId"] == "coreweave-nvda")["value"] is None


def test_compound_credit_event_rejects_missing_or_invalid_state() -> None:
    response = TestClient(app).post("/api/v2/scenario/compound-credit-event", json={"incremental_gaap_loss": -1})
    assert response.status_code == 422
```

- [ ] **Step 2: Run the focused tests to verify they fail**

Run: `pytest tests/test_api_v2.py -v`.

Expected: FAIL because the v2 routes are not registered.

- [ ] **Step 3: Implement request validation and route handlers**

Instantiate the hero seed per request, construct a `Shock` from the validated request, call `run_compound_shock`, and pass the result to `build_evidence_payload`. For review routes, use the existing Plan 2 lifecycle/repository methods and return HTTP 409 for invalid transitions, HTTP 404 for unknown candidate IDs, and HTTP 422 for malformed edited candidates. Never accept a client-provided numeric result or tier.

- [ ] **Step 4: Run API tests, full Python suite, and lint**

Run: `pytest tests/test_api_v2.py tests/test_api_v2_payload.py tests/test_hero_seed.py -v && make test && make lint`.

Expected: all tests PASS and Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/api/server.py tests/test_api_v2.py
git commit -m "feat(api): add compound credit event and review routes"
```

---

### Task 4: Dashed-amber realized-loss guardrail and sensitivity output

**Files:**
- Modify: `src/fragility_map/model/propagation.py`
- Create: `tests/test_engine_modes.py`
- Modify: `src/fragility_map/api/v2_payload.py`

**Interfaces:**
- Produces `RealizedLossUnidentifiable(edge: StructuralRelationship, exposure: float, missing_parameters: tuple[str, ...])` rendered as `tier=Tier.DASHED_AMBER`, `result_kind="realized_loss_unidentifiable"`, `value=None`.
- Produces `run_sensitivity(relationships, shock, parameter_names: tuple[str, ...]) -> SensitivityResult` whose rows contain parameter name, supported range (`None` when undisclosed), and `output_status="not_identifiable"`; it must not emit a guessed loss interval.
- `build_evidence_payload` includes `dashed_amber` edges only when explicitly requested by `include_realized_loss_guardrail=True`; default compound event output remains Impact/Exposure plus diffuse dissolve.

- [ ] **Step 1: Write failing tests**

```python
from fragility_map.model.propagation import run_sensitivity


def test_realized_loss_is_dashed_amber_without_point_value() -> None:
    result = run_compound_shock(hero_relationships(), hero_shock(), include_realized_loss_guardrail=True)
    edge = next(edge for edge in result.edges if edge.relationship_id == "openai-coreweave-realized-loss")
    assert edge.tier is Tier.DASHED_AMBER
    assert edge.result_kind == "realized_loss_unidentifiable"
    assert edge.value is None


def test_sensitivity_reports_missing_credit_parameters_without_fabricating_range() -> None:
    sensitivity = run_sensitivity(hero_relationships(), hero_shock(), ("PD", "LGD", "timing"))
    assert [row.parameter for row in sensitivity.rows] == ["PD", "LGD", "timing"]
    assert all(row.supported_range is None and row.output_status == "not_identifiable" for row in sensitivity.rows)
```

- [ ] **Step 2: Run focused tests to verify they fail**

Run: `pytest tests/test_engine_modes.py -v`.

Expected: FAIL because the guardrail and sensitivity interfaces do not exist.

- [ ] **Step 3: Implement explicit no-number outputs**

Add the result dataclasses and optional flag without changing default `run_compound_shock` behaviour. The realized-loss edge must reference the take-or-pay exposure and list exactly `("EAD", "PD", "LGD", "timing")` as missing parameters. `run_sensitivity` returns rows with `supported_range=None`; no random, midpoint, or assumed parameter may enter the result.

- [ ] **Step 4: Run tests and lint**

Run: `pytest tests/test_engine_modes.py tests/test_stress_model.py -v && make lint`.

Expected: PASS and Ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/propagation.py src/fragility_map/api/v2_payload.py tests/test_engine_modes.py
git commit -m "feat(engine): expose dashed amber loss guardrail and sensitivity"
```

---

### Task 5: Frontend v2 types, four-tier graph, and evidence result panel

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/NetworkMap.tsx`
- Modify: `frontend/src/components/ResultsPanel.tsx`
- Modify: `frontend/src/components/CompanyPanel.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/tests/App.test.tsx`
- Modify: `frontend/tests/NetworkMap.test.tsx`

**Interfaces:**
- `EvidenceTier = "solid_red" | "solid_orange" | "dashed_amber" | "diffuse_amber"` and `ReviewVisualState = "verified" | "blue_striped"`.
- `EvidencePayload` mirrors Task 1’s camelCase payload; `EvidenceNode` exposes `quantifiedImpact`, `activatedExposure`, `epistemicState`, and `rankingEligible`.
- `runCompoundCreditEvent(request) -> Promise<EvidencePayload>`, `listReviewCandidates()`, and `submitReviewDecision(candidateId, action, body)` replace `runCloudSlowdown` in `App`.

- [ ] **Step 1: Write failing frontend tests**

Add tests asserting that a fixture payload renders: (1) red Impact and orange Exposure labels separately, (2) a dashed amber “realized loss not identifiable” row with no number, (3) diffuse amber dissolve marker, (4) a blue-striped candidate with `Pending human review`, and (5) Approve/Reject buttons invoke the review API and refresh the payload.

```tsx
it("renders evidence tiers without turning exposure into loss", async () => {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => evidencePayload }));
  render(<App />);
  expect(await screen.findByText("Calculated Impact")).toBeTruthy();
  expect(screen.getByText("Activated Exposure")).toBeTruthy();
  expect(screen.getByText("Realized loss: not identifiable")).toBeTruthy();
  expect(screen.getByText("Pending human review")).toBeTruthy();
  expect(screen.queryByText("$11,900M loss")).toBeNull();
});
```

- [ ] **Step 2: Run focused frontend tests to verify they fail**

Run: `npm --prefix frontend test -- --run frontend/tests/App.test.tsx frontend/tests/NetworkMap.test.tsx`.

Expected: FAIL because v2 types, API calls, labels, and review controls do not exist.

- [ ] **Step 3: Implement typed client and rendering**

Use `tier` to select Cytoscape styles: solid red/orange lines for quantified results, dashed amber for unidentifiable realized loss, diffuse amber low-opacity dotted lines for behavioural dissolve, and a blue diagonal stripe CSS class for `blue_striped` candidates. ResultsPanel must render separate numeric fields and literal copy `Calculated Impact`, `Activated Exposure`, `Realized loss: not identifiable`, and `Pending human review`. CompanyPanel must show epistemic state and hide ranking controls when `rankingEligible` is false. Review actions call the API, display the returned audit reason, and then refresh the graph.

- [ ] **Step 4: Run frontend tests and build**

Run: `npm --prefix frontend test -- --run && npm --prefix frontend run build`.

Expected: all Vitest tests PASS and Vite build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/tests
git commit -m "feat(frontend): render evidence tiers and review actions"
```

---

### Task 6: Remove legacy frontend path and add end-to-end hero regression

**Files:**
- Modify: `frontend/src/api.ts`
- Modify: `frontend/src/App.tsx`
- Modify: `e2e/dashboard.spec.ts`
- Modify: `README.md`

**Interfaces:**
- The frontend makes no request to `/api/scenario/cloud-slowdown`; all scenario interaction uses `/api/v2/scenario/compound-credit-event`.
- The browser-visible hero flow has one button, explicit observed shock state, separate Impact/Exposure headings, and a review rejection that appears in the audit log.

- [ ] **Step 1: Write the failing browser regression**

```ts
test("hero compound credit event preserves evidence grammar", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Run compound credit event" })).toBeVisible();
  await page.getByRole("button", { name: "Run compound credit event" }).click();
  await expect(page.getByText("Calculated Impact")).toBeVisible();
  await expect(page.getByText("Activated Exposure")).toBeVisible();
  await expect(page.getByText("Realized loss: not identifiable")).toBeVisible();
  await expect(page.getByText("Pending human review")).toBeVisible();
});
```

- [ ] **Step 2: Run the browser test to verify it fails**

Run: `npx playwright test e2e/dashboard.spec.ts --project=chromium`.

Expected: FAIL because the legacy controls and payload are still rendered.

- [ ] **Step 3: Retire the old path from the frontend and document the v2 contract**

Remove `runCloudSlowdown` from the frontend client and legacy scenario controls from `App`; retain backend compatibility routes until a later cleanup. Update README commands and the API contract section with the exact request JSON and evidence-tier meanings.

- [ ] **Step 4: Run all verification**

Run: `make test && make lint && npm --prefix frontend test -- --run && npm --prefix frontend run build && npx playwright test e2e/dashboard.spec.ts --project=chromium`.

Expected: all Python/TypeScript tests, build, and browser regression PASS.

- [ ] **Step 5: Commit**

```bash
git add frontend/src frontend/tests e2e/dashboard.spec.ts README.md
git commit -m "test: lock compound credit event hero flow"
```

---

## Self-Review

**Spec coverage:** v2 endpoint and payload → Tasks 1 and 3; verified accessioned hero seed → Task 2; Impact/Exposure separation and four tiers → Tasks 1, 4, and 5; dashed-amber guardrail and sensitivity output → Task 4; review UI and audit actions → Tasks 3 and 5; blue-striped candidate and signature rejection → Tasks 3 and 5; legacy frontend migration and browser proof → Task 6.

**Placeholder scan:** no TODO/TBD instructions; every task includes exact files, interfaces, tests, commands, expected output, and commit text.

**Type consistency:** `EvidencePayload`, `EvidenceNode`, `EvidenceTier`, `CompoundCreditEventRequest`, `runCompoundCreditEvent`, and review action names are defined once and reused across backend and frontend tasks. Existing Plan 1/2 types are consumed by their exact module paths.

**Scope boundary:** live EDGAR retrieval and real accession validation remain ingestion work; this plan uses accession strings already carried by verified seed relationships and makes missing verification visible rather than claiming external resolution.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-18-api-v2-seed-frontend.md`. Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, with review between tasks.
2. **Inline Execution** — execute tasks in this session using executing-plans, with checkpoints.

Which approach?
