# Vercel, Render, and Neon Deployment Design

## Goal

Deploy FragilityGraph as a low-cost public hackathon demo with:

- the Next.js frontend on Vercel;
- the FastAPI backend on Render;
- persistent PostgreSQL data on Neon;
- the hero graph available automatically on the first successful backend start.

## Deployment Topology

```text
Browser
  -> Vercel / Next.js
  -> Render / FastAPI
  -> Neon / PostgreSQL
```

The frontend receives the public Render URL through `NEXT_PUBLIC_API_BASE` at
build time. The backend receives the Neon connection string and the public
Vercel origin through runtime environment variables.

## Frontend Deployment

Vercel deploys the repository with `revamp/frontend` as the project root. The
existing npm scripts remain the source of truth:

- install: `npm install`;
- build: `npm run build`;
- production output: Next.js default output;
- public backend address: `NEXT_PUBLIC_API_BASE=https://<service>.onrender.com`.

The repository will document the Vercel Dashboard settings. It will not commit
a generated project ID, deployment URL, or environment-specific `.vercel`
metadata.

## Backend Deployment

Render deploys a Python web service from `revamp/backend`. Infrastructure
settings are captured in a root `render.yaml` so the service is reproducible:

- build command: `uv sync --frozen`;
- start command: `uv run uvicorn app.main:app --host 0.0.0.0 --port $PORT`;
- health check: `/health`;
- auto-deploy branch: `main`;
- secrets are declared with `sync: false`, never committed.

The backend remains independently runnable with SQLite for local development.

## Neon Database Connection

Production uses a Neon pooled PostgreSQL connection string supplied as
`DATABASE_URL`. The backend adds Psycopg 3 as the PostgreSQL driver.

The database adapter will:

- leave SQLite URLs unchanged;
- normalize `postgres://` and bare `postgresql://` URLs to SQLAlchemy's
  `postgresql+psycopg://` driver form;
- retain query parameters supplied by Neon, including SSL settings;
- enable `pool_pre_ping=True` so stale pooled connections are detected before
  use.

The application will not log the connection string.

## Idempotent Hero Seed

The reusable seed path must never call `drop_all()`.

At application startup:

1. Create missing tables with `Base.metadata.create_all()`.
2. Open one database transaction.
3. Check for the stable hero sentinel scenario and the required hero entities.
4. If the complete hero seed already exists, do nothing.
5. If the database is empty, insert the hero entities, approved edges, evidence,
   and scenario in one transaction.
6. If some hero data exists but the sentinel is incomplete, do not overwrite or
   duplicate records; log a warning and leave the database unchanged.

This policy protects graph edits made during the demo. A restart is safe and
does not duplicate or reset data.

The existing destructive development reset, if retained, stays in an explicit
CLI-only function with a name that includes `reset`. Production startup cannot
reach it.

## CORS and Configuration

The settings model gains `frontend_origin`, defaulting locally to
`http://localhost:3000`. FastAPI allows exactly:

- `http://localhost:3000` for local development;
- the normalized `FRONTEND_ORIGIN` value when it differs from localhost.

Wildcard origins are not allowed. Trailing slashes are removed so browser
Origin headers compare correctly.

Render runtime variables:

- `DATABASE_URL` — Neon pooled connection string;
- `FRONTEND_ORIGIN` — production Vercel origin;
- `LLM_PROVIDER` — `openai` or `fallback`;
- `OPENAI_API_KEY` — required only for OpenAI mode;
- `OPENAI_MODEL` — structured-output-capable model.

Vercel build variable:

- `NEXT_PUBLIC_API_BASE` — public Render service URL without a trailing slash.

## Failure Behavior

- Database connection failure prevents backend startup and appears in Render
  logs without exposing credentials.
- Seed insertion failure rolls back the whole seed transaction and prevents a
  partially initialized hero graph.
- An incomplete existing hero graph is preserved and produces a warning rather
  than a destructive repair.
- The frontend continues to show its existing API error state when Render is
  sleeping or unavailable.

## Verification

Automated tests will cover:

- SQLite URL behavior remains unchanged;
- Neon/PostgreSQL URL normalization and query preservation;
- stale-connection checking is enabled;
- empty database receives one complete hero seed;
- a second startup does not duplicate records;
- non-empty or partially seeded databases are not overwritten;
- CORS includes localhost and the configured Vercel origin without a wildcard;
- `render.yaml` contains the correct root, build, start, health, and secret
  declarations;
- existing backend tests and frontend test/lint/build gates remain green.

Deployment smoke checks will verify `/health`, entity/scenario presence, browser
CORS access from Vercel, and a full scenario run against Neon.

## Security and Operational Boundaries

- No Neon URL, OpenAI key, Vercel project metadata, or Render secret value is
  committed.
- The demo uses one backend instance and one Neon database branch.
- Database migrations, authentication, custom domains, background workers, and
  production-grade observability are outside this hackathon deployment scope.

## Primary References

- Render monorepo support: https://render.com/docs/monorepo-support
- Render FastAPI deployment: https://render.com/docs/deploy-fastapi
- Render environment secrets: https://render.com/docs/configure-environment-variables
- Vercel monorepos: https://vercel.com/docs/monorepos
- Vercel environment variables: https://vercel.com/docs/environment-variables
- Neon scale to zero: https://neon.com/docs/introduction/scale-to-zero
