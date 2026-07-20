import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app import main
from app.models import Document, Edge, Entity, Passage, Scenario
from app.services import hero_seed
from app.services.hero_seed import HERO_SCENARIO_NAME, seed_hero_if_empty


def test_empty_database_is_seeded_once(db_engine):
    with Session(db_engine) as session, session.begin():
        assert seed_hero_if_empty(session) == "seeded"

    with Session(db_engine) as session:
        assert session.query(Entity).filter(Entity.name == "OpenAI").count() == 1
        assert session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).count() == 1
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


def test_seed_failure_rolls_back_all_graph_data(db_engine, monkeypatch):
    def insert_then_fail(session):
        session.add(Document(title="partial", raw_text="must roll back"))
        session.flush()
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
