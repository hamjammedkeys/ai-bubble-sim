import logging

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app import db


def test_normalize_database_url_preserves_sqlite_and_normalizes_postgres_urls():
    from app.db import normalize_database_url

    assert normalize_database_url("sqlite:///./demo.db") == "sqlite:///./demo.db"
    assert normalize_database_url("postgres://u:p@host/db?sslmode=require") == (
        "postgresql+psycopg://u:p@host/db?sslmode=require"
    )
    assert normalize_database_url("postgresql://u:p@host/db?sslmode=require") == (
        "postgresql+psycopg://u:p@host/db?sslmode=require"
    )
    assert normalize_database_url("postgresql+psycopg://u:p@host/db") == (
        "postgresql+psycopg://u:p@host/db"
    )


def test_build_engine_configures_sqlite_and_never_logs_credentials(monkeypatch, caplog):
    from app.db import build_engine

    calls = []

    def fake_create_engine(*args, **kwargs):
        calls.append((args, kwargs))
        return object()

    monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)
    caplog.set_level(logging.DEBUG)

    build_engine("sqlite:///./demo.db")
    build_engine("postgres://u:super-secret@host/db?sslmode=require")

    assert calls == [
        (
            ("sqlite:///./demo.db",),
            {"connect_args": {"check_same_thread": False}, "pool_pre_ping": True},
        ),
        (
            ("postgresql+psycopg://u:super-secret@host/db?sslmode=require",),
            {"connect_args": {}, "pool_pre_ping": True},
        ),
    ]
    assert "super-secret" not in caplog.text
    assert "postgres://u:super-secret@host/db?sslmode=require" not in caplog.text


def test_build_engine_configures_postgres_without_sqlite_connect_args(monkeypatch):
    from app.db import build_engine

    calls = []

    def fake_create_engine(*args, **kwargs):
        calls.append((args, kwargs))
        return object()

    monkeypatch.setattr(sqlalchemy, "create_engine", fake_create_engine)

    build_engine("postgres://u:p@host/db?sslmode=require")

    assert calls == [
        (
            ("postgresql+psycopg://u:p@host/db?sslmode=require",),
            {"connect_args": {}, "pool_pre_ping": True},
        )
    ]


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
