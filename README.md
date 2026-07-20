# FragilityGraph

Evidence-backed AI infrastructure exposure mapping and scenario simulation.

## Hackathon category

**Work and productivity**

## Project description

I built FragilityGraph for analysts and financial or infrastructure researchers
to make a specific research task less brittle: finding a material relationship
buried deep in a long SEC filing, checking the source, and understanding what
else may be exposed if that company is stressed. The app reads the full filing
in bounded chunks, turns supported claims into reviewable graph candidates, and
runs evidence-backed propagation scenarios without filling missing values with
invented numbers.

## How it works

1. Ingest a public filing URL.
2. Extract the full filing in bounded chunks.
3. Review cited relationship candidates.
4. Run a company shock scenario on approved evidence.
5. Inspect each result and its supporting evidence or declared assumptions in
   the evidence desk.

## Key capabilities

- Extract full filings in bounded, overlapping chunks rather than applying a
  whole-document character cutoff.
- Review cited relationship candidates before they enter the trusted graph.
- Explore grouped relationships in the graph without losing their individual
  evidence records.
- Run scenario layers and watch their propagation animate across the graph.
- Create scenarios through the chat copilot as well as the scenario interface.
- Use a responsive evidence desk to inspect relationships, results, and sources.
- Start with persistent, verified hero data in a fresh database.
- Run locally with SQLite or use a hosted PostgreSQL database.

## Sample data

A fresh, empty database is seeded automatically with the verified hero graph:
filings and passages, approved relationships, and a scenario modeling a shock to OpenAI.
No sample-data download is required. Existing non-empty databases are preserved,
so the seed never overwrites work already in progress. To recreate the sample
safely alongside a populated database, set `DATABASE_URL` to a new SQLite path
such as `sqlite:///./fragilitygraph-demo.db`; startup will seed that new empty
database while leaving the original database untouched.

## How GPT-5.6 and Codex accelerated the build

GPT-5.6 and Codex were iterative engineering collaborators, not autonomous
authors of the product. They accelerated repository exploration and helped turn
the earlier 40,000-character ingestion cutoff into bounded full-document
chunking. They supported iterative UX work on the evidence desk, grouped
relationships, scenario cards, and propagation animation; regression tests and
browser-driven diagnosis of hover flicker and disappearing scenario edges; and
deployment hardening for Neon, Render, and Vercel. They also made it practical
to repeat lint, unit-test, API-test, and production-build verification loops
throughout the build.

## Key decisions I kept human

I set the evidence-first product boundary and refused to invent missing
financial values. I chose the square financial-terminal visual direction and
the review-before-trust workflow. I also made the category and scope decisions,
then accepted generated changes only after reading them and testing the final
behavior.

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

## Limitations

- Extraction quality depends on source text and the selected LLM provider.
- Candidate relationships require human review before entering the trusted graph.
- Scenario outputs propagate declared evidence and assumptions; they are not investment advice or price forecasts.
- The fallback provider is deterministic for demos but is not a substitute for model-backed extraction.

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
