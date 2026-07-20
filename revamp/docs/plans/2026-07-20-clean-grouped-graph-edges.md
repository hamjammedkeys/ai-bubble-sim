# Clean Grouped Graph Edges Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace spaghetti-like fan-out routing with one calm visual connection per directed company pair while keeping every underlying relationship accessible in the Evidence Desk.

**Architecture:** Group API edges only in the frontend presentation layer. A pure graph utility chooses each group's representative and highest-priority semantic state; `page.tsx` renders one React Flow edge per group, and `EvidenceDesk` provides navigation across the group's original edges. Backend records and scenario results remain unchanged.

**Tech Stack:** Next.js 16.2, React 19.2, TypeScript 5, React Flow 12, Vitest, Playwright smoke scripts.

## Global Constraints

- Preserve fixed React Flow node dimensions from commit `fe8d6c6` so hover never triggers remeasurement flicker.
- Do not merge, delete, or rewrite backend edge records.
- Render one restrained connection for each directed source/target pair.
- A grouped connection uses priority `impact > exposure > unresolved > candidate > inactive`.
- Individual filing passages, values, verification states, and review actions remain available in the Evidence Desk.
- Mouse and keyboard activation must behave equivalently.
- Preserve scenario propagation, layer filters, reduced motion, and the existing terminal palette.

---

### Task 1: Pure edge grouping and semantic priority

**Files:**
- Modify: `revamp/frontend/app/lib/graph.ts`
- Modify: `revamp/frontend/app/lib/graph.test.ts`

**Interfaces:**
- Consumes: `Edge[]` and `Record<string, EdgeResult>`.
- Produces: `groupGraphEdges(edges, results) -> GraphEdgeGroup[]`.
- Produces `GraphEdgeGroup` with `id`, `source`, `target`, `edges`, `representative`, and `visualState`.

- [ ] **Step 1: Write failing grouping tests**

Add fixtures asserting that three edges with the same directed endpoints produce one group, reverse-direction edges produce a separate group, all original edge IDs remain in `group.edges`, and an impact result outranks exposure/candidate/inactive.

```ts
const groups = groupGraphEdges(
  [candidateEdge, exposureEdge, impactEdge, reverseEdge],
  {
    exposure: { edge_id: "exposure", visual_state: "solid_orange" } as EdgeResult,
    impact: { edge_id: "impact", visual_state: "solid_red" } as EdgeResult,
  },
);

expect(groups).toHaveLength(2);
expect(groups[0].edges.map((edge) => edge.id)).toEqual([
  "candidate",
  "exposure",
  "impact",
]);
expect(groups[0].representative.id).toBe("impact");
expect(groups[0].visualState).toBe("impact");
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd revamp/frontend && npm test -- app/lib/graph.test.ts`

Expected: FAIL because `groupGraphEdges` and `GraphEdgeGroup` do not exist.

- [ ] **Step 3: Implement deterministic grouping**

Use a directed key `${source_entity_id}->${target_entity_id}`. Ignore edges missing either endpoint. Preserve API input order inside each group. Derive state with the existing `visualStateFor`, then choose the first edge at the highest priority.

```ts
const VISUAL_PRIORITY: Record<VisualState, number> = {
  impact: 5,
  exposure: 4,
  amber: 3,
  candidate: 2,
  grey: 1,
};
```

Delete `routingLaneOffset` and `routingOffsetForEdge`; keep `NODE_W`, `NODE_H`, `reactFlowNodeDimensions`, layout, filter, focus, and visual-state helpers.

- [ ] **Step 4: Run focused and full graph tests**

Run: `cd revamp/frontend && npm test -- app/lib/graph.test.ts`

Expected: all graph tests pass, including fixed node dimensions and grouping semantics.

- [ ] **Step 5: Commit the pure grouping seam**

```bash
git add revamp/frontend/app/lib/graph.ts revamp/frontend/app/lib/graph.test.ts
git commit -m "refactor(revamp): group graph edges by company pair"
```

---

### Task 2: Calm grouped-edge rendering and interaction

**Files:**
- Modify: `revamp/frontend/app/page.tsx`
- Modify: `revamp/frontend/app/components/market-terminal.test.tsx`

**Interfaces:**
- Consumes: `groupGraphEdges(edges, presentedResults)` from Task 1.
- Produces one `RFEdge` per `GraphEdgeGroup`.
- Passes `selectedEdgeGroup: Edge[]` to the Evidence Desk in Task 3.

- [ ] **Step 1: Add failing presentation tests**

Extend the component seam to verify label copy:

```tsx
expect(renderGroupedEdgeLabel({ count: 3, active: false })).toBe("3 relationships");
expect(renderGroupedEdgeLabel({ count: 1, active: false })).toBeNull();
expect(renderGroupedEdgeLabel({ count: 1, active: true, relationship: "take or pay" }))
  .toBe("take or pay");
```

The test must also assert that activation returns the representative underlying edge ID rather than the synthetic group ID.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd revamp/frontend && npm test -- app/components/market-terminal.test.tsx`

Expected: FAIL because grouped-edge presentation helpers are absent.

- [ ] **Step 3: Replace fan-out rendering with grouped rendering**

In `page.tsx`, remove outgoing/parallel indexes and routing offsets. Build groups once:

```ts
const graphEdgeGroups = groupGraphEdges(edges, presentedResults);
```

For each group:

- use `group.id` as the React Flow edge ID;
- use a shallow default Bezier (`offset: 0`);
- mark selected when `group.edges.some((edge) => edge.id === selected)`;
- mark active/recently-approved when any underlying edge matches;
- select the currently selected member when present, otherwise `group.representative.id`;
- display `N relationships` at rest only when `N > 1`;
- reveal a single relationship type on hover, focus, or selection;
- keep the accessible label explicit, for example `Inspect 3 relationships from Microsoft to CoreWeave`.

Map group hover/focus to its representative edge for `graphFocusFor`, so both endpoint nodes remain emphasized without modifying underlying evidence state.

- [ ] **Step 4: Verify mouse and keyboard behavior**

Run focused tests and confirm Enter/Space invokes the same representative edge callback as click. Confirm the fixed `width` and `height` fields remain on every RF node.

- [ ] **Step 5: Commit grouped graph presentation**

```bash
git add revamp/frontend/app/page.tsx \
  revamp/frontend/app/components/market-terminal.test.tsx
git commit -m "feat(revamp): render calm grouped graph connections"
```

---

### Task 3: Navigate grouped evidence and visually verify density

**Files:**
- Modify: `revamp/frontend/app/components/evidence-desk.tsx`
- Modify: `revamp/frontend/app/components/market-terminal.test.tsx`
- Modify: `revamp/frontend/app/page.tsx`

**Interfaces:**
- Adds `selectedEdgeGroup: Edge[]` to `EvidenceDeskProps`.
- Reuses `onSelectEdge(id)` to navigate between original edges.

- [ ] **Step 1: Write failing Evidence Desk group tests**

Render the Evidence Desk with three same-pair edges and one selected edge. Assert:

```tsx
expect(html).toContain("Relationship 2 of 3");
expect(html).toContain("take or pay");
expect(html).toContain("purchase obligation");
```

Add accessible Previous/Next controls and assert they are disabled only at their respective boundaries. Single-edge groups must not render the navigator.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd revamp/frontend && npm test -- app/components/market-terminal.test.tsx`

Expected: FAIL because the group navigator and prop do not exist.

- [ ] **Step 3: Implement the compact group navigator**

At the top of `EvidenceInspector`, render a square terminal row only when `selectedEdgeGroup.length > 1`:

```tsx
<div aria-label="Relationships in this company pair">
  <button onClick={() => onSelectEdge(previous.id)}>Previous</button>
  <span className="num">Relationship {index + 1} of {group.length}</span>
  <button onClick={() => onSelectEdge(next.id)}>Next</button>
</div>
```

List compact relationship-type chips beneath the counter; selecting a chip loads that edge's existing detail endpoint. Preserve candidate Approve/Reject behavior and panel-local error handling.

- [ ] **Step 4: Run all automated verification**

Run:

```bash
cd revamp/frontend
npm test
npm run lint
npm run build
git diff --check
```

Expected: all tests pass, ESLint exits 0, Next.js production build exits 0, and diff-check prints nothing.

- [ ] **Step 5: Run browser regressions against the current CoreWeave data**

At 1440×900 and 968×565, use Playwright to assert:

- the number of rendered React Flow edges equals the number of unique directed endpoint pairs;
- no duplicate group ID is present;
- sweeping across every node produces exactly one `mouseenter` and one `mouseleave`;
- grouped edges expose `N relationships` and keyboard activation opens the Evidence Desk;
- no large fan-out routing offset remains in edge data.

Capture the final desktop screenshot to `/tmp/clean-grouped-graph.png` for visual inspection.

- [ ] **Step 6: Commit Evidence Desk navigation and verification**

```bash
git add revamp/frontend/app/page.tsx \
  revamp/frontend/app/components/evidence-desk.tsx \
  revamp/frontend/app/components/market-terminal.test.tsx
git commit -m "feat(revamp): navigate evidence within grouped edges"
```
