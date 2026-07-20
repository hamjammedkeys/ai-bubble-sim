from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import db


def test_db_layer_exposes_base_engine_session():
    from app.db import Base, SessionLocal, engine

    assert Base is not None
    assert engine is not None
    assert SessionLocal is not None


def test_init_db_runs_and_session_opens(tmp_path, monkeypatch):
    # No models registered in this task: init_db runs against empty metadata
    # and must not raise. Table creation is asserted in Task 3.
    engine = create_engine(f"sqlite:///{tmp_path/'t.db'}")
    monkeypatch.setattr(db, "engine", engine)
    db.init_db()
    session = Session(engine)
    assert isinstance(session, Session)
    session.close()
