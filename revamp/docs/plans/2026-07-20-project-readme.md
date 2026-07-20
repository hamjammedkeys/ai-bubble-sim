# Project README Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create an English root README that explains FragilityGraph and provides verified local setup, run, test, and troubleshooting instructions.

**Architecture:** The repository root `README.md` is the single onboarding entrypoint. It links configuration to the existing backend and frontend example environment files and derives all commands from the current Python and npm manifests.

**Tech Stack:** Markdown, Python 3.11+, FastAPI/Uvicorn, Node.js 20+, Next.js 16, npm, optional `uv`.

## Global Constraints

- Do not include real API keys or other secrets.
- Keep the guide useful to both hackathon judges and first-time developers.
- Use `uv` as the recommended backend setup and standard `venv`/`pip` as the fallback.
- Use npm for frontend commands.
- Do not modify application behavior or the generated `revamp/frontend/README.md`.

---

### Task 1: Root project README

**Files:**
- Create: `README.md`

**Interfaces:**
- Consumes: `revamp/backend/pyproject.toml`, `revamp/backend/.env.example`, `revamp/backend/app/main.py`, `revamp/frontend/package.json`, and `revamp/frontend/.env.local.example`.
- Produces: An English onboarding document with copy-paste commands executed from the repository root.

- [ ] **Step 1: Confirm documented project interfaces**

Run:

```bash
test -f revamp/backend/pyproject.toml
test -f revamp/backend/.env.example
test -f revamp/frontend/package.json
test -f revamp/frontend/.env.local.example
rg '"(dev|build|lint|test)"' revamp/frontend/package.json
rg 'app = FastAPI' revamp/backend/app/main.py
```

Expected: every `test` exits 0; npm scripts and the FastAPI application are found.

- [ ] **Step 2: Create the README**

Create `README.md` with these concrete sections:

```markdown
# FragilityGraph

Evidence-backed AI infrastructure exposure mapping and scenario simulation.

## What it does
## Key capabilities
## Architecture
## Prerequisites
## Quick start
### 1. Start the backend
### 2. Start the frontend
## LLM configuration
## Verification
## Troubleshooting
```

The backend quick start must recommend:

```bash
cd revamp/backend
cp .env.example .env
uv sync --dev
uv run uvicorn app.main:app --reload
```

It must also show this fallback:

```bash
cd revamp/backend
python3.11 -m venv .venv
source .venv/bin/activate
pip install \
  "fastapi>=0.115" "uvicorn>=0.32" "sqlalchemy>=2.0" \
  "pydantic>=2.9" "pydantic-settings>=2.6" "pymupdf>=1.24" \
  "rapidfuzz>=3.10" "openai>=1.54" "pytest>=8.3" "httpx>=0.27"
uvicorn app.main:app --reload
```

The explicit dependency list is required because the backend does not currently
declare Python build-system metadata, so `pip install -e .` is unsupported.

The frontend quick start must show:

```bash
cd revamp/frontend
cp .env.local.example .env.local
npm install
npm run dev
```

- [ ] **Step 3: Verify paths, commands, and secret safety**

Run:

```bash
rg -n 'localhost:3000|localhost:8000|localhost:8000/docs|LLM_PROVIDER=fallback' README.md
rg -n 'uv sync --dev|uv run uvicorn app.main:app --reload|npm run dev|npm test|npm run lint|npm run build' README.md
test "$(rg -c 'sk-your-key-here' README.md)" -eq 0
git diff --check -- README.md
```

Expected: required URLs and commands are present, the example secret is absent, and the Markdown diff has no whitespace errors.

- [ ] **Step 4: Commit only the README**

```bash
git add README.md
git diff --cached --check
git commit -m "docs: add project setup guide"
```

Expected: the commit contains only `README.md`; cleanup deletions and existing `revamp` changes remain unstaged.
