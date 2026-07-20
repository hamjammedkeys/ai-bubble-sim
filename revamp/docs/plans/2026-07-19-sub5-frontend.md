# Sub-project 5: Frontend Implementation Plan

**Goal:** A Next.js + React Flow single-page instrument panel that renders the evidence-typed graph, fires the hero scenario with the solid→dissolve animation, and shows the split results — wired to the SP1–SP4 backend. Executed **inline** (visual/integration work verified with screenshots), not subagent-driven.

**Design tokens (color = meaning; chrome is grayscale, only evidence carries hue):**
- bg `#0E1116`, surface `#161B22`, hairline `#2A313C`, text `#E6EDF3`, muted `#8B949E`
- impact red `#E5484D` (equity-method forced loss) · exposure orange `#F5A623` (exposure-at-risk) · amber dissolve `#C99A3B` dashed (unknown) · candidate blue `#4C8DFF` striped
- Type: system sans for prose; **monospace for every number/metric** (ui-monospace / "SF Mono" stack). Numbers are the product.
- Signature: **the dissolve** — on scenario run, edges transition solid→dashed-amber at the evidence boundary; mono value labels appear only where the math is real; caveat co-located with the number.

**Stack:** Next.js (App Router) + TypeScript + Tailwind v4 + `@xyflow/react` (React Flow) + `@dagrejs/dagre`. Under `revamp/frontend/`. Talks to backend at `http://localhost:8000`.

## Tasks (inline; verify each with a screenshot before moving on)

- **T1 — Scaffold + seed.** `create-next-app` (TS, Tailwind, App Router) in `revamp/frontend/`; add `@xyflow/react`, `@dagrejs/dagre`. Add a backend seed script `revamp/backend/seed_hero.py` that inserts the hero graph (MSFT→OpenAI equity 27%, OpenAI→CoreWeave $11.9B purchase_obligation, CoreWeave→Nvidia + Nvidia→TSMC + TSMC→ASML behavioural, all approved) + the credit-event scenario, and a couple of candidate edges. Verify: backend serves `/entities` & `/edges`, frontend dev server boots.
- **T2 — Graph canvas.** Fetch `/entities` + `/edges?status=approved`, lay out with dagre (layered), render custom nodes (entity type label) and custom edges colored by `evidence_class` per the grammar, with a persistent legend + metric cards. Verify screenshot: layered graph, correct colors, legend.
- **T3 — Scenario runner + split results + dissolve.** "Run: OpenAI credit event" button → `POST /scenarios/{id}/run`; apply returned `visual_state` per edge with staged CSS transition (hop-delay); split results panel: **Structural impact** (warm, has numbers) vs **Assumption-dependent** (muted, no numbers). Verify screenshot: 2.7 red on MSFT edge, 11.9 orange on CoreWeave edge, amber dissolve outward, split panel.
- **T4 — Evidence inspector.** Click an edge → right rail: relationship type, metric/value/period (mono), evidence-class badge, exact passage, permitted vs unsupported operation, verification result.
- **T5 — Review queue.** `/edges/candidates` list with verification pass/flag badges; approve / reject; on approve, refetch graph. (Upload modal + edit-before-approve are stretch.)

## Cut order if short: T5 → T4 detail → animation staging (instant recolor still legible). Never cut: correct colors + the impact/exposure split + caveat co-location.

## Acceptance
Graph opens populated + evidence-colored; hero scenario fires showing impact 2.7 (red) and exposure 11.9 (orange) separated in the split panel with amber dissolve for behavioural edges; clicking an edge shows its evidence; candidates are visibly distinct (striped blue) and approvable. Verified by screenshot.
