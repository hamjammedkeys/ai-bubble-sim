# Sub-project 1: Foundation + Data Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A runnable FastAPI backend with the full FragilityGraph persistence schema (six SQLite-backed SQLAlchemy tables) and Pydantic API schemas, so later sub-projects have typed tables and models to build against.

**Architecture:** Single `revamp/backend/` Python package managed by `uv`. FastAPI app exposes a health endpoint and wires a SQLAlchemy 2.0 layer over SQLite. ORM models mirror plan §4 with SQLite-compatible types (String UUIDs, JSON for JSONB/arrays). Pydantic v2 response schemas read from ORM instances via `from_attributes`. No extraction, verification, calc, or frontend logic — those are later sub-projects.

**Tech Stack:** Python 3.14 (via `uv`), FastAPI, Uvicorn, SQLAlchemy 2.0, Pydantic v2, pydantic-settings, SQLite. Test deps: pytest, httpx (for FastAPI TestClient). Runtime deps installed now but unused until later: pymupdf, rapidfuzz, openai.

## Global Constraints

- Project root for all work is `revamp/`. Backend lives in `revamp/backend/`. Never touch files outside `revamp/`.
- Database is **SQLite** via SQLAlchemy; same ORM schema must swap to Postgres by connection string alone — so no SQLite-only column types.
- Schema is **plan §4 verbatim**: tables `documents, passages, entities, edges, scenarios, scenario_runs` with the exact columns listed there.
- UUID primary keys as `String` defaulting to `str(uuid4())`; `JSONB`→`JSON`; `TEXT[]`→`JSON`; `TIMESTAMPTZ`→`DateTime` default `datetime.utcnow`; `NUMERIC`→`Float`.
- `edges.status` defaults to `'candidate'`.
- Run all commands from `revamp/backend/`. Test command: `uv run pytest`.
- TDD: every code change is preceded by a failing test. Commit after each green task.

---

### Task 1: Backend scaffold + config + health endpoint

**Files:**
- Create: `revamp/backend/pyproject.toml`
- Create: `revamp/backend/app/__init__.py`
- Create: `revamp/backend/app/config.py`
- Create: `revamp/backend/app/main.py`
- Create: `revamp/backend/tests/__init__.py`
- Create: `revamp/backend/tests/test_health.py`

**Interfaces:**
- Consumes: nothing (first task).
- Produces:
  - `app.config.Settings` (pydantic-settings) with fields `database_url: str = "sqlite:///./fragilitygraph.db"`, `llm_provider: str = "openai"`, `openai_api_key: str | None = None`.
  - `app.config.settings` — a module-level `Settings()` instance.
  - `app.main.app` — the FastAPI application. `GET /health` → `{"status": "ok"}`.

- [ ] **Step 1: Create the package structure and pyproject**

Create `revamp/backend/pyproject.toml`:

```toml
[project]
name = "fragilitygraph-backend"
version = "0.1.0"
description = "FragilityGraph backend — evidence-backed AI-bubble simulator"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115",
    "uvicorn>=0.32",
    "sqlalchemy>=2.0",
    "pydantic>=2.9",
    "pydantic-settings>=2.6",
    "pymupdf>=1.24",
    "rapidfuzz>=3.10",
    "openai>=1.54",
]

[dependency-groups]
dev = [
    "pytest>=8.3",
    "httpx>=0.27",
]

[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

Create empty `revamp/backend/app/__init__.py` and `revamp/backend/tests/__init__.py` (empty files).

- [ ] **Step 2: Write the failing test**

Create `revamp/backend/tests/test_health.py`:

```python
from fastapi.testclient import TestClient

from app.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 3: Run test to verify it fails**

Run (from `revamp/backend/`):
```bash
uv run pytest tests/test_health.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.main'` (config/main not created yet). Running `uv run` also bootstraps the venv and installs deps on first invocation.

- [ ] **Step 4: Write the config module**

Create `revamp/backend/app/config.py`:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./fragilitygraph.db"
    llm_provider: str = "openai"
    openai_api_key: str | None = None


settings = Settings()
```

- [ ] **Step 5: Write the FastAPI app**

Create `revamp/backend/app/main.py`:

```python
from fastapi import FastAPI

app = FastAPI(title="FragilityGraph API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run test to verify it passes**

Run:
```bash
uv run pytest tests/test_health.py -v
```
Expected: PASS.

- [ ] **Step 7: Create .gitignore and commit**

Create `revamp/backend/.gitignore`:

```
.venv/
__pycache__/
*.db
.env
.pytest_cache/
```

Commit:
```bash
git add revamp/backend/pyproject.toml revamp/backend/uv.lock revamp/backend/.gitignore revamp/backend/app/ revamp/backend/tests/
git commit -m "feat(revamp/backend): scaffold FastAPI app with health endpoint"
```

---

### Task 2: SQLAlchemy DB layer (engine, session, Base, init_db)

**Files:**
- Create: `revamp/backend/app/db.py`
- Create: `revamp/backend/tests/test_db.py`

**Interfaces:**
- Consumes: `app.config.settings.database_url`.
- Produces:
  - `app.db.Base` — SQLAlchemy `DeclarativeBase` subclass; all models inherit from it.
  - `app.db.engine` — engine built from `settings.database_url` (with `check_same_thread=False` for SQLite).
  - `app.db.SessionLocal` — a `sessionmaker` bound to `engine`.
  - `app.db.init_db() -> None` — calls `Base.metadata.create_all(engine)`. In this task no models are registered yet, so it runs against empty metadata; Task 3 extends it to import models first.
  - `app.db.get_session()` — FastAPI dependency yielding a session, closing it after.

Note on the `engine` global: `init_db` must reference the **module-level** `engine` name at call time (not capture it into a default argument), because later tests monkeypatch `db.engine` to point at a temp database.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_db.py`:

```python
from sqlalchemy.orm import Session

from app import db


def test_db_layer_exposes_base_engine_session():
    from app.db import Base, SessionLocal, engine

    assert Base is not None
    assert engine is not None
    assert SessionLocal is not None


def test_init_db_runs_and_session_opens():
    # No models registered in this task: init_db runs against empty metadata
    # and must not raise. Table creation is asserted in Task 3.
    db.init_db()
    session = db.SessionLocal()
    assert isinstance(session, Session)
    session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run pytest tests/test_db.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.db'`.

- [ ] **Step 3: Write the DB layer**

Create `revamp/backend/app/db.py`:

```python
from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


def _connect_args(url: str) -> dict:
    return {"check_same_thread": False} if url.startswith("sqlite") else {}


engine = create_engine(settings.database_url, connect_args=_connect_args(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
uv run pytest tests/test_db.py -v
```
Expected: PASS — both tests green (empty-metadata `init_db` runs, session opens).

- [ ] **Step 5: Commit**

```bash
git add revamp/backend/app/db.py revamp/backend/tests/test_db.py
git commit -m "feat(revamp/backend): add SQLAlchemy engine, session, and init_db"
```

---

### Task 3: ORM models for the six §4 tables

**Files:**
- Create: `revamp/backend/app/models.py`
- Modify: `revamp/backend/app/db.py` (make `init_db` import models before `create_all`)
- Create: `revamp/backend/tests/test_models.py`

**Interfaces:**
- Consumes: `app.db.Base`, `app.db.init_db`, `app.db.SessionLocal`.
- Produces ORM classes (SQLAlchemy 2.0 `Mapped`/`mapped_column`), one per §4 table:
  - `Document(id, title, filing_type, company, url, filed_date, period, raw_text, ingested_at)`
  - `Passage(id, document_id, text, char_start, char_end, page_number)`
  - `Entity(id, name, entity_type, aliases)` — `name` unique, `aliases` a JSON list.
  - `Edge(id, source_entity_id, target_entity_id, relationship_type, metric, value, unit, period, evidence_class, permitted_operation, unsupported_operation, passage_id, document_id, status, verification, reviewed_by, reviewed_at, created_at)` — `status` default `"candidate"`, `verification` JSON.
  - `Scenario(id, name, description, shock_json)` — `shock_json` JSON.
  - `ScenarioRun(id, scenario_id, results, run_at)` — `results` JSON.
  - Shared `_uuid_pk()` helper returning a `str(uuid4())` default string PK column value.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_models.py`:

```python
from datetime import date

from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

from app import db
from app.models import Document, Edge, Entity, Passage


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
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run pytest tests/test_models.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.models'`.

- [ ] **Step 3a: Make `init_db` register models before creating tables**

Modify `revamp/backend/app/db.py` — replace the `init_db` body so it imports the models module (registering the ORM classes on `Base.metadata`) before `create_all`, so a caller that hasn't already imported models still gets all six tables:

```python
def init_db() -> None:
    from app import models  # noqa: F401  # register ORM models on Base.metadata

    Base.metadata.create_all(engine)
```

- [ ] **Step 3b: Write the models**

Create `revamp/backend/app/models.py`:

```python
from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import JSON

from app.db import Base


def _uuid() -> str:
    return str(uuid4())


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    filing_type: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text)
    filed_date: Mapped[date | None] = mapped_column(Date)
    period: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Passage(Base):
    __tablename__ = "passages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    text: Mapped[str] = mapped_column(Text, nullable=False)
    char_start: Mapped[int | None] = mapped_column(Integer)
    char_end: Mapped[int | None] = mapped_column(Integer)
    page_number: Mapped[int | None] = mapped_column(Integer)


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    entity_type: Mapped[str | None] = mapped_column(Text)
    aliases: Mapped[list | None] = mapped_column(JSON, default=list)


class Edge(Base):
    __tablename__ = "edges"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"))
    target_entity_id: Mapped[str | None] = mapped_column(ForeignKey("entities.id"))
    relationship_type: Mapped[str] = mapped_column(Text, nullable=False)
    metric: Mapped[str | None] = mapped_column(Text)
    value: Mapped[float | None] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(Text)
    period: Mapped[str | None] = mapped_column(Text)
    evidence_class: Mapped[str] = mapped_column(Text, nullable=False)
    permitted_operation: Mapped[str | None] = mapped_column(Text)
    unsupported_operation: Mapped[str | None] = mapped_column(Text)
    passage_id: Mapped[str | None] = mapped_column(ForeignKey("passages.id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"))
    status: Mapped[str] = mapped_column(Text, nullable=False, default="candidate")
    verification: Mapped[dict | None] = mapped_column(JSON)
    reviewed_by: Mapped[str | None] = mapped_column(Text)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Scenario(Base):
    __tablename__ = "scenarios"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    name: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    shock_json: Mapped[dict | None] = mapped_column(JSON)


class ScenarioRun(Base):
    __tablename__ = "scenario_runs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario_id: Mapped[str | None] = mapped_column(ForeignKey("scenarios.id"))
    results: Mapped[dict | None] = mapped_column(JSON)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest tests/test_models.py tests/test_db.py -v
```
Expected: PASS — both `test_models.py` cases and the previously-red `test_db.py::test_init_db_creates_all_tables` now pass.

- [ ] **Step 5: Commit**

```bash
git add revamp/backend/app/models.py revamp/backend/tests/test_models.py
git commit -m "feat(revamp/backend): add ORM models for the six schema tables"
```

---

### Task 4: Pydantic API response schemas

**Files:**
- Create: `revamp/backend/app/schemas.py`
- Create: `revamp/backend/tests/test_schemas.py`

**Interfaces:**
- Consumes: `app.models.Entity`, `app.models.Edge` instances.
- Produces Pydantic v2 models with `model_config = ConfigDict(from_attributes=True)`:
  - `EntityOut(id, name, entity_type, aliases)`
  - `EdgeOut(id, source_entity_id, target_entity_id, relationship_type, metric, value, unit, period, evidence_class, permitted_operation, unsupported_operation, passage_id, document_id, status, verification, created_at)`
  - These are the serialization contract later API endpoints (sub-project 3) will return.

- [ ] **Step 1: Write the failing test**

Create `revamp/backend/tests/test_schemas.py`:

```python
from app.models import Edge, Entity
from app.schemas import EdgeOut, EntityOut


def test_entity_out_from_orm():
    e = Entity(id="ent1", name="OpenAI", entity_type="model_company", aliases=["OAI"])
    out = EntityOut.model_validate(e)
    assert out.id == "ent1"
    assert out.aliases == ["OAI"]


def test_edge_out_from_orm_carries_status_and_verification():
    edge = Edge(
        id="edge1",
        source_entity_id="a",
        target_entity_id="b",
        relationship_type="purchase_obligation",
        evidence_class="reported",
        value=11.9,
        status="approved",
        verification={"overall": "pass"},
    )
    out = EdgeOut.model_validate(edge)
    assert out.id == "edge1"
    assert out.value == 11.9
    assert out.status == "approved"
    assert out.verification == {"overall": "pass"}
```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
uv run pytest tests/test_schemas.py -v
```
Expected: FAIL — `ModuleNotFoundError: No module named 'app.schemas'`.

- [ ] **Step 3: Write the schemas**

Create `revamp/backend/app/schemas.py`:

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EntityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    entity_type: str | None = None
    aliases: list[str] | None = None


class EdgeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_entity_id: str | None = None
    target_entity_id: str | None = None
    relationship_type: str
    metric: str | None = None
    value: float | None = None
    unit: str | None = None
    period: str | None = None
    evidence_class: str
    permitted_operation: str | None = None
    unsupported_operation: str | None = None
    passage_id: str | None = None
    document_id: str | None = None
    status: str
    verification: dict | None = None
    created_at: datetime | None = None
```

- [ ] **Step 4: Run tests to verify they pass**

Run:
```bash
uv run pytest -v
```
Expected: PASS — all tests across `test_health`, `test_db`, `test_models`, `test_schemas`.

- [ ] **Step 5: Commit**

```bash
git add revamp/backend/app/schemas.py revamp/backend/tests/test_schemas.py
git commit -m "feat(revamp/backend): add Pydantic response schemas for entities and edges"
```

---

## Acceptance (whole sub-project)

- `cd revamp/backend && uv run uvicorn app.main:app` boots; `GET /health` → `{"status":"ok"}`.
- `uv run python -c "from app.db import init_db; init_db()"` creates `fragilitygraph.db` with all six tables.
- `uv run pytest` — all tests green (health, db, models, schemas).
- No extraction / verification / calc / frontend code present (deferred to sub-projects 2–6).
