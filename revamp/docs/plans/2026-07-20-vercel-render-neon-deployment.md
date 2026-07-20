# Vercel, Render, and Neon Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make FragilityGraph deployable as a Vercel frontend, Render FastAPI service, and Neon PostgreSQL database with a safe hero graph on first startup.

**Architecture:** Deployment settings remain environment-driven: Vercel builds the nested Next.js app, Render runs the nested FastAPI app, and SQLAlchemy connects to either local SQLite or Neon through Psycopg 3. Startup creates tables and invokes a transaction-safe, non-destructive hero seed that is a no-op after the first complete seed.

**Tech Stack:** Next.js 16, Vercel, FastAPI, Render Blueprint, SQLAlchemy 2, Psycopg 3, Neon PostgreSQL, pytest, Vitest.

## Global Constraints

- Local SQLite development must continue to work without PostgreSQL.
- Production startup must never call `drop_all()` or overwrite existing graph data.
- Neon, OpenAI, Vercel, and Render secret values must never be committed or logged.
- CORS must allow localhost and the configured Vercel origin, never a wildcard.
- Render builds from `revamp/backend`; Vercel builds from `revamp/frontend`.
- The existing backend and frontend test suites must remain green.

---

### Task 1: Neon-compatible database engine

**Files:**
- Modify: `revamp/backend/pyproject.toml`
- Modify: `revamp/backend/app/db.py`
- Modify: `revamp/backend/tests/test_db.py`
- Modify: `revamp/backend/uv.lock`

**Interfaces:**
- Produces: `normalize_database_url(url: str) -> str` and `build_engine(url: str) -> Engine`.
- Preserves: module-level `engine`, `SessionLocal`, `init_db()`, and `get_session()` consumers.

- [ ] **Step 1: Write failing URL and engine tests**

Add tests that assert:

```python
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
```

Monkeypatch `sqlalchemy.create_engine` and assert `build_engine()` passes
`pool_pre_ping=True`, uses SQLite `check_same_thread=False` only for SQLite, and
does not include credentials in logs.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd revamp/backend && uv run pytest tests/test_db.py -q`

Expected: FAIL because the two public helpers do not exist.

- [ ] **Step 3: Add Psycopg and implement the engine seam**

Add `psycopg[binary]>=3.2` to project dependencies and refresh `uv.lock` with
`uv lock`.

Implement:

```python
def normalize_database_url(url: str) -> str:
    if url.startswith("postgres://"):
        return "postgresql+psycopg://" + url.removeprefix("postgres://")
    if url.startswith("postgresql://"):
        return "postgresql+psycopg://" + url.removeprefix("postgresql://")
    return url


def build_engine(url: str) -> Engine:
    normalized = normalize_database_url(url)
    connect_args = {"check_same_thread": False} if normalized.startswith("sqlite") else {}
    return create_engine(normalized, connect_args=connect_args, pool_pre_ping=True)
```

Construct the module-level engine through `build_engine(settings.database_url)`.

- [ ] **Step 4: Run Task 1 and full backend tests**

Run:

```bash
cd revamp/backend
uv run pytest tests/test_db.py -q
uv run pytest -q
```

Expected: focused and full backend suites pass.

- [ ] **Step 5: Commit Task 1**

```bash
git add revamp/backend/pyproject.toml revamp/backend/uv.lock \
  revamp/backend/app/db.py revamp/backend/tests/test_db.py
git commit -m "feat(revamp): support Neon PostgreSQL"
```

---

### Task 2: Non-destructive idempotent hero seed

**Files:**
- Create: `revamp/backend/app/services/hero_seed.py`
- Create: `revamp/backend/tests/test_hero_seed.py`
- Modify: `revamp/backend/seed_hero.py`
- Modify: `revamp/backend/app/main.py`

**Interfaces:**
- Produces: `SeedOutcome = Literal["seeded", "already_seeded", "preserved_partial"]`.
- Produces: `seed_hero_if_empty(session: Session) -> SeedOutcome`.
- Produces: `initialize_database() -> SeedOutcome`, called once during FastAPI lifespan.

- [ ] **Step 1: Write failing seed lifecycle tests**

Use an isolated SQLite database with all ORM tables and assert:

```python
assert seed_hero_if_empty(session) == "seeded"
assert session.query(Entity).filter(Entity.name == "OpenAI").count() == 1
assert session.query(Scenario).filter(Scenario.name == "OpenAI credit event").count() == 1

assert seed_hero_if_empty(session) == "already_seeded"
assert session.query(Entity).filter(Entity.name == "OpenAI").count() == 1
```

In a second database, insert an unrelated entity before calling the helper and
assert `"preserved_partial"`, no hero sentinel, and the unrelated row unchanged.
Patch the insertion helper to raise midway and assert the transaction rolls back
without leaving documents, passages, entities, edges, or scenarios.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd revamp/backend && uv run pytest tests/test_hero_seed.py -q`

Expected: FAIL because `app.services.hero_seed` does not exist.

- [ ] **Step 3: Extract the seed data without destructive reset**

Move the existing hero data construction from `seed_hero.py` into
`app/services/hero_seed.py` behind these functions:

```python
HERO_SCENARIO_NAME = "OpenAI credit event"


def _database_has_any_graph_data(session: Session) -> bool:
    return any(
        session.query(model).first() is not None
        for model in (Document, Passage, Entity, Edge, Scenario)
    )


def seed_hero_if_empty(session: Session) -> SeedOutcome:
    if session.query(Scenario).filter(Scenario.name == HERO_SCENARIO_NAME).first():
        return "already_seeded"
    if _database_has_any_graph_data(session):
        logger.warning("Hero seed skipped because the database already contains graph data")
        return "preserved_partial"
    _insert_hero_graph(session)
    return "seeded"
```

`_insert_hero_graph()` must insert the exact entities, filings, passages, edges,
verification payloads, and scenario currently defined in `seed_hero.py`, then
flush but not commit. The caller owns the transaction.

Implement startup initialization:

```python
def initialize_database() -> SeedOutcome:
    init_db()
    with SessionLocal.begin() as session:
        return seed_hero_if_empty(session)
```

Call `initialize_database()` in FastAPI lifespan. Keep `seed_hero.py` as an
explicit development reset command whose destructive function is named
`reset_and_seed()`; startup imports only the non-destructive service.

- [ ] **Step 4: Run seed, health, and full backend tests**

Run:

```bash
cd revamp/backend
uv run pytest tests/test_hero_seed.py tests/test_health.py -q
uv run pytest -q
```

Expected: seed lifecycle, health, and full backend suites pass.

- [ ] **Step 5: Commit Task 2**

```bash
git add revamp/backend/app/services/hero_seed.py revamp/backend/tests/test_hero_seed.py \
  revamp/backend/seed_hero.py revamp/backend/app/main.py
git commit -m "feat(revamp): seed hero graph safely on startup"
```

---

### Task 3: Environment-driven production CORS

**Files:**
- Modify: `revamp/backend/app/config.py`
- Modify: `revamp/backend/app/main.py`
- Modify: `revamp/backend/.env.example`
- Modify: `revamp/backend/tests/test_health.py`

**Interfaces:**
- Produces: `Settings.frontend_origin: str` from `FRONTEND_ORIGIN`.
- Produces: `allowed_origins(frontend_origin: str) -> list[str]`.

- [ ] **Step 1: Write failing origin tests**

Assert:

```python
assert allowed_origins("http://localhost:3000") == ["http://localhost:3000"]
assert allowed_origins("https://fragility.vercel.app/") == [
    "http://localhost:3000",
    "https://fragility.vercel.app",
]
assert "*" not in allowed_origins("https://fragility.vercel.app")
```

Issue an OPTIONS request with the production Origin and assert the matching
`access-control-allow-origin` header.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd revamp/backend && uv run pytest tests/test_health.py -q`

Expected: FAIL because the helper and setting do not exist.

- [ ] **Step 3: Implement settings and CORS normalization**

Add to Settings:

```python
frontend_origin: str = "http://localhost:3000"
```

Implement in `main.py`:

```python
LOCAL_FRONTEND_ORIGIN = "http://localhost:3000"


def allowed_origins(frontend_origin: str) -> list[str]:
    configured = frontend_origin.rstrip("/")
    if configured == LOCAL_FRONTEND_ORIGIN:
        return [LOCAL_FRONTEND_ORIGIN]
    return [LOCAL_FRONTEND_ORIGIN, configured]
```

Configure middleware with `allowed_origins(settings.frontend_origin)`. Add
`FRONTEND_ORIGIN=http://localhost:3000` to `.env.example`.

- [ ] **Step 4: Run focused and full backend tests**

Run: `cd revamp/backend && uv run pytest tests/test_health.py -q && uv run pytest -q`

Expected: all tests pass.

- [ ] **Step 5: Commit Task 3**

```bash
git add revamp/backend/app/config.py revamp/backend/app/main.py \
  revamp/backend/.env.example revamp/backend/tests/test_health.py
git commit -m "feat(revamp): configure production frontend origin"
```

---

### Task 4: Render and Vercel deployment contract

**Files:**
- Create: `render.yaml`
- Create: `revamp/frontend/vercel.json`
- Modify: `README.md`
- Modify: `revamp/backend/.env.example`
- Modify: `revamp/frontend/.env.local.example`
- Create: `revamp/backend/tests/test_deployment_config.py`

**Interfaces:**
- Produces: Render Blueprint service `fragilitygraph-api` rooted at `revamp/backend`.
- Produces: Vercel project defaults for the nested Next.js frontend.

- [ ] **Step 1: Write failing deployment contract tests**

Parse `render.yaml` with `yaml.safe_load` and assert one Python web service with:

```python
assert service["name"] == "fragilitygraph-api"
assert service["rootDir"] == "revamp/backend"
assert service["buildCommand"] == "uv sync --frozen"
assert service["startCommand"] == "uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT"
assert service["healthCheckPath"] == "/health"
```

Assert `DATABASE_URL`, `FRONTEND_ORIGIN`, and `OPENAI_API_KEY` use `sync: false`
and no secret value is present. Parse `vercel.json` and assert framework
`nextjs`. Add `pyyaml>=6.0` to the dev dependency group and refresh `uv.lock` so
the contract test has an explicit parser dependency.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd revamp/backend && uv run pytest tests/test_deployment_config.py -q`

Expected: FAIL because `render.yaml` and `vercel.json` do not exist.

- [ ] **Step 3: Add infrastructure files**

Create root `render.yaml`:

```yaml
services:
  - type: web
    name: fragilitygraph-api
    runtime: python
    plan: free
    branch: main
    rootDir: revamp/backend
    buildCommand: uv sync --frozen
    startCommand: uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    autoDeployTrigger: commit
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: FRONTEND_ORIGIN
        sync: false
      - key: LLM_PROVIDER
        value: fallback
      - key: OPENAI_API_KEY
        sync: false
      - key: OPENAI_MODEL
        value: gpt-4o-2024-08-06
```

Create `revamp/frontend/vercel.json`:

```json
{
  "$schema": "https://openapi.vercel.sh/vercel.json",
  "framework": "nextjs"
}
```

- [ ] **Step 4: Document exact dashboard sequence and smoke checks**

Update the root README with a Deployment section that tells the operator to:

1. Create a Neon project and copy its pooled connection string.
2. Create the Render service from `render.yaml` and enter secrets in the Render
   dashboard.
3. Wait for `/health` and confirm hero entities/scenario through the API.
4. Create a Vercel project rooted at `revamp/frontend`.
5. Set `NEXT_PUBLIC_API_BASE` to the Render URL and deploy.
6. Set `FRONTEND_ORIGIN` to the final Vercel origin and redeploy Render.
7. Open the Vercel app, run the hero scenario, and confirm a page reload retains
   the graph through Neon.

Document that Neon and Render free computes can wake from idle, so the first
request can be slower. Do not include real URLs or credentials.

- [ ] **Step 5: Run all gates**

```bash
cd revamp/backend
uv run pytest
cd ../frontend
npm test
npm run lint
npm run build
cd ../..
git diff --check
```

Expected: backend tests, frontend tests/lint/build, and whitespace validation
all pass.

- [ ] **Step 6: Commit Task 4**

```bash
git add render.yaml README.md revamp/frontend/vercel.json \
  revamp/backend/.env.example revamp/frontend/.env.local.example \
  revamp/backend/pyproject.toml revamp/backend/uv.lock \
  revamp/backend/tests/test_deployment_config.py
git commit -m "chore(revamp): add demo deployment configuration"
```
