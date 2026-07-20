# Project README Design

## Goal

Create an English repository-level README that lets a hackathon judge or new developer understand FragilityGraph and run the current `revamp` application locally without reading the source code.

## Audience

- Hackathon judges evaluating the product quickly.
- Developers running the project for the first time.

## Structure

The README will contain:

1. A concise product overview and the problem FragilityGraph solves.
2. A feature summary covering evidence-backed graph ingestion, scenario simulation, and the chat copilot.
3. A short architecture and technology-stack overview.
4. Prerequisites: Python 3.11+, Node.js 20+, npm, and optionally `uv`.
5. Copy-paste backend setup and start commands.
6. Copy-paste frontend setup and start commands.
7. Configuration for deterministic offline mode and OpenAI-backed mode.
8. Local application, API health, and Swagger URLs.
9. Test, lint, and production-build commands.
10. Focused troubleshooting for ports, API connectivity, and missing OpenAI credentials.

## Command Policy

Commands must match the repository's current manifests and entrypoints. Backend instructions will use `uv` as the recommended path and include a standard `venv`/`pip` fallback. Frontend instructions will use npm. Commands will be shown from the repository root so working-directory changes are explicit.

## Configuration Policy

The README will never include a real secret. It will direct users to copy:

- `revamp/backend/.env.example` to `revamp/backend/.env`.
- `revamp/frontend/.env.local.example` to `revamp/frontend/.env.local`.

Offline mode will use `LLM_PROVIDER=fallback`. OpenAI mode will document `LLM_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` at a high level.

## Scope

This task creates the root `README.md`. It does not change application behavior, deployment configuration, API contracts, or the generated Next.js README under `revamp/frontend`.

## Verification

- Confirm every documented script exists in `package.json` or `pyproject.toml`.
- Confirm the documented FastAPI module is importable.
- Confirm all example paths and environment templates exist.
- Scan for placeholders, contradictory setup paths, and accidental secrets.
