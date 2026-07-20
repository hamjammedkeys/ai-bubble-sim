import json
from collections import Counter
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import main
from app.models import Document, Edge, Entity, Passage, Scenario
from app.services import hero_seed
from app.services.hero_seed import HERO_SCENARIO_NAME, seed_hero_if_empty


ENTITY_TYPES = {
    "Microsoft": "investor",
    "OpenAI": "model_company",
    "CoreWeave": "cloud_provider",
    "Nvidia": "gpu_maker",
    "TSMC": "foundry",
    "ASML": "equipment_maker",
}

SCENARIO_DESCRIPTION = "OpenAI reports a +$10B incremental GAAP loss under severe distress."
SCENARIO_SHOCK = {
    "origin_entity": "OpenAI",
    "kind": "gaap_loss",
    "magnitude": 10.0,
    "unit": "usd_billions",
}

PASS_VERIFICATION = {
    "overall": "pass",
    "passage_found": True,
    "match_score": 100,
    "number_found": True,
}

FLAG_VERIFICATION = {
    "overall": "flag",
    "passage_found": True,
    "match_score": 100,
    "number_found": True,
    "entities_found": False,
    "note": "passage describes data-center leases, not an OpenAI commitment",
}

MSFT_PASSAGE = "We have an investment of approximately 27 percent of OpenAI on an as-converted basis accounted for under the equity method of accounting."
CW_119_PASSAGE = (
    "OpenAI has committed to pay us up to approximately $11.9 billion through October 2030."
)
CW_65_PASSAGE = (
    "OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031."
)
CW_LEASE_PASSAGE = "The aggregate amount of estimated future undiscounted lease payments associated with such data-center leases is $11.9 billion."


def test_empty_database_is_seeded_once(db_engine):
    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "seeded"

    with Session(db_engine) as session:
        assert session.query(Entity).filter(Entity.name == "OpenAI").count() == 1
        assert session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).count() == 1


def test_seeded_database_matches_the_exact_hero_contract(db_engine):
    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "seeded"

    with Session(db_engine) as session:
        entities = {entity.name: entity.entity_type for entity in session.query(Entity)}
        assert entities == ENTITY_TYPES

        documents = {
            document.title: (
                document.filing_type,
                document.company,
                document.url,
                document.filed_date,
                document.period,
                document.raw_text,
            )
            for document in session.query(Document)
        }
        assert documents == {
            "Microsoft 10-Q, quarter ended March 31, 2026": (
                "10-Q",
                "Microsoft",
                "https://www.sec.gov/Archives/edgar/data/789019/000119312526191507/msft-20260331.htm",
                date(2026, 4, 29),
                "Q3 FY2026",
                "We have an investment of approximately 27 percent of OpenAI on an as-converted basis accounted for under the equity method of accounting. We have made total funding commitments of $13 billion, of which $11.8 billion has been funded as of March 31, 2026.",
            ),
            "CoreWeave S-1/A": (
                "S-1/A",
                "CoreWeave",
                "https://www.sec.gov/Archives/edgar/data/1769628/000119312525058309/d899798ds1a.htm",
                date(2025, 3, 20),
                "as of March 2025",
                "In March 2025, we entered into a master services agreement with OpenAI, a private company, pursuant to which OpenAI has committed to pay us up to approximately $11.9 billion through October 2030. The aggregate amount of estimated future undiscounted lease payments associated with such data-center leases is $11.9 billion.",
            ),
            "CoreWeave 10-Q, quarter ended March 31, 2026": (
                "10-Q",
                "CoreWeave",
                "https://www.sec.gov/Archives/edgar/data/1769628/000176962826000222/0001769628-26-000222-index.htm",
                date(2026, 5, 8),
                "Q1 2026",
                "In May 2025, we entered into a master services agreement with OpenAI OpCo, LLC and in September 2025 an order form under this master services agreement pursuant to which OpenAI has committed to pay us up to approximately $6.5 billion through May 31, 2031.",
            ),
        }

        document_titles = {document.id: document.title for document in session.query(Document)}
        passages = {
            (document_titles[passage.document_id], passage.text)
            for passage in session.query(Passage)
        }
        assert passages == {
            ("Microsoft 10-Q, quarter ended March 31, 2026", MSFT_PASSAGE),
            ("CoreWeave S-1/A", CW_119_PASSAGE),
            ("CoreWeave 10-Q, quarter ended March 31, 2026", CW_65_PASSAGE),
            ("CoreWeave S-1/A", CW_LEASE_PASSAGE),
        }

        entity_names = {entity.id: entity.name for entity in session.query(Entity)}
        passage_texts = {passage.id: passage.text for passage in session.query(Passage)}
        actual_edges = Counter(
            (
                entity_names[edge.source_entity_id],
                entity_names[edge.target_entity_id],
                edge.relationship_type,
                edge.metric,
                edge.value,
                edge.unit,
                edge.period,
                edge.evidence_class,
                edge.status,
                document_titles.get(edge.document_id),
                passage_texts.get(edge.passage_id),
                json.dumps(edge.verification, sort_keys=True),
            )
            for edge in session.query(Edge)
        )
        expected_edges = Counter(
            [
                (
                    "Microsoft",
                    "OpenAI",
                    "equity_method",
                    "ownership_pct",
                    27.0,
                    "percent",
                    "as-converted, as of Mar 31, 2026 (post Oct-2025 recap)",
                    "reported",
                    "approved",
                    "Microsoft 10-Q, quarter ended March 31, 2026",
                    MSFT_PASSAGE,
                    json.dumps(PASS_VERIFICATION, sort_keys=True),
                ),
                (
                    "OpenAI",
                    "CoreWeave",
                    "purchase_obligation",
                    "contract_value",
                    11.9,
                    "usd_billions",
                    "through October 2030",
                    "reported",
                    "approved",
                    "CoreWeave S-1/A",
                    CW_119_PASSAGE,
                    json.dumps(PASS_VERIFICATION, sort_keys=True),
                ),
                (
                    "CoreWeave",
                    "Nvidia",
                    "supplier_dependency",
                    None,
                    None,
                    None,
                    None,
                    "unknown",
                    "approved",
                    None,
                    None,
                    "null",
                ),
                (
                    "Nvidia",
                    "TSMC",
                    "supplier_dependency",
                    None,
                    None,
                    None,
                    None,
                    "unknown",
                    "approved",
                    None,
                    None,
                    "null",
                ),
                (
                    "TSMC",
                    "ASML",
                    "supplier_dependency",
                    None,
                    None,
                    None,
                    None,
                    "unknown",
                    "approved",
                    None,
                    None,
                    "null",
                ),
                (
                    "OpenAI",
                    "CoreWeave",
                    "purchase_obligation",
                    "contract_value",
                    6.5,
                    "usd_billions",
                    "through May 2031",
                    "reported",
                    "candidate",
                    "CoreWeave 10-Q, quarter ended March 31, 2026",
                    CW_65_PASSAGE,
                    json.dumps(PASS_VERIFICATION, sort_keys=True),
                ),
                (
                    "OpenAI",
                    "CoreWeave",
                    "purchase_obligation",
                    "contract_value",
                    11.9,
                    "usd_billions",
                    "lease term",
                    "reported",
                    "candidate",
                    "CoreWeave S-1/A",
                    CW_LEASE_PASSAGE,
                    json.dumps(FLAG_VERIFICATION, sort_keys=True),
                ),
            ]
        )
        assert actual_edges == expected_edges

        scenario = session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).one()
        assert scenario.description == SCENARIO_DESCRIPTION
        assert scenario.shock_json == SCENARIO_SHOCK
        assert session.query(Entity).count() == 6
        assert session.query(Document).count() == 3
        assert session.query(Passage).count() == 4
        assert session.query(Edge).filter(Edge.status == "approved").count() == 5
        assert session.query(Edge).filter(Edge.status == "candidate").count() == 2

        assert seed_hero_if_empty(session) == "already_seeded"
        session.commit()

        assert session.query(Entity).filter(Entity.name == "OpenAI").count() == 1
        assert session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).count() == 1


def test_nonempty_database_is_preserved(db_engine):
    with Session(db_engine) as session, session.begin():
        session.add(Entity(name="Unrelated company", entity_type="other", aliases=["Untouched"]))

    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "preserved_partial"

    with Session(db_engine) as session:
        unrelated = session.query(Entity).filter(Entity.name == "Unrelated company").one()
        assert unrelated.aliases == ["Untouched"]
        assert session.query(Entity).filter(Entity.name == "OpenAI").count() == 0
        assert session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).count() == 0


def test_incomplete_hero_sentinel_is_preserved(db_engine):
    with Session(db_engine) as session, session.begin():
        session.add(Scenario(name=HERO_SCENARIO_NAME, description="incomplete", shock_json={}))

    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "preserved_partial"

    with Session(db_engine) as session:
        assert session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).count() == 1
        assert session.query(Entity).count() == 0


def test_scenario_and_six_entities_without_the_rest_is_preserved(db_engine):
    with Session(db_engine) as session, session.begin():
        session.add_all(
            Entity(name=name, entity_type=entity_type, aliases=[])
            for name, entity_type in ENTITY_TYPES.items()
        )
        session.add(
            Scenario(
                name=HERO_SCENARIO_NAME,
                description=SCENARIO_DESCRIPTION,
                shock_json=SCENARIO_SHOCK,
            )
        )

    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "preserved_partial"

    with Session(db_engine) as session:
        assert session.query(Entity).count() == 6
        assert session.query(Scenario).count() == 1
        assert session.query(Document).count() == 0
        assert session.query(Passage).count() == 0
        assert session.query(Edge).count() == 0


@pytest.mark.parametrize("missing_component", ["entity", "scenario", "document", "passage", "edge"])
def test_seed_with_a_missing_or_changed_component_is_preserved(db_engine, missing_component):
    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "seeded"

    with Session(db_engine) as session, session.begin():
        if missing_component == "entity":
            session.query(Entity).filter(Entity.name == "ASML").one().entity_type = "changed"
        elif missing_component == "scenario":
            session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).one().shock_json = {}
        elif missing_component == "document":
            session.delete(session.query(Document).filter(Document.title == "CoreWeave S-1/A").one())
        elif missing_component == "passage":
            session.delete(session.query(Passage).filter(Passage.text == CW_65_PASSAGE).one())
        else:
            session.delete(
                session.query(Edge)
                .filter(Edge.relationship_type == "equity_method")
                .one()
            )

    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "preserved_partial"


def test_seed_failure_rolls_back_all_graph_data(db_engine, monkeypatch):
    real_insert = hero_seed._insert_hero_graph

    def insert_then_fail(session):
        real_insert(session)
        raise RuntimeError("seed failed")

    monkeypatch.setattr(hero_seed, "_insert_hero_graph", insert_then_fail)

    with Session(db_engine) as session:
        with pytest.raises(RuntimeError, match="seed failed"):
            with session.begin():
                seed_hero_if_empty(session)

        for model in (Document, Passage, Entity, Edge, Scenario):
            assert session.query(model).count() == 0


def test_lifespan_initializes_database_once(monkeypatch):
    outcomes = []
    monkeypatch.setattr(main, "initialize_database", lambda: outcomes.append("seeded") or "seeded")

    with TestClient(main.app):
        pass

    assert outcomes == ["seeded"]
