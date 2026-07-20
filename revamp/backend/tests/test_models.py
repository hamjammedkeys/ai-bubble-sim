from datetime import date

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app import db
from app.models import Document, Edge, Entity, Passage, Scenario, ScenarioRun


def _session(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setattr(db, "engine", engine)
    db.init_db()
    return sessionmaker(bind=engine, expire_on_commit=False)()


def test_edge_defaults_and_json_roundtrip(tmp_path, monkeypatch):
    s = _session(tmp_path, monkeypatch)

    openai = Entity(name="OpenAI", entity_type="model_company", aliases=["OAI"])
    coreweave = Entity(name="CoreWeave", entity_type="cloud_provider", aliases=[])
    doc = Document(title="CoreWeave S-1", filing_type="S-1", raw_text="... $11.9 billion ...", filed_date=date(2025, 3, 1))
    s.add_all([openai, coreweave, doc])
    s.flush()

    passage = Passage(document_id=doc.id, text="$11.9 billion", char_start=4, char_end=17, page_number=42)
    s.add(passage)
    s.flush()

    edge = Edge(
        source_entity_id=openai.id,
        target_entity_id=coreweave.id,
        relationship_type="purchase_obligation",
        metric="contract_value",
        value=11.9,
        unit="usd_billions",
        period="through_2030",
        evidence_class="reported",
        passage_id=passage.id,
        document_id=doc.id,
        verification={"passage_found": True, "match_score": 97},
    )
    s.add(edge)
    s.commit()

    fetched = s.get(Edge, edge.id)
    assert fetched.status == "candidate"          # default applied
    assert fetched.value == 11.9
    assert fetched.verification["match_score"] == 97   # JSON round-trip
    assert s.get(Entity, openai.id).aliases == ["OAI"]  # JSON list round-trip
    assert isinstance(fetched.id, str)             # string UUID PK


def test_all_six_tables_registered(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setattr(db, "engine", engine)
    db.init_db()
    tables = set(inspect(engine).get_table_names())
    assert {"documents", "passages", "entities", "edges", "scenarios", "scenario_runs"} <= tables


def test_scenario_and_scenario_run_roundtrip(tmp_path, monkeypatch):
    s = _session(tmp_path, monkeypatch)

    scenario = Scenario(
        name="Risk Shock",
        description="A shock scenario",
        shock_json={"target": "OpenAI", "gaap_loss_usd_bn": 10},
    )
    s.add(scenario)
    s.flush()

    scenario_run = ScenarioRun(
        scenario_id=scenario.id,
        results={"edges": [{"id": "e1", "impact": 2.7}]},
    )
    s.add(scenario_run)
    s.commit()

    fetched_scenario = s.get(Scenario, scenario.id)
    fetched_run = s.get(ScenarioRun, scenario_run.id)

    assert fetched_scenario.shock_json == {"target": "OpenAI", "gaap_loss_usd_bn": 10}  # JSON round-trip
    assert fetched_run.results == {"edges": [{"id": "e1", "impact": 2.7}]}  # JSON round-trip
    assert isinstance(fetched_scenario.id, str)  # string UUID PK
    assert isinstance(fetched_run.id, str)  # string UUID PK
    assert fetched_run.run_at is not None  # default applied
