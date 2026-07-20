# Market Terminal UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the existing FragilityGraph frontend as a square, readable financial Market Terminal that exposes scenarios, graph propagation, evidence review, and risk totals in one desktop dashboard.

**Architecture:** Keep the current API and React Flow graph, but separate pure dashboard derivations and interaction sequencing from the page component. Build a small set of terminal layout components around the existing workflows, then add semantic CSS animation and responsive drawers without changing backend calculations.

**Tech Stack:** Next.js 16.2, React 19.2, TypeScript 5, React Flow 12, CSS, Vitest.

## Global Constraints

- Read relevant Next.js 16 guides from `revamp/frontend/node_modules/next/dist/docs/` before changing font or layout code, per `revamp/frontend/AGENTS.md`.
- Use IBM Plex Sans for prose/UI and IBM Plex Mono for financial values/statuses through `next/font/google`.
- Preserve current API contracts and every existing workflow: ingest/extract, inspect, approve/reject, create/run scenario, company details, and copilot.
- Never display absent scenario values as zero; use an em dash or an explicit idle state.
- Preserve evidence semantics: red impact, yellow exposure, amber unresolved, blue candidate, green verification pass.
- Do not add a 3D globe, backend calculations, authentication, background jobs, or a new state-management dependency.
- All motion must have a `prefers-reduced-motion` equivalent with the same final state.

---

### Task 1: Pure dashboard metrics and propagation sequence

**Files:**
- Modify: `revamp/frontend/package.json`
- Modify: `revamp/frontend/package-lock.json`
- Create: `revamp/frontend/app/lib/dashboard.ts`
- Create: `revamp/frontend/app/lib/dashboard.test.ts`

**Interfaces:**
- Consumes: `Entity`, `Edge`, `EdgeResult`, and `ScenarioRun["totals"]` from `app/lib/api.ts`.
- Produces: `deriveDeskMetrics(...) -> DeskMetrics`.
- Produces: `orderedResultIds(results: EdgeResult[]) -> string[]`.
- Produces: `evidenceCoverage(edges: Edge[]) -> number | null`.

- [ ] **Step 1: Add Vitest and a deterministic test script**

Run:

```bash
cd revamp/frontend
npm install --save-dev vitest
```

Add scripts to `package.json`:

```json
"test": "vitest run",
"test:watch": "vitest"
```

- [ ] **Step 2: Write failing derivation tests**

Create `app/lib/dashboard.test.ts` with fixtures that assert:

```ts
import { describe, expect, it } from "vitest";
import { deriveDeskMetrics, evidenceCoverage, orderedResultIds } from "./dashboard";

describe("deriveDeskMetrics", () => {
  it("keeps result-dependent metrics null before a scenario run", () => {
    expect(deriveDeskMetrics([], [], null)).toEqual({
      entityCount: 0,
      approvedEdgeCount: 0,
      candidateCount: 0,
      impactTotal: null,
      exposureTotal: null,
      unresolvedCount: null,
      evidenceCoverage: null,
    });
  });

  it("separates network counts from scenario totals", () => {
    const entities = [{ id: "amazon" }, { id: "anthropic" }] as never[];
    const edges = [
      { id: "approved", status: "approved", verification: { overall: "pass" } },
      { id: "candidate", status: "candidate", verification: { overall: "flag" } },
    ] as never[];
    const totals = { impact_total: 2.7, exposure_total: 8, unresolved_count: 3 };
    expect(deriveDeskMetrics(entities, edges, totals)).toMatchObject({
      entityCount: 2,
      approvedEdgeCount: 1,
      candidateCount: 1,
      impactTotal: 2.7,
      exposureTotal: 8,
      unresolvedCount: 3,
      evidenceCoverage: 50,
    });
  });
});

it("orders structural results before unresolved results", () => {
  const results = [
    { edge_id: "u", kind: "unresolved" },
    { edge_id: "e", kind: "exposure" },
    { edge_id: "i", kind: "impact" },
  ] as never[];
  expect(orderedResultIds(results)).toEqual(["i", "e", "u"]);
});

it("returns null coverage for an empty graph", () => {
  expect(evidenceCoverage([])).toBeNull();
});
```

- [ ] **Step 3: Run tests and verify RED**

Run: `cd revamp/frontend && npm test`

Expected: FAIL because `app/lib/dashboard.ts` does not exist.

- [ ] **Step 4: Implement the pure derivations**

Create `app/lib/dashboard.ts` with exported `DeskMetrics`, `deriveDeskMetrics`,
`evidenceCoverage`, and `orderedResultIds`. Coverage is the percentage of visible approved or
candidate edges whose `verification.overall` is `"pass"`, rounded to the nearest integer. Result
order is impact, exposure, unresolved while preserving input order inside each kind.

- [ ] **Step 5: Run tests and verify GREEN**

Run: `cd revamp/frontend && npm test`

Expected: all dashboard tests pass.

- [ ] **Step 6: Commit the derivation seam**

```bash
git add revamp/frontend/package.json revamp/frontend/package-lock.json \
  revamp/frontend/app/lib/dashboard.ts revamp/frontend/app/lib/dashboard.test.ts
git commit -m "test(revamp): add market desk derivations"
```

### Task 2: Market Terminal fonts, tokens, and primitives

**Files:**
- Modify: `revamp/frontend/app/layout.tsx`
- Modify: `revamp/frontend/app/globals.css`
- Create: `revamp/frontend/app/components/terminal.tsx`

**Interfaces:**
- Produces CSS variables `--font-plex-sans`, `--font-plex-mono`, `--bg`, `--surface`,
  `--surface-raised`, `--hairline`, `--text`, `--muted`, `--impact`, `--exposure`, `--amber`,
  `--candidate`, and `--pass`.
- Produces `TerminalLabel`, `TerminalMetric`, `TerminalButton`, `TerminalPanel`, and
  `TerminalStatus` components.

- [ ] **Step 1: Read the installed Next.js font and root-layout guides**

Run:

```bash
cd revamp/frontend
rg -n "next/font|Root Layout" node_modules/next/dist/docs --glob '*.md' | head -30
```

Open and read the matching Next.js 16 documents completely before editing `layout.tsx`.

- [ ] **Step 2: Replace Geist with IBM Plex font variables**

In `app/layout.tsx`, import `IBM_Plex_Sans` and `IBM_Plex_Mono` from `next/font/google`, configure
Latin subsets and useful weights, and attach both variables to `<html>`. Keep the metadata and
semantic document structure unchanged.

- [ ] **Step 3: Implement terminal tokens and global states**

Update `app/globals.css` to use the approved palette and geometry. Add reusable classes for:

```css
.terminal-panel { border: 1px solid var(--hairline); background: var(--surface); border-radius: 0; }
.terminal-label { font: 600 0.625rem/1 var(--font-plex-mono); letter-spacing: .1em; text-transform: uppercase; color: var(--muted); }
.num { font-family: var(--font-plex-mono), ui-monospace, monospace; font-variant-numeric: tabular-nums; }
.terminal-focus:focus-visible { outline: 1px solid var(--exposure); outline-offset: 2px; }
```

Retain React Flow base styles and map its canvas to the radar/grid projection. Remove rounded
cards and ambient shadows from redesigned surfaces. Preserve reduced-motion rules.

- [ ] **Step 4: Create typed terminal primitives**

Create `app/components/terminal.tsx`. Components accept native button/div attributes where
appropriate, keep semantic elements, expose `tone` values (`neutral`, `impact`, `exposure`,
`candidate`, `pass`), and render no invented fallback values. `TerminalMetric` takes
`value: string | null` and displays `—` for null.

- [ ] **Step 5: Run lint and build**

Run:

```bash
cd revamp/frontend
npm run lint
npm run build
```

Expected: both commands exit 0 with IBM Plex font CSS generated by Next.js.

- [ ] **Step 6: Commit the visual foundation**

```bash
git add revamp/frontend/app/layout.tsx revamp/frontend/app/globals.css \
  revamp/frontend/app/components/terminal.tsx
git commit -m "feat(revamp): add market terminal visual system"
```

### Task 3: Exposure Desk shell, scenario book, and risk tape

**Files:**
- Create: `revamp/frontend/app/components/exposure-desk.tsx`
- Create: `revamp/frontend/app/components/scenario-book.tsx`
- Create: `revamp/frontend/app/components/risk-tape.tsx`
- Modify: `revamp/frontend/app/page.tsx:143-401`

**Interfaces:**
- Consumes: `DeskMetrics` from `app/lib/dashboard.ts`.
- Consumes current `ScenarioControls` behavior through explicit scenario callbacks.
- Produces `ExposureDesk`, `ScenarioBook`, `MarketStrip`, and `RiskTape`.

- [ ] **Step 1: Add the four-zone shell without changing behavior**

Create `ExposureDesk` with semantic regions:

```tsx
<main className="exposure-desk">
  <header className="terminal-header">...</header>
  <section className="market-strip" aria-label="Market summary">...</section>
  <section className="desk-workspace">
    <aside className="scenario-column">...</aside>
    <section className="network-column">...</section>
    <aside className="evidence-column">...</aside>
  </section>
  <footer className="risk-tape">...</footer>
</main>
```

Use slots/children so this component owns layout only, not API state.

- [ ] **Step 2: Move current scenario behavior into Scenario Book**

Create `ScenarioBook` using existing scenario selection, create, Run, and Reset callbacks. Render
all scenarios as square rows, expose the active row with `aria-current`, and preserve the existing
new-scenario form. Add five controlled layer toggles: impact, exposure, unresolved, candidate,
inactive. Their initial values are all `true`.

- [ ] **Step 3: Add market strip and risk tape using derived metrics**

Use `deriveDeskMetrics(entities, edges, totals)` in `page.tsx`. Render scenario-dependent totals
as null before the first run. The risk tape summary uses the selected scenario name and real run
results; it says `Select and run a scenario` in idle state. Do not manufacture evidence coverage
from scenario results—the pure graph coverage calculation is authoritative.

- [ ] **Step 4: Recompose page.tsx around ExposureDesk**

Keep data loading, API calls, entity/edge selection, scenario creation, copilot, ingestion, and
review callbacks in `Home`. Replace the old two-column wrapper and floating scenario controls
with the four-zone shell. Do not modify graph calculation in this task.

- [ ] **Step 5: Verify behavior**

Run:

```bash
cd revamp/frontend
npm test
npm run lint
npm run build
```

Expected: all commands exit 0; idle metrics use em dashes and existing scenario actions compile.

- [ ] **Step 6: Commit the desk shell**

```bash
git add revamp/frontend/app/page.tsx revamp/frontend/app/components/exposure-desk.tsx \
  revamp/frontend/app/components/scenario-book.tsx revamp/frontend/app/components/risk-tape.tsx
git commit -m "feat(revamp): build exposure desk layout"
```

### Task 4: Network projection, filters, and evidence review

**Files:**
- Modify: `revamp/frontend/app/lib/graph.ts`
- Modify: `revamp/frontend/app/page.tsx`
- Create: `revamp/frontend/app/components/evidence-desk.tsx`
- Test: `revamp/frontend/app/lib/dashboard.test.ts`

**Interfaces:**
- Produces `GraphFilters = Record<VisualState, boolean>`.
- Produces `edgeVisible(visualState: VisualState, filters: GraphFilters) -> boolean`.
- Produces `EvidenceDesk` with evidence/company/queue/ingestion modes.

- [ ] **Step 1: Write a failing graph-filter test**

Add to `dashboard.test.ts` (or a focused `graph.test.ts` if imports remain cleaner):

```ts
it("hides only disabled visual layers", () => {
  const filters = { grey: true, impact: true, exposure: false, amber: true, candidate: true };
  expect(edgeVisible("exposure", filters)).toBe(false);
  expect(edgeVisible("impact", filters)).toBe(true);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run: `cd revamp/frontend && npm test`

Expected: FAIL because `edgeVisible` and `GraphFilters` do not exist.

- [ ] **Step 3: Implement graph layers and terminal node treatment**

Add the filter types and pure visibility function to `graph.ts`. Apply filter state in `rfEdges`
using React Flow's `hidden` property, never by deleting API edges. Update node and edge renderers
to use square terminal styling, mono badges, non-color relationship labels, and dim unrelated
elements on selection/hover.

- [ ] **Step 4: Build Evidence Desk from existing panels**

Move/recompose the current evidence inspector, company panel, ingestion panel, review queue, and
scenario results into `EvidenceDesk`. Its priority is:

1. selected edge evidence;
2. selected company;
3. active propagation result;
4. candidate queue and filing ingestion.

Candidate evidence mode contains Approve and Reject controls beside all mechanical check rows.
Approve/Reject call the existing API methods, preserve error messages in the panel, reload graph
data on success, and keep the selected edge long enough to display its final state.

- [ ] **Step 5: Verify graph and review workflows**

Run:

```bash
cd revamp/frontend
npm test
npm run lint
npm run build
```

Expected: all commands exit 0; graph filter tests pass; all prior workflows remain reachable.

- [ ] **Step 6: Commit projection and evidence desk**

```bash
git add revamp/frontend/app/lib/graph.ts revamp/frontend/app/lib/dashboard.test.ts \
  revamp/frontend/app/page.tsx revamp/frontend/app/components/evidence-desk.tsx
git commit -m "feat(revamp): add terminal graph and evidence desk"
```

### Task 5: Semantic scenario animation and responsive states

**Files:**
- Create: `revamp/frontend/app/lib/propagation.ts`
- Create: `revamp/frontend/app/lib/propagation.test.ts`
- Modify: `revamp/frontend/app/page.tsx`
- Modify: `revamp/frontend/app/globals.css`

**Interfaces:**
- Produces `propagationFrames(results: EdgeResult[]) -> PropagationFrame[]` where each frame has
  `edgeId`, `kind`, and `delayMs`.
- Consumes `orderedResultIds` and the existing React Flow edge visual states.

- [ ] **Step 1: Write failing deterministic animation tests**

Create `propagation.test.ts`:

```ts
import { expect, it } from "vitest";
import { propagationFrames } from "./propagation";

it("assigns one 700ms frame per ordered result", () => {
  const results = [
    { edge_id: "impact", kind: "impact" },
    { edge_id: "unresolved", kind: "unresolved" },
  ] as never[];
  expect(propagationFrames(results)).toEqual([
    { edgeId: "impact", kind: "impact", delayMs: 0 },
    { edgeId: "unresolved", kind: "unresolved", delayMs: 700 },
  ]);
});
```

- [ ] **Step 2: Run test and verify RED**

Run: `cd revamp/frontend && npm test`

Expected: FAIL because `propagation.ts` does not exist.

- [ ] **Step 3: Implement frames and connect animation state**

Implement pure frames and replace the current two-phase timeout with a cleanup-safe effect that
reveals each result according to its frame. On each frame, set the active edge id so the graph
traces it and the inspector follows it. Clear all scheduled timers when rerunning, resetting, or
unmounting. The full API result remains stored immediately; animation only controls presentation.

- [ ] **Step 4: Add CSS motion and reduced-motion behavior**

Add one-shot origin pulse, edge trace, metric update, short panel entry, and candidate approval
state classes. In `prefers-reduced-motion: reduce`, disable animation/transition durations and
show all run results immediately. Candidate marching remains the only continuous default motion.

- [ ] **Step 5: Add responsive layout states**

At widths below the desktop breakpoint, move Scenario Book above the graph as a compact selector,
turn Evidence Desk into a keyboard-accessible overlay/drawer, and allow Risk Tape to scroll
horizontally. Do not compress labels below the approved minimum size.

- [ ] **Step 6: Run full frontend verification**

Run:

```bash
cd revamp/frontend
npm test
npm run lint
npm run build
```

Expected: all commands exit 0 with deterministic propagation tests passing.

- [ ] **Step 7: Commit animation and responsive behavior**

```bash
git add revamp/frontend/app/lib/propagation.ts revamp/frontend/app/lib/propagation.test.ts \
  revamp/frontend/app/page.tsx revamp/frontend/app/globals.css
git commit -m "feat(revamp): animate evidence propagation"
```

### Task 6: Visual and end-to-end demo verification

**Files:**
- Verify: all modified files under `revamp/frontend/`.

**Interfaces:** None.

- [ ] **Step 1: Start the backend and frontend using existing project commands**

Run backend: `cd revamp/backend && uv run uvicorn app.main:app --reload`

Run frontend: `cd revamp/frontend && npm run dev`

- [ ] **Step 2: Verify the primary demo path at a desktop viewport**

At approximately 1440×900, confirm in order:

1. the Exposure Desk shows scenario, graph, evidence rail, and risk tape without overlap;
2. idle scenario totals show em dashes;
3. selecting and running a scenario traces every returned result and ends at exact API totals;
4. selecting an edge shows citation and verification checks;
5. approving/rejecting a candidate updates its edge and queue state;
6. company selection remains usable;
7. filing ingestion and copilot remain reachable;
8. backend failure displays an error without erasing the last successful state.

- [ ] **Step 3: Verify reduced motion and narrow layout**

Enable reduced motion in browser emulation and confirm final states appear without tracing or
count-up. At a narrow viewport, confirm Scenario Book compacts, Evidence Desk opens as a drawer,
and Risk Tape scrolls without clipped labels.

- [ ] **Step 4: Capture a final screenshot for review**

Save the screenshot under `revamp/docs/screenshots/market-terminal.png` only if the repository
already tracks review screenshots there; otherwise report the temporary artifact path without
adding it to git.

- [ ] **Step 5: Run fresh final checks**

Run:

```bash
cd revamp/frontend
npm test
npm run lint
npm run build
```

Expected: all commands exit 0.
