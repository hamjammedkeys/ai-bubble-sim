# Sub-project 4: Calc Engine + Scenarios Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A deterministic, LLM-free structural calc engine that turns a shock into per-edge results honoring the Impact-vs-Exposure distinction (ADR 0005), plus the hero compound credit-event scenario and a `POST /scenarios/{id}/run` endpoint — so the two headline figures ($2.7B equity-method **impact**, $11.9B disclosed **exposure**) come out right and are never conflated.

**Architecture:** New pure `app/engine/` package: `models.py` (Shock, EdgeInput, EdgeResult), `rules.py` (structural rule functions keyed by `relationship_type` + behavioural unresolved), `scenario.py` (`run_scenario` + `edge_touches_shock` + visual-state grammar). None of it touches the DB or an LLM. A `app/routers/scenarios.py` router builds `EdgeInput`s from **approved** edges only, runs the engine, persists a `ScenarioRun`, and returns results.

**Tech Stack:** Python (uv), Pydantic v2, FastAPI, SQLAlchemy. Builds on SP1 (models: Edge, Entity, Scenario, ScenarioRun) and SP3 (approved edges exist).

## Global Constraints

- Work only inside `revamp/backend/`. Never touch files outside `revamp/`.
- **The engine never calls the LLM and never reads the DB directly** (plan §2). Rules operate on `EdgeInput` value objects; the router does the DB→EdgeInput mapping.
- **Impact vs Exposure is sacred (ADR 0005, plan §16 "never cut"):** an *impact* (equity-method share of a disclosed net loss) is a forced loss → `kind="impact"`, `visual_state="solid_red"`. An *exposure* (disclosed contract/obligation ceiling) is an amount at risk whose realized loss needs undisclosed PD/LGD/EAD → `kind="exposure"`, `visual_state="solid_orange"`, `realized_loss` ALWAYS `None`. **Never sum a contract value into a loss; never print an exposure as a realized loss.**
- Behavioural / operational / supplier / commercial-spending edges are **never computed** → `kind="unresolved"`, `value=None`, `visual_state="dashed_amber"`.
- Only `status='approved'` edges ever reach the engine (candidates are hard-filtered at the router, plan §10).
- Equity-method impact = `shock.magnitude * ownership_fraction`, where a percent-style `value` (unit `percent`/`ownership_pct`, or value > 1) is divided by 100.
- `edge_touches_shock(edge, shock)` is true when `shock.origin_entity` equals the edge's source or target entity.
- Run commands from `revamp/backend/`. Test command: `uv run pytest`. TDD: failing test first, commit after each green task.

---

### Task 1: Engine value models

**Files:**
- Create: `revamp/backend/app/engine/__init__.py`
- Create: `revamp/backend/app/engine/models.py`
- Create: `revamp/backend/tests/test_engine_models.py`

**Interfaces:**
- Produces (Pydantic v2 models):
  - `Shock(origin_entity: str, kind: str, magnitude: float | None = None, unit: str | None = None, description: str | None = None)`
  - `EdgeInput(id, source_entity, target_entity, relationship_type, metric: str | None = None, value: float | None = None, unit: str | None = None, period: str | None = None, evidence_class: str)`
  - `EdgeResult(edge_id, source_entity, target_entity, relationship_type, kind: str, value: float | None, unit: str | None, label: str, caveat: str, realized_loss: float | None, evidence_class: str, visual_state: str)`

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_engine_models.py`:

```python
from app.engine.models import EdgeInput, EdgeResult, Shock


def test_shock_defaults():
    s = Shock(origin_entity="OpenAI", kind="gaap_loss", magnitude=10.0, unit="usd_billions")
    assert s.origin_entity == "OpenAI"
    assert s.magnitude == 10.0
    assert s.description is None


def test_edge_input_optional_value():
    e = EdgeInput(
        id="e1",
        source_entity="Nvidia",
        target_entity="CoreWeave",
        relationship_type="supplier_dependency",
        evidence_class="unknown",
    )
    assert e.value is None


def test_edge_result_carries_kind_and_visual():
    r = EdgeResult(
        edge_id="e1",
        source_entity="Microsoft",
        target_entity="OpenAI",
        relationship_type="equity_method",
        kind="impact",
        value=2.7,
        unit="usd_billions",
        label="$2.7B indicative equity-method impact",
        caveat="accounting basis",
        realized_loss=None,
        evidence_class="calculated",
        visual_state="solid_red",
    )
    assert r.kind == "impact"
    assert r.realized_loss is None
    assert r.visual_state == "solid_red"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine_models.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.engine'`.

- [ ] **Step 3: Write the models**

Create empty `revamp/backend/app/engine/__init__.py`.

Create `revamp/backend/app/engine/models.py`:

```python
from pydantic import BaseModel


class Shock(BaseModel):
    origin_entity: str
    kind: str
    magnitude: float | None = None
    unit: str | None = None
    description: str | None = None


class EdgeInput(BaseModel):
    id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    evidence_class: str


class EdgeResult(BaseModel):
    edge_id: str
    source_entity: str
    target_entity: str
    relationship_type: str
    kind: str  # "impact" | "exposure" | "unresolved"
    value: float | None
    unit: str | None
    label: str
    caveat: str
    realized_loss: float | None
    evidence_class: str
    visual_state: str  # "solid_red" | "solid_orange" | "dashed_amber"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine_models.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add app/engine/__init__.py app/engine/models.py tests/test_engine_models.py
git commit -m "feat(revamp/backend): add engine value models (Shock/EdgeInput/EdgeResult)"
```

---

### Task 2: Structural rules + registries

**Files:**
- Create: `revamp/backend/app/engine/rules.py`
- Create: `revamp/backend/tests/test_engine_rules.py`

**Interfaces:**
- Consumes: `app.engine.models` (Shock, EdgeInput, EdgeResult).
- Produces:
  - `equity_method_rule(edge, shock) -> EdgeResult` — `kind="impact"`, `value = shock.magnitude * ownership_fraction`, `realized_loss=None`, `visual_state="solid_red"`. `_ownership_fraction(edge)` divides a percent-style value by 100.
  - `exposure_rule(edge, shock) -> EdgeResult` — `kind="exposure"`, `value = edge.value` (the disclosed ceiling), `realized_loss=None`, `visual_state="solid_orange"`; caveat states PD/LGD/EAD are missing.
  - `investment_exposure_rule(edge, shock) -> EdgeResult` — like `exposure_rule` (reported exposure, no downstream multiplier).
  - `unresolved_result(edge) -> EdgeResult` — `kind="unresolved"`, `value=None`, `realized_loss=None`, `visual_state="dashed_amber"`, label "unknown — assumption required".
  - `STRUCTURAL_RULES: dict[str, callable]` keyed by `equity_method, customer_concentration, purchase_obligation, take_or_pay, counterparty_credit_exposure, investment_exposure`.
  - `BEHAVIOURAL_TYPES: frozenset[str]` = `{behavioural_response, operational_dependency, supplier_dependency, commercial_spending}`.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_engine_rules.py`:

```python
from app.engine.models import EdgeInput, Shock
from app.engine.rules import (
    BEHAVIOURAL_TYPES,
    STRUCTURAL_RULES,
    equity_method_rule,
    exposure_rule,
    unresolved_result,
)

SHOCK = Shock(origin_entity="OpenAI", kind="gaap_loss", magnitude=10.0, unit="usd_billions")


def _edge(**over) -> EdgeInput:
    base = dict(
        id="e1",
        source_entity="Microsoft",
        target_entity="OpenAI",
        relationship_type="equity_method",
        metric="ownership_pct",
        value=27.0,
        unit="percent",
        period="FY2026",
        evidence_class="reported",
    )
    base.update(over)
    return EdgeInput(**base)


def test_equity_method_computes_2_7B_impact():
    r = equity_method_rule(_edge(), SHOCK)
    assert r.kind == "impact"
    assert round(r.value, 2) == 2.7          # 10 * 0.27
    assert r.realized_loss is None
    assert r.visual_state == "solid_red"


def test_exposure_surfaces_ceiling_not_loss():
    edge = _edge(
        source_entity="OpenAI",
        target_entity="CoreWeave",
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
    )
    r = exposure_rule(edge, SHOCK)
    assert r.kind == "exposure"
    assert r.value == 11.9                    # disclosed ceiling, surfaced as-is
    assert r.realized_loss is None            # NEVER a realized loss
    assert r.visual_state == "solid_orange"
    assert "PD" in r.caveat or "realized" in r.caveat.lower()


def test_exposure_is_never_an_impact():
    edge = _edge(relationship_type="take_or_pay", source_entity="OpenAI", target_entity="Oracle", value=30.0)
    r = exposure_rule(edge, SHOCK)
    assert r.kind != "impact"
    assert r.realized_loss is None


def test_behavioural_edge_is_unresolved():
    edge = _edge(relationship_type="supplier_dependency", source_entity="CoreWeave", target_entity="Nvidia", value=None, evidence_class="unknown")
    r = unresolved_result(edge)
    assert r.kind == "unresolved"
    assert r.value is None
    assert r.visual_state == "dashed_amber"


def test_registries_partition_the_types():
    assert "equity_method" in STRUCTURAL_RULES
    assert "purchase_obligation" in STRUCTURAL_RULES
    assert "supplier_dependency" in BEHAVIOURAL_TYPES
    assert set(STRUCTURAL_RULES).isdisjoint(BEHAVIOURAL_TYPES)


def test_ownership_fraction_handles_already_fractional():
    # a value <= 1 with no percent unit is treated as an already-fractional ownership
    edge = _edge(value=0.27, unit=None)
    r = equity_method_rule(edge, SHOCK)
    assert round(r.value, 2) == 2.7
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine_rules.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.engine.rules'`.

- [ ] **Step 3: Write the rules**

Create `revamp/backend/app/engine/rules.py`:

```python
from app.engine.models import EdgeInput, EdgeResult, Shock

_PERCENT_UNITS = {"percent", "ownership_pct", "pct", "%"}


def _ownership_fraction(edge: EdgeInput) -> float:
    value = edge.value or 0.0
    if edge.unit in _PERCENT_UNITS or value > 1:
        return value / 100.0
    return value


def equity_method_rule(edge: EdgeInput, shock: Shock) -> EdgeResult:
    magnitude = shock.magnitude or 0.0
    impact = magnitude * _ownership_fraction(edge)
    return EdgeResult(
        edge_id=edge.id,
        source_entity=edge.source_entity,
        target_entity=edge.target_entity,
        relationship_type=edge.relationship_type,
        kind="impact",
        value=impact,
        unit=shock.unit,
        label=f"${impact:.1f}B indicative equity-method impact",
        caveat="Accounting-basis: this is the equity-method share of a disclosed net loss, not a cash loss.",
        realized_loss=None,
        evidence_class="calculated",
        visual_state="solid_red",
    )


def _exposure(edge: EdgeInput, kind_label: str) -> EdgeResult:
    return EdgeResult(
        edge_id=edge.id,
        source_entity=edge.source_entity,
        target_entity=edge.target_entity,
        relationship_type=edge.relationship_type,
        kind="exposure",
        value=edge.value,
        unit=edge.unit,
        label=f"${edge.value:.1f}B {kind_label} disclosed" if edge.value is not None else f"{kind_label} disclosed",
        caveat="Exposure-at-risk, not a realized loss: realizing it needs PD/LGD/EAD, which no filing discloses.",
        realized_loss=None,
        evidence_class=edge.evidence_class,
        visual_state="solid_orange",
    )


def exposure_rule(edge: EdgeInput, shock: Shock) -> EdgeResult:
    return _exposure(edge, "contract exposure")


def investment_exposure_rule(edge: EdgeInput, shock: Shock) -> EdgeResult:
    return _exposure(edge, "reported investment exposure")


def unresolved_result(edge: EdgeInput) -> EdgeResult:
    return EdgeResult(
        edge_id=edge.id,
        source_entity=edge.source_entity,
        target_entity=edge.target_entity,
        relationship_type=edge.relationship_type,
        kind="unresolved",
        value=None,
        unit=None,
        label="unknown — assumption required",
        caveat="Documented relationship, but no filing discloses how a shock propagates here, so the engine refuses to invent a number.",
        realized_loss=None,
        evidence_class=edge.evidence_class,
        visual_state="dashed_amber",
    )


STRUCTURAL_RULES = {
    "equity_method": equity_method_rule,
    "customer_concentration": exposure_rule,
    "purchase_obligation": exposure_rule,
    "take_or_pay": exposure_rule,
    "counterparty_credit_exposure": exposure_rule,
    "investment_exposure": investment_exposure_rule,
}

BEHAVIOURAL_TYPES = frozenset(
    {
        "behavioural_response",
        "operational_dependency",
        "supplier_dependency",
        "commercial_spending",
    }
)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine_rules.py -v`
Expected: PASS (all six).

- [ ] **Step 5: Commit**

```bash
git add app/engine/rules.py tests/test_engine_rules.py
git commit -m "feat(revamp/backend): add structural calc rules with impact/exposure split"
```

---

### Task 3: run_scenario + visual grammar

**Files:**
- Create: `revamp/backend/app/engine/scenario.py`
- Create: `revamp/backend/tests/test_engine_scenario.py`

**Interfaces:**
- Consumes: `app.engine.models`, `app.engine.rules`.
- Produces:
  - `edge_touches_shock(edge: EdgeInput, shock: Shock) -> bool` — true when `shock.origin_entity` is the edge's source or target.
  - `run_scenario(shock: Shock, edges: list[EdgeInput]) -> list[EdgeResult]` — for each **touched** edge: if `relationship_type in STRUCTURAL_RULES` apply the rule; elif in `BEHAVIOURAL_TYPES` append `unresolved_result`; else skip. Untouched edges produce no result (the frontend greys them). Deterministic order = input order.
  - `totals(results) -> dict` — `{"impact_total": sum of impact values, "exposure_total": sum of exposure values, "unresolved_count": n}`; `impact_total` sums ONLY `kind=="impact"`, `exposure_total` sums ONLY `kind=="exposure"` — the two are never combined.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_engine_scenario.py`:

```python
from app.engine.models import EdgeInput, Shock
from app.engine.scenario import edge_touches_shock, run_scenario, totals

SHOCK = Shock(origin_entity="OpenAI", kind="gaap_loss", magnitude=10.0, unit="usd_billions")


def _edges() -> list[EdgeInput]:
    return [
        EdgeInput(id="msft", source_entity="Microsoft", target_entity="OpenAI",
                  relationship_type="equity_method", metric="ownership_pct", value=27.0,
                  unit="percent", evidence_class="reported"),
        EdgeInput(id="cw", source_entity="OpenAI", target_entity="CoreWeave",
                  relationship_type="purchase_obligation", metric="contract_value", value=11.9,
                  unit="usd_billions", evidence_class="reported"),
        EdgeInput(id="nv", source_entity="CoreWeave", target_entity="Nvidia",
                  relationship_type="supplier_dependency", value=None, evidence_class="unknown"),
        EdgeInput(id="asml", source_entity="TSMC", target_entity="ASML",
                  relationship_type="supplier_dependency", value=None, evidence_class="unknown"),
    ]


def test_touch_detection():
    edges = _edges()
    assert edge_touches_shock(edges[0], SHOCK) is True   # MSFT->OpenAI
    assert edge_touches_shock(edges[1], SHOCK) is True   # OpenAI->CoreWeave
    assert edge_touches_shock(edges[3], SHOCK) is False  # TSMC->ASML untouched


def test_hero_scenario_produces_impact_and_exposure_separately():
    results = run_scenario(SHOCK, _edges())
    by_id = {r.edge_id: r for r in results}

    # untouched TSMC->ASML edge is not in the results
    assert "asml" not in by_id

    assert by_id["msft"].kind == "impact"
    assert round(by_id["msft"].value, 2) == 2.7
    assert by_id["msft"].visual_state == "solid_red"

    assert by_id["cw"].kind == "exposure"
    assert by_id["cw"].value == 11.9
    assert by_id["cw"].realized_loss is None
    assert by_id["cw"].visual_state == "solid_orange"

    assert by_id["nv"].kind == "unresolved"
    assert by_id["nv"].visual_state == "dashed_amber"


def test_totals_never_conflate_impact_and_exposure():
    t = totals(run_scenario(SHOCK, _edges()))
    assert round(t["impact_total"], 2) == 2.7      # only the equity-method impact
    assert t["exposure_total"] == 11.9             # only the disclosed exposure
    assert t["impact_total"] != t["exposure_total"]
    assert t["unresolved_count"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_engine_scenario.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.engine.scenario'`.

- [ ] **Step 3: Write the engine**

Create `revamp/backend/app/engine/scenario.py`:

```python
from app.engine.models import EdgeInput, EdgeResult, Shock
from app.engine.rules import BEHAVIOURAL_TYPES, STRUCTURAL_RULES, unresolved_result


def edge_touches_shock(edge: EdgeInput, shock: Shock) -> bool:
    return shock.origin_entity in (edge.source_entity, edge.target_entity)


def run_scenario(shock: Shock, edges: list[EdgeInput]) -> list[EdgeResult]:
    results: list[EdgeResult] = []
    for edge in edges:
        if not edge_touches_shock(edge, shock):
            continue
        if edge.relationship_type in STRUCTURAL_RULES:
            results.append(STRUCTURAL_RULES[edge.relationship_type](edge, shock))
        elif edge.relationship_type in BEHAVIOURAL_TYPES:
            results.append(unresolved_result(edge))
    return results


def totals(results: list[EdgeResult]) -> dict:
    impact_total = sum(r.value or 0.0 for r in results if r.kind == "impact")
    exposure_total = sum(r.value or 0.0 for r in results if r.kind == "exposure")
    unresolved_count = sum(1 for r in results if r.kind == "unresolved")
    return {
        "impact_total": impact_total,
        "exposure_total": exposure_total,
        "unresolved_count": unresolved_count,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_engine_scenario.py -v`
Expected: PASS (all three).

- [ ] **Step 5: Commit**

```bash
git add app/engine/scenario.py tests/test_engine_scenario.py
git commit -m "feat(revamp/backend): add run_scenario with impact/exposure totals"
```

---

### Task 4: Scenario persistence + endpoints

**Files:**
- Modify: `revamp/backend/app/schemas.py` (add scenario request/response models)
- Create: `revamp/backend/app/services/scenarios.py`
- Create: `revamp/backend/app/routers/scenarios.py`
- Modify: `revamp/backend/app/main.py` (include the scenarios router)
- Create: `revamp/backend/tests/test_scenarios_api.py`

**Interfaces:**
- Consumes: `app.engine` (Shock, EdgeInput, run_scenario, totals), `app.models` (Edge, Entity, Scenario, ScenarioRun), `app.db.get_session`.
- Produces schemas: `ScenarioOut(id, name, description)` (`from_attributes`); `ScenarioRunOut(scenario_id, results: list[dict], totals: dict, run_id: str)`.
- Produces `app.services.scenarios`:
  - `edges_to_inputs(session) -> list[EdgeInput]` — builds `EdgeInput` from every `status='approved'` Edge, resolving source/target entity names via `session.get(Entity, ...)`.
  - `shock_from_scenario(scenario) -> Shock` — reads `scenario.shock_json` (keys `origin_entity, kind, magnitude, unit, description`).
  - `run_and_store(session, scenario) -> tuple[list[EdgeResult], dict, ScenarioRun]` — builds inputs, runs `run_scenario`, computes `totals`, persists a `ScenarioRun(scenario_id, results={"results": [...], "totals": {...}})`, returns them.
- Produces endpoints:
  - `GET /scenarios -> list[ScenarioOut]`.
  - `POST /scenarios/{scenario_id}/run -> ScenarioRunOut` (404 if scenario unknown). Only approved edges participate.

- [ ] **Step 1: Add schemas**

Add to `revamp/backend/app/schemas.py`:

```python
class ScenarioOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str | None = None
    description: str | None = None


class ScenarioRunOut(BaseModel):
    scenario_id: str
    run_id: str
    results: list[dict]
    totals: dict
```

- [ ] **Step 2: Write the failing test**

Create `revamp/backend/tests/test_scenarios_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.db import get_session
from app.main import app
from app.models import Document, Edge, Entity, Scenario
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


def _seed_hero(db_engine) -> str:
    s = Session(db_engine)
    msft = Entity(name="Microsoft", aliases=[])
    openai = Entity(name="OpenAI", aliases=[])
    cw = Entity(name="CoreWeave", aliases=[])
    nv = Entity(name="Nvidia", aliases=[])
    s.add_all([msft, openai, cw, nv])
    s.flush()

    # approved equity_method MSFT->OpenAI (27%)
    s.add(Edge(source_entity_id=msft.id, target_entity_id=openai.id, relationship_type="equity_method",
               metric="ownership_pct", value=27.0, unit="percent", evidence_class="reported", status="approved"))
    # approved purchase_obligation OpenAI->CoreWeave ($11.9B)
    s.add(Edge(source_entity_id=openai.id, target_entity_id=cw.id, relationship_type="purchase_obligation",
               metric="contract_value", value=11.9, unit="usd_billions", evidence_class="reported", status="approved"))
    # behavioural CoreWeave->Nvidia
    s.add(Edge(source_entity_id=cw.id, target_entity_id=nv.id, relationship_type="supplier_dependency",
               evidence_class="unknown", status="approved"))
    # a CANDIDATE edge that must be ignored by the engine
    s.add(Edge(source_entity_id=openai.id, target_entity_id=nv.id, relationship_type="purchase_obligation",
               metric="contract_value", value=999.0, unit="usd_billions", evidence_class="reported", status="candidate"))

    scenario = Scenario(name="OpenAI credit event", description="+$10B GAAP loss",
                        shock_json={"origin_entity": "OpenAI", "kind": "gaap_loss", "magnitude": 10.0, "unit": "usd_billions"})
    s.add(scenario)
    s.commit()
    sid = scenario.id
    s.close()
    return sid


def test_run_hero_scenario_returns_impact_and_exposure(client, db_engine):
    sid = _seed_hero(db_engine)

    resp = client.post(f"/scenarios/{sid}/run")
    assert resp.status_code == 200
    body = resp.json()

    assert round(body["totals"]["impact_total"], 2) == 2.7
    assert body["totals"]["exposure_total"] == 11.9   # candidate $999B edge excluded
    assert body["totals"]["unresolved_count"] == 1

    kinds = {r["relationship_type"]: r for r in body["results"]}
    assert kinds["equity_method"]["kind"] == "impact"
    assert kinds["equity_method"]["visual_state"] == "solid_red"
    assert kinds["purchase_obligation"]["kind"] == "exposure"
    assert kinds["purchase_obligation"]["realized_loss"] is None


def test_list_scenarios(client, db_engine):
    _seed_hero(db_engine)
    resp = client.get("/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_run_unknown_scenario_404(client):
    assert client.post("/scenarios/nope/run").status_code == 404
```

- [ ] **Step 3: Run test to verify it fails**

Run: `uv run pytest tests/test_scenarios_api.py -v`
Expected: FAIL — scenarios router/service missing.

- [ ] **Step 4: Write the service**

Create `revamp/backend/app/services/scenarios.py`:

```python
from sqlalchemy.orm import Session

from app.engine.models import EdgeInput, EdgeResult, Shock
from app.engine.scenario import run_scenario, totals
from app.models import Edge, Entity, Scenario, ScenarioRun


def edges_to_inputs(session: Session) -> list[EdgeInput]:
    inputs: list[EdgeInput] = []
    approved = session.query(Edge).filter(Edge.status == "approved").all()
    for edge in approved:
        src = session.get(Entity, edge.source_entity_id) if edge.source_entity_id else None
        tgt = session.get(Entity, edge.target_entity_id) if edge.target_entity_id else None
        inputs.append(
            EdgeInput(
                id=edge.id,
                source_entity=src.name if src else "",
                target_entity=tgt.name if tgt else "",
                relationship_type=edge.relationship_type,
                metric=edge.metric,
                value=edge.value,
                unit=edge.unit,
                period=edge.period,
                evidence_class=edge.evidence_class,
            )
        )
    return inputs


def shock_from_scenario(scenario: Scenario) -> Shock:
    data = scenario.shock_json or {}
    return Shock(
        origin_entity=data.get("origin_entity", ""),
        kind=data.get("kind", "shock"),
        magnitude=data.get("magnitude"),
        unit=data.get("unit"),
        description=data.get("description"),
    )


def run_and_store(session: Session, scenario: Scenario) -> tuple[list[EdgeResult], dict, ScenarioRun]:
    shock = shock_from_scenario(scenario)
    results = run_scenario(shock, edges_to_inputs(session))
    tot = totals(results)
    run = ScenarioRun(
        scenario_id=scenario.id,
        results={"results": [r.model_dump() for r in results], "totals": tot},
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return results, tot, run
```

- [ ] **Step 5: Write the router**

Create `revamp/backend/app/routers/scenarios.py`:

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import Scenario
from app.schemas import ScenarioOut, ScenarioRunOut
from app.services.scenarios import run_and_store

router = APIRouter()


@router.get("/scenarios", response_model=list[ScenarioOut])
def list_scenarios(session: Session = Depends(get_session)):
    return session.query(Scenario).all()


@router.post("/scenarios/{scenario_id}/run", response_model=ScenarioRunOut)
def run_scenario_endpoint(scenario_id: str, session: Session = Depends(get_session)):
    scenario = session.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    results, tot, run = run_and_store(session, scenario)
    return ScenarioRunOut(
        scenario_id=scenario.id,
        run_id=run.id,
        results=[r.model_dump() for r in results],
        totals=tot,
    )
```

- [ ] **Step 6: Wire the router into main.py**

In `revamp/backend/app/main.py`, add `scenarios` to the routers import and include it:
- Change `from app.routers import documents, edges` to `from app.routers import documents, edges, scenarios`.
- After `app.include_router(edges.router)` add `app.include_router(scenarios.router)`.

- [ ] **Step 7: Run tests and commit**

Run: `uv run pytest tests/test_scenarios_api.py -v` then `uv run pytest`.
Expected: all green.

```bash
git add app/schemas.py app/services/scenarios.py app/routers/scenarios.py app/main.py tests/test_scenarios_api.py
git commit -m "feat(revamp/backend): scenario run endpoint over approved edges"
```

---

## Acceptance (whole sub-project)

- Engine is pure (no DB/LLM imports in `app/engine/`).
- Equity-method impact = 2.7 (10 × 27%), `kind="impact"`, `solid_red`.
- Disclosed exposure = 11.9, `kind="exposure"`, `realized_loss=None`, `solid_orange` — never summed into impact.
- Behavioural edges → `unresolved`, `dashed_amber`.
- `POST /scenarios/{id}/run` runs over **approved edges only** (a candidate $999B edge is excluded), persists a `ScenarioRun`, returns per-edge results + separated totals.
- `uv run pytest` — all green, offline.
