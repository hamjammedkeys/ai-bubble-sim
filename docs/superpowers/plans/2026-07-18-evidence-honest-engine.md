# Evidence-Honest Engine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the behavioural stress engine with a deterministic *structural* propagation engine that separates calculated Impact from activated Exposure, refuses to fabricate unconstrained multipliers, and visibly dissolves the shock where evidence stops.

**Architecture:** Add two pure modules under `src/fragility_map/model/` — `evidence.py` (provenance value objects + tier gating) and `propagation.py` (compound Shock, structural relationships, and the `run_compound_shock` engine). These are purely additive: the legacy `stress.py`, `graph_export.py`, `api/server.py`, and the frontend are left untouched by this plan and continue to pass, so the tree stays green at every commit. Wiring the new engine into the API and frontend are separate follow-up plans (see "Follow-up plans").

**Tech Stack:** Python 3.11+, `dataclasses`, `enum`, `pytest`. No new dependencies.

## Global Constraints

- Governed by ADRs 0001–0006 and the `CONTEXT.md` glossary. Use glossary vocabulary verbatim: **Shock, Structural propagation, Behavioural propagation, Impact, Exposure, Provenance label, Propagation mode, Tier**. Do NOT reintroduce `confidence_score` or a single per-edge label.
- Five provenance labels only: `reported`, `calculated`, `constrained_estimate`, `assumed`, `hypothetical`.
- Four tiers only: `solid_red` (calculated accounting Impact), `solid_orange` (quantified Exposure), `dashed_amber` (assumption-dependent realized loss — not identifiable), `diffuse_amber` (behavioural downstream response).
- **Impact ≠ Exposure:** an Exposure is an amount *placed at risk*; it must never be emitted as `result_kind="impact"` nor summed into a node's `quantified_impact`.
- **Evidence-only is the default mode.** An edge propagates a *quantified* value only if its `propagation` provenance is `reported` or `calculated`. Otherwise the shock dissolves at that edge (no fabricated point value).
- Python: `pyproject.toml` sets `pythonpath=["src"]`, `testpaths=["tests"]`; ruff `line-length=100`, `target-version=py311`, lint select `["E","F","I","UP","B"]`. Run tests with `make test` (`pytest -v`) and lint with `make lint` (`ruff check src tests`).
- All new engine behaviour tests live in the agreed seam file `tests/test_stress_model.py`. Leave the existing tests in that file untouched.
- Every code step ends by running the named test/lint command and confirming the stated output, then a commit.

---

### Task 1: Provenance value objects and tier gating (`evidence.py`)

**Files:**
- Create: `src/fragility_map/model/evidence.py`
- Test: `tests/test_stress_model.py` (append new tests; do not edit existing ones)

**Interfaces:**
- Consumes: nothing (leaf module).
- Produces:
  - `ProvenanceLabel` (str Enum): `REPORTED="reported"`, `CALCULATED="calculated"`, `CONSTRAINED="constrained_estimate"`, `ASSUMED="assumed"`, `HYPOTHETICAL="hypothetical"`.
  - `StructureType` (str Enum): `EQUITY_METHOD="equity_method"`, `TAKE_OR_PAY="take_or_pay"`, `CUSTOMER_CONCENTRATION="customer_concentration"`, `PURCHASE_OBLIGATION="purchase_obligation"`, `OWNERSHIP_STAKE="ownership_stake"`, `DEBT_OBLIGATION="debt_obligation"`, `BEHAVIOURAL="behavioural"`.
  - `Tier` (str Enum): `SOLID_RED="solid_red"`, `SOLID_ORANGE="solid_orange"`, `DASHED_AMBER="dashed_amber"`, `DIFFUSE_AMBER="diffuse_amber"`.
  - `EdgeProvenance` (frozen dataclass): fields `relationship: ProvenanceLabel`, `magnitude: ProvenanceLabel`, `propagation: ProvenanceLabel`, `timing: ProvenanceLabel`.
  - `quantifies_propagation(prov: EdgeProvenance) -> bool` — True iff `prov.propagation in {REPORTED, CALCULATED}`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stress_model.py`:

```python
from fragility_map.model.evidence import (
    EdgeProvenance,
    ProvenanceLabel,
    Tier,
    quantifies_propagation,
)


def test_quantifies_propagation_requires_reported_or_calculated() -> None:
    reported = EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.REPORTED,
    )
    assumed = EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CONSTRAINED,
        ProvenanceLabel.ASSUMED,
        ProvenanceLabel.ASSUMED,
    )
    assert quantifies_propagation(reported) is True
    assert quantifies_propagation(assumed) is False


def test_tier_values_are_the_four_canonical_strings() -> None:
    assert {t.value for t in Tier} == {
        "solid_red",
        "solid_orange",
        "dashed_amber",
        "diffuse_amber",
    }
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stress_model.py::test_quantifies_propagation_requires_reported_or_calculated -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map.model.evidence'`

- [ ] **Step 3: Write minimal implementation**

Create `src/fragility_map/model/evidence.py`:

```python
from dataclasses import dataclass
from enum import Enum


class ProvenanceLabel(str, Enum):
    REPORTED = "reported"
    CALCULATED = "calculated"
    CONSTRAINED = "constrained_estimate"
    ASSUMED = "assumed"
    HYPOTHETICAL = "hypothetical"


class StructureType(str, Enum):
    EQUITY_METHOD = "equity_method"
    TAKE_OR_PAY = "take_or_pay"
    CUSTOMER_CONCENTRATION = "customer_concentration"
    PURCHASE_OBLIGATION = "purchase_obligation"
    OWNERSHIP_STAKE = "ownership_stake"
    DEBT_OBLIGATION = "debt_obligation"
    BEHAVIOURAL = "behavioural"


class Tier(str, Enum):
    SOLID_RED = "solid_red"
    SOLID_ORANGE = "solid_orange"
    DASHED_AMBER = "dashed_amber"
    DIFFUSE_AMBER = "diffuse_amber"


@dataclass(frozen=True)
class EdgeProvenance:
    relationship: ProvenanceLabel
    magnitude: ProvenanceLabel
    propagation: ProvenanceLabel
    timing: ProvenanceLabel


def quantifies_propagation(prov: EdgeProvenance) -> bool:
    return prov.propagation in {ProvenanceLabel.REPORTED, ProvenanceLabel.CALCULATED}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stress_model.py -v` then `make lint`
Expected: PASS (all tests, including the pre-existing ones); ruff reports no errors.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/evidence.py tests/test_stress_model.py
git commit -m "feat(engine): add provenance value objects and tier vocabulary"
```

---

### Task 2: Shock, structural relationship, and result types (`propagation.py`)

**Files:**
- Create: `src/fragility_map/model/propagation.py`
- Test: `tests/test_stress_model.py` (append)

**Interfaces:**
- Consumes: `StructureType`, `EdgeProvenance` from `evidence.py`.
- Produces:
  - `Shock` (frozen dataclass): `source_company_id: str`, `incremental_gaap_loss: float | None = None`, `credit_status: str = "normal"`, `default_status: str = "not_defaulted"`. (`credit_status` ∈ `{"normal","severe_distress"}`; `default_status` ∈ `{"not_defaulted","defaulted"}`.)
  - `EdgeFlowShock` (frozen dataclass): `relationship_id: str`, `flow_change: float` — a shock applied *directly to a disclosed edge flow* (e.g. "MSFT purchases from CoreWeave −20%" → `flow_change=-0.20`).
  - `StructuralRelationship` (frozen dataclass): `relationship_id: str`, `source_company_id: str`, `target_company_id: str`, `structure_type: StructureType`, `provenance: EdgeProvenance`, `ownership_share: float | None = None`, `concentration: float | None = None`, `committed_envelope: float | None = None`, `source_accession: str | None = None`.
  - `EdgeResult` (frozen dataclass): `relationship_id: str`, `source_company_id: str`, `target_company_id: str`, `tier: Tier`, `result_kind: str`, `value: float | None`, `basis: str`. (`result_kind` ∈ `{"impact","exposure","realized_loss_unidentifiable","behavioural"}`.)
  - `NodeResult` (frozen dataclass): `company_id: str`, `quantified_impact: float | None`, `activated_exposure: float | None`, `epistemic_state: str`. (`epistemic_state` ∈ `{"quantified_impact","exposure_detected","not_identifiable","unaffected"}`.)
  - `ShockResult` (frozen dataclass): `edges: list[EdgeResult]`, `nodes: dict[str, NodeResult]`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stress_model.py`:

```python
from fragility_map.model.propagation import (
    EdgeFlowShock,
    Shock,
    StructuralRelationship,
)
from fragility_map.model.evidence import StructureType


def test_shock_defaults_are_normal_and_not_defaulted() -> None:
    shock = Shock("openai", incremental_gaap_loss=10_000)
    assert shock.credit_status == "normal"
    assert shock.default_status == "not_defaulted"


def test_structural_relationship_holds_only_disclosed_parameters() -> None:
    rel = StructuralRelationship(
        "openai-msft",
        "openai",
        "msft",
        StructureType.EQUITY_METHOD,
        _reported_provenance(),
        ownership_share=0.27,
        source_accession="msft-10k-2025",
    )
    assert rel.ownership_share == 0.27
    assert rel.concentration is None
    assert rel.committed_envelope is None


def _reported_provenance():
    from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel

    return EdgeProvenance(
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED,
        ProvenanceLabel.REPORTED,
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stress_model.py::test_shock_defaults_are_normal_and_not_defaulted -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fragility_map.model.propagation'`

- [ ] **Step 3: Write minimal implementation**

Create `src/fragility_map/model/propagation.py`:

```python
from dataclasses import dataclass

from fragility_map.model.evidence import EdgeProvenance, StructureType, Tier


@dataclass(frozen=True)
class Shock:
    source_company_id: str
    incremental_gaap_loss: float | None = None
    credit_status: str = "normal"
    default_status: str = "not_defaulted"


@dataclass(frozen=True)
class EdgeFlowShock:
    relationship_id: str
    flow_change: float


@dataclass(frozen=True)
class StructuralRelationship:
    relationship_id: str
    source_company_id: str
    target_company_id: str
    structure_type: StructureType
    provenance: EdgeProvenance
    ownership_share: float | None = None
    concentration: float | None = None
    committed_envelope: float | None = None
    source_accession: str | None = None


@dataclass(frozen=True)
class EdgeResult:
    relationship_id: str
    source_company_id: str
    target_company_id: str
    tier: Tier
    result_kind: str
    value: float | None
    basis: str


@dataclass(frozen=True)
class NodeResult:
    company_id: str
    quantified_impact: float | None
    activated_exposure: float | None
    epistemic_state: str


@dataclass(frozen=True)
class ShockResult:
    edges: list[EdgeResult]
    nodes: dict[str, NodeResult]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stress_model.py -v` then `make lint`
Expected: PASS; ruff clean. (Note: `Tier` import is used by later tasks; ruff `F401` would flag it now — if so, remove the `Tier` name from this import and re-add it in Task 3 where it is first used.)

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/propagation.py tests/test_stress_model.py
git commit -m "feat(engine): add Shock, StructuralRelationship, and result types"
```

---

### Task 3: Equity-method Impact (solid red)

**Files:**
- Modify: `src/fragility_map/model/propagation.py`
- Test: `tests/test_stress_model.py` (append)

**Interfaces:**
- Consumes: `Shock`, `StructuralRelationship` (Task 2); `quantifies_propagation`, `Tier`, `StructureType` (Tasks 1–2).
- Produces: `run_compound_shock(relationships: list[StructuralRelationship], shock: Shock) -> ShockResult`. In this task it handles only `EQUITY_METHOD` edges whose `source_company_id == shock.source_company_id`.

**Rule (ADR 0005):** an equity-method edge fires only when `shock.incremental_gaap_loss is not None` and `quantifies_propagation(edge.provenance)` is True. `value = -(ownership_share * incremental_gaap_loss)` (a loss, negative), `result_kind="impact"`, `tier=SOLID_RED`. The target node's `quantified_impact` accumulates this value and `epistemic_state="quantified_impact"`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stress_model.py`:

```python
from fragility_map.model.propagation import run_compound_shock
from fragility_map.model.evidence import EdgeProvenance, ProvenanceLabel, Tier


def _equity_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,   # relationship: ownership disclosed
        ProvenanceLabel.REPORTED,   # magnitude: loss stated in shock
        ProvenanceLabel.CALCULATED, # propagation: GAAP share is arithmetic
        ProvenanceLabel.CONSTRAINED,
    )


def test_equity_method_produces_solid_red_impact() -> None:
    rel = StructuralRelationship(
        "openai-msft",
        "openai",
        "msft",
        StructureType.EQUITY_METHOD,
        _equity_provenance(),
        ownership_share=0.27,
    )
    shock = Shock("openai", incremental_gaap_loss=10_000)

    result = run_compound_shock([rel], shock)

    edge = result.edges[0]
    assert edge.tier == Tier.SOLID_RED
    assert edge.result_kind == "impact"
    assert edge.value == -2_700.0
    node = result.nodes["msft"]
    assert node.quantified_impact == -2_700.0
    assert node.activated_exposure is None
    assert node.epistemic_state == "quantified_impact"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stress_model.py::test_equity_method_produces_solid_red_impact -v`
Expected: FAIL with `ImportError: cannot import name 'run_compound_shock'`

- [ ] **Step 3: Write minimal implementation**

Append to `src/fragility_map/model/propagation.py`:

```python
from fragility_map.model.evidence import quantifies_propagation


def run_compound_shock(
    relationships: list[StructuralRelationship],
    shock: Shock,
) -> ShockResult:
    edges: list[EdgeResult] = []
    nodes: dict[str, NodeResult] = {}

    for rel in relationships:
        if rel.source_company_id != shock.source_company_id:
            continue
        if rel.structure_type == StructureType.EQUITY_METHOD:
            if shock.incremental_gaap_loss is None or not quantifies_propagation(
                rel.provenance
            ):
                continue
            value = -(rel.ownership_share * shock.incremental_gaap_loss)
            edges.append(
                EdgeResult(
                    rel.relationship_id,
                    rel.source_company_id,
                    rel.target_company_id,
                    Tier.SOLID_RED,
                    "impact",
                    round(value, 6),
                    "equity-method share of stated GAAP loss",
                )
            )
            nodes[rel.target_company_id] = NodeResult(
                rel.target_company_id,
                quantified_impact=round(value, 6),
                activated_exposure=None,
                epistemic_state="quantified_impact",
            )

    return ShockResult(edges=edges, nodes=nodes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stress_model.py -v` then `make lint`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/propagation.py tests/test_stress_model.py
git commit -m "feat(engine): equity-method edges produce solid-red Impact"
```

---

### Task 4: Take-or-pay Exposure (solid orange), never a loss

**Files:**
- Modify: `src/fragility_map/model/propagation.py`
- Test: `tests/test_stress_model.py` (append)

**Interfaces:**
- Consumes: everything from Task 3.
- Produces: extends `run_compound_shock` to handle `TAKE_OR_PAY` edges.

**Rule (ADR 0005):** a take-or-pay edge *activates exposure* when the shock signals distress (`shock.credit_status == "severe_distress"` or `shock.default_status == "defaulted"`). `value = committed_envelope`, `result_kind="exposure"`, `tier=SOLID_ORANGE`, `basis="take-or-pay contract envelope activated (not a realized loss)"`. The target node's `activated_exposure` accumulates the envelope and, **if it has no quantified_impact**, `epistemic_state="exposure_detected"`. Exposure is NEVER written to `quantified_impact`.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stress_model.py`:

```python
def _take_or_pay_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,   # contract disclosed
        ProvenanceLabel.REPORTED,   # envelope amount disclosed
        ProvenanceLabel.CALCULATED, # envelope is a stated figure
        ProvenanceLabel.CONSTRAINED,
    )


def test_take_or_pay_produces_solid_orange_exposure_not_loss() -> None:
    rel = StructuralRelationship(
        "openai-coreweave",
        "openai",
        "coreweave",
        StructureType.TAKE_OR_PAY,
        _take_or_pay_provenance(),
        committed_envelope=11_900,
    )
    shock = Shock("openai", incremental_gaap_loss=10_000, credit_status="severe_distress")

    result = run_compound_shock([rel], shock)

    edge = result.edges[0]
    assert edge.tier == Tier.SOLID_ORANGE
    assert edge.result_kind == "exposure"
    assert edge.value == 11_900
    node = result.nodes["coreweave"]
    assert node.activated_exposure == 11_900
    assert node.quantified_impact is None
    assert node.epistemic_state == "exposure_detected"


def test_take_or_pay_stays_dormant_without_distress() -> None:
    rel = StructuralRelationship(
        "openai-coreweave",
        "openai",
        "coreweave",
        StructureType.TAKE_OR_PAY,
        _take_or_pay_provenance(),
        committed_envelope=11_900,
    )
    shock = Shock("openai", incremental_gaap_loss=10_000)  # credit_status defaults normal

    result = run_compound_shock([rel], shock)

    assert result.edges == []
    assert "coreweave" not in result.nodes
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stress_model.py::test_take_or_pay_produces_solid_orange_exposure_not_loss -v`
Expected: FAIL with `IndexError: list index out of range` (no edge produced yet).

- [ ] **Step 3: Write minimal implementation**

In `run_compound_shock`, add an `elif` branch after the `EQUITY_METHOD` block, inside the loop:

```python
        elif rel.structure_type == StructureType.TAKE_OR_PAY:
            distressed = (
                shock.credit_status == "severe_distress"
                or shock.default_status == "defaulted"
            )
            if not distressed or not quantifies_propagation(rel.provenance):
                continue
            edges.append(
                EdgeResult(
                    rel.relationship_id,
                    rel.source_company_id,
                    rel.target_company_id,
                    Tier.SOLID_ORANGE,
                    "exposure",
                    rel.committed_envelope,
                    "take-or-pay contract envelope activated (not a realized loss)",
                )
            )
            existing = nodes.get(rel.target_company_id)
            impact = existing.quantified_impact if existing else None
            nodes[rel.target_company_id] = NodeResult(
                rel.target_company_id,
                quantified_impact=impact,
                activated_exposure=rel.committed_envelope,
                epistemic_state=(
                    "quantified_impact" if impact is not None else "exposure_detected"
                ),
            )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stress_model.py -v` then `make lint`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/propagation.py tests/test_stress_model.py
git commit -m "feat(engine): take-or-pay edges activate solid-orange Exposure"
```

---

### Task 5: Evidence-only dissolve — unconstrained propagation stops the number

**Files:**
- Modify: `src/fragility_map/model/propagation.py`
- Test: `tests/test_stress_model.py` (append)

**Interfaces:**
- Consumes: everything from Task 4.
- Produces: extends `run_compound_shock` so that `BEHAVIOURAL` edges (and any edge whose `propagation` provenance is not `reported`/`calculated`) emit a `DIFFUSE_AMBER` edge with `value=None`, `result_kind="behavioural"`, and set the target node (if not already quantified) to `epistemic_state="not_identifiable"` with both numeric fields `None`.

**Rule (ADRs 0002–0004):** the shock still *travels* to the target (a documented dependency path) but carries no number.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stress_model.py`:

```python
def _behavioural_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,   # relationship exists (disclosed dependency)
        ProvenanceLabel.ASSUMED,
        ProvenanceLabel.ASSUMED,    # propagation NOT constrained
        ProvenanceLabel.ASSUMED,
    )


def test_behavioural_edge_dissolves_to_diffuse_amber_without_number() -> None:
    rel = StructuralRelationship(
        "coreweave-nvda",
        "coreweave",
        "nvda",
        StructureType.BEHAVIOURAL,
        _behavioural_provenance(),
    )
    shock = Shock("coreweave", incremental_gaap_loss=5_000, credit_status="severe_distress")

    result = run_compound_shock([rel], shock)

    edge = result.edges[0]
    assert edge.tier == Tier.DIFFUSE_AMBER
    assert edge.result_kind == "behavioural"
    assert edge.value is None
    node = result.nodes["nvda"]
    assert node.quantified_impact is None
    assert node.activated_exposure is None
    assert node.epistemic_state == "not_identifiable"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stress_model.py::test_behavioural_edge_dissolves_to_diffuse_amber_without_number -v`
Expected: FAIL with `IndexError: list index out of range`.

- [ ] **Step 3: Write minimal implementation**

Add a final `elif` branch inside the loop (after the `TAKE_OR_PAY` block):

```python
        elif rel.structure_type == StructureType.BEHAVIOURAL or not quantifies_propagation(
            rel.provenance
        ):
            edges.append(
                EdgeResult(
                    rel.relationship_id,
                    rel.source_company_id,
                    rel.target_company_id,
                    Tier.DIFFUSE_AMBER,
                    "behavioural",
                    None,
                    "documented dependency; magnitude not identifiable from evidence",
                )
            )
            if rel.target_company_id not in nodes:
                nodes[rel.target_company_id] = NodeResult(
                    rel.target_company_id,
                    quantified_impact=None,
                    activated_exposure=None,
                    epistemic_state="not_identifiable",
                )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stress_model.py -v` then `make lint`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/propagation.py tests/test_stress_model.py
git commit -m "feat(engine): behavioural/unconstrained edges dissolve to diffuse amber"
```

---

### Task 6: Edge-flow vs aggregate guardrail (customer concentration)

**Files:**
- Modify: `src/fragility_map/model/propagation.py`
- Test: `tests/test_stress_model.py` (append)

**Interfaces:**
- Consumes: everything from Task 5.
- Produces: `run_edge_flow_shock(relationships: list[StructuralRelationship], shock: EdgeFlowShock) -> ShockResult` — a *separate* entry point for shocks applied directly to a disclosed edge flow. A `CUSTOMER_CONCENTRATION` edge targeted by an `EdgeFlowShock` produces a `SOLID_ORANGE` Exposure `value = concentration * flow_change` (signed). There is deliberately **no** path by which a compound `Shock` (an aggregate) fires a concentration edge — that keeps "MSFT earnings −20% → CoreWeave −12.4%" impossible, per ADR 0004.

**Rule:** the guardrail is enforced *structurally* by having two entry points: `run_compound_shock` (aggregate/credit event) never quantifies a concentration edge; only `run_edge_flow_shock` does, and only for the one relationship it names.

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stress_model.py`:

```python
from fragility_map.model.propagation import run_edge_flow_shock
from fragility_map.model.evidence import quantifies_propagation as _qp  # noqa: F401


def _concentration_provenance() -> EdgeProvenance:
    return EdgeProvenance(
        ProvenanceLabel.REPORTED,   # 62% disclosed in S-1
        ProvenanceLabel.REPORTED,
        ProvenanceLabel.CALCULATED, # first-order 0.62 x flow
        ProvenanceLabel.CONSTRAINED,
    )


def test_concentration_edge_is_solid_only_under_edge_flow_shock() -> None:
    rel = StructuralRelationship(
        "msft-coreweave",
        "msft",
        "coreweave",
        StructureType.CUSTOMER_CONCENTRATION,
        _concentration_provenance(),
        concentration=0.62,
    )

    flow_result = run_edge_flow_shock([rel], EdgeFlowShock("msft-coreweave", flow_change=-0.20))
    edge = flow_result.edges[0]
    assert edge.tier == Tier.SOLID_ORANGE
    assert edge.result_kind == "exposure"
    assert edge.value == -0.124  # 0.62 * -0.20


def test_aggregate_shock_never_quantifies_a_concentration_edge() -> None:
    rel = StructuralRelationship(
        "msft-coreweave",
        "msft",
        "coreweave",
        StructureType.CUSTOMER_CONCENTRATION,
        _concentration_provenance(),
        concentration=0.62,
    )
    # An aggregate credit event on MSFT must not travel the concentration edge as a number.
    result = run_compound_shock([rel], Shock("msft", incremental_gaap_loss=10_000))
    assert result.edges == []
    assert result.nodes == {}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stress_model.py::test_concentration_edge_is_solid_only_under_edge_flow_shock -v`
Expected: FAIL with `ImportError: cannot import name 'run_edge_flow_shock'`

- [ ] **Step 3: Write minimal implementation**

First, in `run_compound_shock`, ensure a `CUSTOMER_CONCENTRATION` edge under an aggregate shock produces nothing: add an explicit guard as the first check inside the loop, right after the `source_company_id` filter:

```python
        if rel.structure_type == StructureType.CUSTOMER_CONCENTRATION:
            # Guardrail (ADR 0004): concentration only quantifies under an edge-flow shock.
            continue
```

Then append the new entry point to `propagation.py`:

```python
def run_edge_flow_shock(
    relationships: list[StructuralRelationship],
    shock: EdgeFlowShock,
) -> ShockResult:
    edges: list[EdgeResult] = []
    nodes: dict[str, NodeResult] = {}
    for rel in relationships:
        if rel.relationship_id != shock.relationship_id:
            continue
        if rel.structure_type != StructureType.CUSTOMER_CONCENTRATION:
            continue
        if rel.concentration is None or not quantifies_propagation(rel.provenance):
            continue
        value = round(rel.concentration * shock.flow_change, 6)
        edges.append(
            EdgeResult(
                rel.relationship_id,
                rel.source_company_id,
                rel.target_company_id,
                Tier.SOLID_ORANGE,
                "exposure",
                value,
                "disclosed customer-concentration exposure to an edge-flow change",
            )
        )
        nodes[rel.target_company_id] = NodeResult(
            rel.target_company_id,
            quantified_impact=None,
            activated_exposure=value,
            epistemic_state="exposure_detected",
        )
    return ShockResult(edges=edges, nodes=nodes)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stress_model.py -v` then `make lint`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/propagation.py tests/test_stress_model.py
git commit -m "feat(engine): edge-flow vs aggregate guardrail for concentration edges"
```

---

### Task 7: Vulnerability ranking excludes unquantified nodes

**Files:**
- Modify: `src/fragility_map/model/propagation.py`
- Test: `tests/test_stress_model.py` (append)

**Interfaces:**
- Consumes: `ShockResult`, `NodeResult` (Task 2).
- Produces: `rank_vulnerability(result: ShockResult) -> list[tuple[str, float]]` — returns `(company_id, magnitude)` pairs sorted by magnitude descending, where magnitude is `abs(quantified_impact)` for nodes with a quantified impact. Nodes whose `epistemic_state` is `"exposure_detected"`, `"not_identifiable"`, or `"unaffected"` are **excluded entirely** (ADR 0003: no ranking on unsupported numbers).

- [ ] **Step 1: Write the failing test**

Append to `tests/test_stress_model.py`:

```python
from fragility_map.model.propagation import NodeResult, ShockResult, rank_vulnerability


def test_ranking_excludes_exposure_and_unidentifiable_nodes() -> None:
    result = ShockResult(
        edges=[],
        nodes={
            "msft": NodeResult("msft", quantified_impact=-2_700.0, activated_exposure=None,
                               epistemic_state="quantified_impact"),
            "coreweave": NodeResult("coreweave", quantified_impact=None,
                                    activated_exposure=11_900, epistemic_state="exposure_detected"),
            "nvda": NodeResult("nvda", quantified_impact=None, activated_exposure=None,
                               epistemic_state="not_identifiable"),
        },
    )

    ranking = rank_vulnerability(result)

    assert ranking == [("msft", 2_700.0)]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_stress_model.py::test_ranking_excludes_exposure_and_unidentifiable_nodes -v`
Expected: FAIL with `ImportError: cannot import name 'rank_vulnerability'`

- [ ] **Step 3: Write minimal implementation**

Append to `propagation.py`:

```python
def rank_vulnerability(result: ShockResult) -> list[tuple[str, float]]:
    ranked = [
        (node.company_id, abs(node.quantified_impact))
        for node in result.nodes.values()
        if node.epistemic_state == "quantified_impact" and node.quantified_impact is not None
    ]
    ranked.sort(key=lambda pair: pair[1], reverse=True)
    return ranked
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_stress_model.py -v` then `make lint`
Expected: PASS; ruff clean.

- [ ] **Step 5: Commit**

```bash
git add src/fragility_map/model/propagation.py tests/test_stress_model.py
git commit -m "feat(engine): vulnerability ranking excludes unquantified nodes"
```

---

### Task 8: Hero-scenario integration test (one Shock, two structural results)

**Files:**
- Test: `tests/test_stress_model.py` (append)

**Interfaces:**
- Consumes: the whole engine.
- Produces: no new source — an integration test proving ADR 0005's headline: one compound Shock lights a solid-red Impact (MSFT) and a solid-orange Exposure (CoreWeave) at once, with the downstream behavioural hop dissolving.

- [ ] **Step 1: Write the failing test** (it should pass immediately if Tasks 3–5 are correct; this is a guard/regression test)

Append to `tests/test_stress_model.py`:

```python
def test_hero_compound_credit_event_lights_impact_and_exposure() -> None:
    equity = StructuralRelationship(
        "openai-msft", "openai", "msft", StructureType.EQUITY_METHOD,
        _equity_provenance(), ownership_share=0.27,
    )
    take_or_pay = StructuralRelationship(
        "openai-coreweave", "openai", "coreweave", StructureType.TAKE_OR_PAY,
        _take_or_pay_provenance(), committed_envelope=11_900,
    )
    downstream = StructuralRelationship(
        "coreweave-nvda", "openai", "nvda", StructureType.BEHAVIOURAL,
        _behavioural_provenance(),
    )
    shock = Shock("openai", incremental_gaap_loss=10_000, credit_status="severe_distress")

    result = run_compound_shock([equity, take_or_pay, downstream], shock)

    assert result.nodes["msft"].epistemic_state == "quantified_impact"
    assert result.nodes["msft"].quantified_impact == -2_700.0
    assert result.nodes["coreweave"].epistemic_state == "exposure_detected"
    assert result.nodes["coreweave"].activated_exposure == 11_900
    assert result.nodes["nvda"].epistemic_state == "not_identifiable"
    tiers = {e.relationship_id: e.tier for e in result.edges}
    assert tiers["openai-msft"] == Tier.SOLID_RED
    assert tiers["openai-coreweave"] == Tier.SOLID_ORANGE
    assert tiers["coreweave-nvda"] == Tier.DIFFUSE_AMBER
```

- [ ] **Step 2: Run test to verify current behaviour**

Run: `pytest tests/test_stress_model.py::test_hero_compound_credit_event_lights_impact_and_exposure -v`
Expected: PASS (if it fails, the defect is in Tasks 3–5 — fix there, do not weaken this test).

- [ ] **Step 3: Full suite + lint**

Run: `make test` then `make lint`
Expected: entire suite PASS; ruff clean.

- [ ] **Step 4: Commit**

```bash
git add tests/test_stress_model.py
git commit -m "test(engine): hero compound-credit-event integration test"
```

---

## Self-Review

**Spec coverage (issue #1 → task):** structural-only propagation → T3/T4/T6; evidence-only dissolve default → T5; Impact vs Exposure split → T3 vs T4; four tiers → T1 vocab + T3–T6 emission; four provenance labels per edge → T1/T2; compound-shock multi-state input → T2/T3/T4; edge-flow vs aggregate guardrail → T6; ranking excludes unquantified → T7; hero scenario (two results, one button) → T8. **Deferred to follow-up plans (out of this plan's scope, noted below):** scenario mode / sensitivity mode entry points; realized-loss `dashed_amber` object; LLM candidate proposal + mechanical verifier; API endpoint + v2 payload; frontend rendering; seed data with real accessions.

**Placeholder scan:** no TBD/TODO; every code step shows complete code; every test step shows the assertion.

**Type consistency:** `run_compound_shock(relationships, shock)`, `run_edge_flow_shock(relationships, shock)`, `rank_vulnerability(result)`, `EdgeResult`/`NodeResult`/`ShockResult` field names, and the `result_kind`/`epistemic_state`/`tier` string domains are used identically across T2–T8.

---

## Follow-up plans (separate specs' subsystems — not in this plan)

- **Plan 2 — Live extraction + mechanical verifier (ADR 0006).** Seam: `tests/test_relationship_extraction.py` + `tests/fixtures/`. LLM proposes a typed candidate behind a stubbable interface; a pure `verify_candidate(filing_text, candidate)` returns per-check results with `semantic_interpretation="pending_human_review"`; candidate lifecycle proposed→approved/edited/rejected + audit log.
- **Plan 3 — API v2 + seed + frontend rendering.** New endpoint `POST /api/scenario/compound-credit-event`, `build_evidence_payload()`, the verified MSFT/OpenAI/CoreWeave seed triangle with real EDGAR accessions (verification debt paid first), `frontend/src/types.ts` v2, four-tier map rendering + dissolve marker + result panel + review UI. Retire the legacy `run_cloud_spending_slowdown` path once the frontend migrates.
- **Engine extras (fold into Plan 3 or a Plan 4):** scenario mode (conditional intervals) and sensitivity mode (output-vs-parameter table + threshold) entry points on the engine, and the `dashed_amber` realized-loss-unidentifiable object.
