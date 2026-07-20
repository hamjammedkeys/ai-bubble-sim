# FragilityGraph — Execution Design

Design for building the FragilityGraph simulator described in
[`revamp/fragilitygraph-implementation-plan-v2.md`](../../fragilitygraph-implementation-plan-v2.md).
That plan is the detailed product/spec reference; this document records the **execution
decisions and decomposition** for building it in full. The project root is `revamp/`.

## Decisions (this session)

- **Scope:** full build of plan v2 (must-have + should-have), decomposed into 6
  sub-projects built sequentially. Each sub-project gets its own spec → plan → implement →
  checkpoint cycle.
- **Database:** **SQLite** via SQLAlchemy, not Postgres/docker-compose. Same ORM schema;
  swapping to Postgres later is a connection-string change. Chosen for zero-infra "runs on a
  laptop immediately" at the 8–12 node / 15–25 edge scale.
- **LLM:** wired **live** to **OpenAI** (`response_format: json_schema, strict: true`)
  behind the provider-agnostic `extract_candidates` adapter (plan §6). API key supplied via
  env var. The adapter keeps an Anthropic branch too, but OpenAI is the default/live path.
  Deterministic/pre-cached fallback still built (plan §16).
- **Layout:** all backend code under `revamp/backend/`, frontend under `revamp/frontend/`.

## Sub-project decomposition & build order

| # | Sub-project | Delivers | Depends on |
|---|---|---|---|
| 1 | Foundation + data layer | Repo scaffold, SQLAlchemy models for §4 schema (SQLite-typed), Pydantic models, FastAPI app skeleton, config/settings, DB init, smoke tests | — |
| 2 | Ingestion + extraction | `extract_pdf_text` (pymupdf), provider-agnostic LLM adapter (Anthropic live), extraction Pydantic schema + prompt (§6) | 1 |
| 3 | Verification + approval | Verifier 6 checks (§7), candidate→approved/rejected/edited state machine, review + approve/reject/edit endpoints (§11) | 2 |
| 4 | Calc engine + scenarios | Structural rules keyed by `relationship_type` (§8), hero compound credit-event scenario, `run_scenario`, per-edge `visual_state`, unit tests for the two headline figures | 1, 3 |
| 5 | Frontend | Next.js + React Flow + dagre layered layout, layer sidebar, links panel, evidence inspector, legend, metric cards, scenario runner + staged animation, review queue, upload modal (§9, §10) | 4 |
| 6 | Seed data + demo | Source real filings, seed the graph, pre-cache fallback extraction, demo script + timed dry-run (§12, §13) | all |

Downstream is provider-blind and status-gated exactly as plan §2/§4 require: the calc engine
reads only `status='approved'` edges and never calls the LLM.

## Sub-project 1 — Foundation + data layer (detailed)

**Purpose:** a runnable FastAPI backend with the full persistence schema in place, so every
later sub-project has typed tables and models to write against. No business logic yet.

**Structure**
```
revamp/backend/
  pyproject.toml            # deps: fastapi, uvicorn, sqlalchemy, pydantic v2,
                            #       pydantic-settings, pymupdf, rapidfuzz, openai, pytest
  app/
    main.py                 # FastAPI app, health endpoint, router wiring
    config.py               # pydantic-settings: DB url, LLM_PROVIDER, API key
    db.py                   # SQLAlchemy engine/session (SQLite), Base, init_db()
    models.py               # ORM models: Document, Passage, Entity, Edge, Scenario, ScenarioRun
    schemas.py              # Pydantic request/response models (EntityOut, EdgeOut, ...)
  tests/
    test_models.py          # create + relationship smoke tests
    test_health.py          # app boots, /health returns ok
```

**Schema translation (§4 → SQLite-compatible SQLAlchemy)**
- `UUID PRIMARY KEY DEFAULT gen_random_uuid()` → `String` PK defaulting to `str(uuid4())`.
- `JSONB` (`verification`, `shock_json`, `results`) → SQLAlchemy `JSON`.
- `TEXT[]` (`entities.aliases`) → `JSON` (list of strings).
- `TIMESTAMPTZ DEFAULT now()` → `DateTime` with `default=datetime.utcnow`.
- `NUMERIC` (`edges.value`) → `Float`.
- Foreign keys, enums-as-TEXT, and the `status` default `'candidate'` preserved as written.
- All six tables from §4: `documents, passages, entities, edges, scenarios, scenario_runs`.

**Config**
- `DATABASE_URL` default `sqlite:///./fragilitygraph.db`.
- `LLM_PROVIDER` default `openai`; `OPENAI_API_KEY` read from env (not required until
  sub-project 2).

**Acceptance for sub-project 1**
- `uvicorn app.main:app` boots; `GET /health` → `{"status":"ok"}`.
- `init_db()` creates all six tables in SQLite.
- Tests pass: can insert an Entity, a Document+Passage, and an Edge referencing them; JSON and
  list columns round-trip.
- No LLM, no PDF, no calc logic yet — those are sub-projects 2–4.

## Non-goals (this sub-project)
Extraction, verification, calc engine, frontend, seed data — all deferred to their own
sub-projects per the table above.
