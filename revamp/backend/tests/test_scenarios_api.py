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
    assert resp.json()[0]["origin_entity"] == "OpenAI"
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_run_unknown_scenario_404(client):
    assert client.post("/scenarios/nope/run").status_code == 404


def test_create_scenario_then_run_it(client, db_engine):
    _seed_hero(db_engine)  # entities + approved hero edges

    created = client.post(
        "/scenarios",
        json={"name": "Custom OpenAI shock", "origin_entity": "OpenAI", "magnitude": 10.0},
    )
    assert created.status_code == 201
    sid = created.json()["id"]

    # the new scenario is listed alongside the seeded one
    assert any(s["id"] == sid for s in client.get("/scenarios").json())

    # and it runs, producing the same structural split as the hero scenario
    run = client.post(f"/scenarios/{sid}/run").json()
    assert round(run["totals"]["impact_total"], 2) == 2.7
    assert run["totals"]["exposure_total"] == 11.9


def test_created_scenario_magnitude_scales_impact_not_exposure(client, db_engine):
    _seed_hero(db_engine)
    sid = client.post(
        "/scenarios",
        json={"name": "Severe", "origin_entity": "OpenAI", "magnitude": 20.0},
    ).json()["id"]
    totals = client.post(f"/scenarios/{sid}/run").json()["totals"]
    assert round(totals["impact_total"], 2) == 5.4     # 20 x 27% scales
    assert totals["exposure_total"] == 11.9            # disclosed ceiling unchanged
