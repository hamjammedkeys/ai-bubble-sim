# FragilityGraph

Evidence-backed AI infrastructure exposure mapping and scenario simulation.

## What it does

FragilityGraph helps users investigate how a shock to one company can propagate
through the AI infrastructure ecosystem. It combines a reviewable relationship
graph with scenario results, so claims can be traced back to their supporting
evidence instead of presented as unsupported forecasts.

## Key capabilities

- Ingest filings and turn supported relationships into graph candidates.
- Review evidence, entities, and relationships before using them in the graph.
- Model a shock and inspect how its effects propagate across connected companies.
- Use the chat copilot to ask about the graph, ingest a filing URL, or create a
  scenario.

## Architecture

The application is split into two local services:

- **Frontend:** a Next.js application in `revamp/frontend`, served at
  http://localhost:3000.
- **Backend:** a FastAPI application in `revamp/backend`, served at
  http://localhost:8000 and documented by Swagger at
  http://localhost:8000/docs.

The frontend calls the backend through `NEXT_PUBLIC_API_BASE`. The backend
stores local data in SQLite by default and can use either a deterministic
offline LLM fallback or OpenAI for extraction and the chat copilot.

## Prerequisites

- Python 3.11 or later
- Node.js 20 or later
- npm
- [`uv`](https://docs.astral.sh/uv/) (recommended for the backend; a standard
  `venv`/`pip` fallback is included below)

## Quick start

Open two terminals at the repository root.

### 1. Start the backend

Recommended (`uv`) setup:

```bash
cd revamp/backend
cp .env.example .env
```

For a reliable first run without credentials, open `.env` in any text editor
and change `LLM_PROVIDER=openai` to `LLM_PROVIDER=fallback`. Then continue:

```bash
uv sync --dev
uv run uvicorn app.main:app --reload
```

The API health check is available at http://localhost:8000/health, and the
interactive API documentation is at http://localhost:8000/docs.

If `uv` is unavailable, use this fallback:

```bash
cd revamp/backend
python3 --version
python3 -m venv .venv
source .venv/bin/activate
pip install \
  "fastapi>=0.115" "uvicorn>=0.32" "sqlalchemy>=2.0" \
  "pydantic>=2.9" "pydantic-settings>=2.6" "pymupdf>=1.24" \
  "rapidfuzz>=3.10" "openai>=1.54" "pytest>=8.3" "httpx>=0.27"
uvicorn app.main:app --reload
```

The reported `python3` version must be 3.11 or later.

### 2. Start the frontend

In a second terminal from the repository root:

```bash
cd revamp/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000. The example frontend configuration points to
http://localhost:8000; change `NEXT_PUBLIC_API_BASE` in `.env.local` only when
the backend runs elsewhere.

## LLM configuration

Copy `revamp/backend/.env.example` to `revamp/backend/.env` before starting
the backend. Choose one of these settings in `.env`:

- **Offline mode:** set `LLM_PROVIDER=fallback`. This deterministic mode needs
  no OpenAI credentials and is suitable for local exploration.
- **OpenAI mode:** set `LLM_PROVIDER=openai`, then provide `OPENAI_API_KEY` and
  an `OPENAI_MODEL` that supports structured outputs. This enables OpenAI-backed
  extraction and chat responses.

Do not commit `.env` or `.env.local`; they can contain local credentials and
machine-specific configuration.

## Deployment

Use the following dashboard sequence to deploy the demo with Neon, Render, and
Vercel. Keep connection strings, API keys, and deployment-specific origins in
the provider dashboards; do not add them to the repository.

1. In Neon, create a project and copy its pooled PostgreSQL connection string.
2. In Render, create a Blueprint from this repository's `render.yaml`. Confirm
   it creates the `fragilitygraph-api` web service from the `main` branch, then
   enter the Neon connection string as `DATABASE_URL`. The Blueprint defaults
   to `LLM_PROVIDER=fallback`; if you change it to `openai`, also enter
   `OPENAI_API_KEY` in the Render dashboard.
3. Wait for the Render service's `/health` endpoint to return successfully.
   Then request `/entities` and `/scenarios` and confirm the hero entities and
   hero scenario are present.
4. In Vercel, import this repository as a new project and set its Root Directory
   to `revamp/frontend`. Keep the detected framework set to Next.js.
5. In the Vercel project settings, set `NEXT_PUBLIC_API_BASE` to the public
   Render service origin without a trailing slash, then deploy the frontend.
6. Copy the final Vercel origin. In the Render service settings, set
   `FRONTEND_ORIGIN` to that origin without a trailing slash and redeploy the
   Render service.
7. Open the Vercel app, run the hero scenario, and reload the page. Confirm the
   graph remains available after the reload, demonstrating that the data is
   persisted in Neon.

Neon and Render free computes can wake from idle, so the first request after an
idle period can be slower. For a deployment smoke check, verify `/health`, the
hero entities and scenario API responses, a browser scenario run from the
Vercel origin, and graph persistence after a page reload.

## Verification

Run the backend tests from the repository root using the command that matches
your backend setup.

With `uv`:

```bash
cd revamp/backend
uv run pytest
```

Or with the fallback virtual environment:

```bash
cd revamp/backend
source .venv/bin/activate
pytest
```

With the frontend dependencies installed, run its checks from the repository
root:

```bash
cd revamp/frontend
npm test
npm run lint
npm run build
```

For a quick running-service check, visit http://localhost:8000/health and
http://localhost:3000 in a browser.

## Troubleshooting

- **A port is already in use:** stop the process using port 8000 or 3000, or
  start the affected service on another port and update
  `NEXT_PUBLIC_API_BASE` when the backend address changes.
- **The frontend cannot reach the API:** confirm the backend is running at
  http://localhost:8000/health and that `.env.local` uses the same backend URL.
  Restart `npm run dev` after changing `.env.local`.
- **OpenAI requests fail:** use `LLM_PROVIDER=fallback` for offline mode, or
  confirm `OPENAI_API_KEY` and `OPENAI_MODEL` are set in
  `revamp/backend/.env` for OpenAI mode.
