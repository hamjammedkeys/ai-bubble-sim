# AI Fragility Map Demo MVP Plan Index

The original combined implementation plan has been split into backend and frontend execution plans.

## Plans

- [Backend plan](2026-07-18-ai-fragility-map-backend.md): Python project foundation, DuckDB schema, company universe, official-source ingestion, evidence extraction, stress model, graph export, and FastAPI endpoints.
- [Frontend plan](2026-07-18-ai-fragility-map-frontend.md): Vite React dashboard, scenario controls, Cytoscape network map, ripple animation, company/results panels, and Playwright verification.

## Recommended Execution Order

1. Complete the backend plan through the FastAPI graph endpoints.
2. Complete the frontend plan against the backend API contract.
3. Run the frontend end-to-end verification with both servers running.

## Execution Options

1. **Subagent-Driven (recommended)** - Dispatch a fresh subagent per plan task, review between tasks, fast iteration.
2. **Inline Execution** - Execute plan tasks in this session using executing-plans, batch execution with checkpoints.
