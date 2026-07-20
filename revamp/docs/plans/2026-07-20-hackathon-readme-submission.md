# Hackathon README Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Revise the root README so hackathon judges can understand, run, and evaluate FragilityGraph, including the specific contribution of GPT-5.6 and Codex.

**Architecture:** This is a documentation-only change. Keep the existing root `README.md` as the single entry point, reorganize its opening around the judge's evaluation flow, and preserve verified setup, deployment, and test commands. Validate every product and AI-collaboration claim against files already present under `revamp`.

**Tech Stack:** Markdown, FastAPI, Next.js, SQLAlchemy, SQLite/PostgreSQL, OpenAI API, Codex.

## Global Constraints

- Submission category is **Work and productivity**.
- Use a direct builder voice and avoid generic marketing language.
- Describe only behavior implemented in `revamp`.
- Clearly separate AI assistance from human product and acceptance decisions.
- Preserve working local setup, deployment, verification, and troubleshooting commands.
- Do not add dependencies or change application code.

---

### Task 1: Judge-Facing README Narrative

**Files:**
- Modify: `README.md`
- Reference: `revamp/docs/specs/2026-07-20-hackathon-readme-submission-design.md`
- Reference: `revamp/backend/app/ingestion.py`
- Reference: `revamp/backend/app/services/hero_seed.py`
- Reference: `revamp/frontend/app/page.tsx`

**Interfaces:**
- Consumes: Existing backend/frontend behavior and commands.
- Produces: A self-contained repository landing page for judges and contributors.

- [ ] **Step 1: Verify feature claims against the implementation**

Run:

```bash
rg -n "chunk_document|orchestrate_document_extraction|seed_hero_if_empty|runScenario|reviewEdge|ingest_filing|create_scenario" \
  revamp/backend/app revamp/frontend/app
```

Expected: matches for chunked filing ingestion, hero data, scenario execution, evidence review, and chat actions.

- [ ] **Step 2: Rewrite the README opening for the submission**

Add these judge-facing sections before architecture:

```markdown
## Hackathon category

**Work and productivity**

## Project description

I built FragilityGraph to make a specific research task less brittle: finding a
material relationship buried deep in a long SEC filing, checking the source,
and understanding what else may be exposed if that company is stressed. The app
reads the full filing in bounded chunks, turns supported claims into reviewable
graph candidates, and runs evidence-backed propagation scenarios without filling
missing values with invented numbers.

## How it works

1. Ingest a public filing URL.
2. Extract the full filing in bounded chunks.
3. Review cited relationship candidates.
4. Run a company shock scenario on approved evidence.
5. Inspect each result and its source in the evidence desk.
```

Expand `Key capabilities` with only implemented items: full-filing chunking, cited candidate review, grouped graph exploration, scenario layers and animated propagation, chat-created scenarios, responsive evidence UI, persistent hero data, and local/hosted database support.

- [ ] **Step 3: Document sample data and honest limitations**

Add a `Sample data` section explaining that a fresh empty database is seeded with the verified hero graph, filings/passages, approved relationships, and an OpenAI shock scenario. State that no download is required and that existing non-empty databases are preserved.

Add a `Limitations` section stating:

```markdown
- Extraction quality depends on source text and the selected LLM provider.
- Candidate relationships require human review before entering the trusted graph.
- Scenario outputs propagate declared evidence and assumptions; they are not investment advice or price forecasts.
- The fallback provider is deterministic for demos but is not a substitute for model-backed extraction.
```

- [ ] **Step 4: Add the Codex and GPT-5.6 build story**

Add `How GPT-5.6 and Codex accelerated the build` with concrete repository-backed examples:

- repository exploration and conversion of the 40,000-character ingestion cutoff into bounded full-document chunking;
- iterative UX design for the evidence desk, grouped relationships, scenario cards, and propagation animation;
- regression tests and browser-driven diagnosis of hover flicker and disappearing scenario edges;
- deployment hardening for Neon, Render, and Vercel;
- repeated lint, unit-test, API-test, and production-build verification.

Add `Key decisions I kept human` covering the evidence-first product boundary, refusal to invent missing financial values, square financial-terminal visual direction, review-before-trust workflow, and final acceptance of generated changes after reading and testing them.

- [ ] **Step 5: Validate the README**

Run:

```bash
rg -n "Work and productivity|Project description|Sample data|GPT-5.6|Codex|Key decisions I kept human|Limitations" README.md
git diff --check
git diff -- README.md
```

Expected: all required sections are present, whitespace validation exits zero, and the diff contains documentation changes only.

- [ ] **Step 6: Commit the documentation**

```bash
git add README.md revamp/docs/plans/2026-07-20-hackathon-readme-submission.md
git commit -m "docs: prepare hackathon submission README"
```
