# Safe Content and Chat Scenario Card Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Contain long external text, standardize terminal scrollbars, and render actionable READY/RUN COMPLETE scenario cards inside Copilot messages.

**Architecture:** Add shared CSS containment/scroll utilities, then introduce a pure parser and focused scenario-card component for chat actions. Refactor scenario execution into an explicit ID-driven parent callback so Scenario Book and Copilot share one propagation path without stale selection state.

**Tech Stack:** Next.js 16.2, React 19.2, TypeScript 5, Vitest, Playwright.

## Global Constraints

- Preserve existing uncommitted node-ignite changes in `revamp/frontend/app/page.tsx` and `revamp/frontend/app/globals.css`; inspect and stage only feature hunks.
- Do not modify the backend chat API contract or backend tool behavior.
- HTTP(S) URL validation remains authoritative; do not make unsafe strings clickable.
- Evidence Desk and Copilot must not create page-level horizontal scrolling.
- Risk Tape retains intentional horizontal scrolling.
- Copilot scenario Run must use the same propagation implementation as Scenario Book.
- A `run_scenario` action already present in the chat response must not be run again automatically.
- Card-level failures preserve the prior successful graph state and scenario details.
- Preserve reduced motion, keyboard focus, drawer behavior, and terminal square geometry.

---

### Task 1: Safe content containment and terminal scrollbars

**Files:**
- Modify: `revamp/frontend/app/globals.css`
- Modify: `revamp/frontend/app/components/evidence-desk.tsx`
- Modify: `revamp/frontend/app/page.tsx`
- Modify: `revamp/frontend/app/components/market-terminal.test.tsx`

**Interfaces:**
- Produces CSS classes `.content-safe` and `.terminal-scrollbar`.
- Consumes existing Evidence Desk, Copilot, scenario, and risk-tape DOM.

- [ ] **Step 1: Write failing structural tests**

Assert rendered Evidence content and Copilot message containers expose the containment/scroll classes, and Risk Tape does not receive horizontal blocking.

```tsx
expect(evidenceHtml).toContain("content-safe");
expect(evidenceHtml).toContain("terminal-scrollbar");
expect(copilotContract).toMatchObject({ messageClassName: expect.stringContaining("content-safe") });
```

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd revamp/frontend && npm test -- app/components/market-terminal.test.tsx`

Expected: FAIL because the containment contract/classes are absent.

- [ ] **Step 3: Implement shared CSS utilities**

Add:

```css
.content-safe {
  min-width: 0;
  max-width: 100%;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.terminal-scrollbar {
  scrollbar-width: thin;
  scrollbar-color: var(--hairline) var(--bg);
}
.terminal-scrollbar::-webkit-scrollbar { width: 8px; height: 8px; }
.terminal-scrollbar::-webkit-scrollbar-track { background: var(--bg); }
.terminal-scrollbar::-webkit-scrollbar-thumb {
  border: 2px solid var(--bg);
  border-radius: 0;
  background: var(--hairline);
}
.terminal-scrollbar::-webkit-scrollbar-thumb:hover { background: var(--muted); }
```

Apply containment to document links, passages, error text, chat bubbles, chat input row, and external/user text. Apply vertical `overflow-x: hidden` only to Evidence/Copilot scrollers. Keep `.risk-tape { overflow-x: auto }`.

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd revamp/frontend && npm test -- app/components/market-terminal.test.tsx`

Expected: all focused tests pass.

- [ ] **Step 5: Commit only Task 1 hunks**

Use `git diff` before staging. Do not stage pre-existing node-ignite hunks in `page.tsx` or `globals.css`.

```bash
git add -p revamp/frontend/app/globals.css revamp/frontend/app/page.tsx
git add revamp/frontend/app/components/evidence-desk.tsx \
  revamp/frontend/app/components/market-terminal.test.tsx
git commit -m "fix(revamp): contain long terminal content"
```

---

### Task 2: Parse chat actions and render scenario cards

**Files:**
- Create: `revamp/frontend/app/lib/chat-actions.ts`
- Create: `revamp/frontend/app/lib/chat-actions.test.ts`
- Create: `revamp/frontend/app/components/chat-scenario-card.tsx`
- Create: `revamp/frontend/app/components/chat-scenario-card.test.tsx`
- Modify: `revamp/frontend/app/lib/api.ts`

**Interfaces:**
- Produces `ChatAction` and typed `ChatReply.actions`.
- Produces `scenarioCardFromActions(actions) -> ChatScenarioCardModel | null`.
- Produces `ChatScenarioCard` with `onRun(scenarioId)` and `onView(scenarioId)` callbacks.

- [ ] **Step 1: Write failing parser tests**

Cover create-only, create plus successful run, malformed result, tool error, and unrelated actions.

```ts
expect(scenarioCardFromActions([createAction])).toMatchObject({
  scenarioId: "scenario-1",
  status: "ready",
  name: "OpenAI shock",
  originEntity: "OpenAI",
  magnitude: 10,
});

expect(scenarioCardFromActions([createAction, runAction])).toMatchObject({
  status: "complete",
  totals: { impact_total: 2.7, exposure_total: 36.8, unresolved_count: 3 },
});
```

- [ ] **Step 2: Run parser tests and verify RED**

Run: `cd revamp/frontend && npm test -- app/lib/chat-actions.test.ts`

Expected: FAIL because the parser module is absent.

- [ ] **Step 3: Implement defensive typed parsing**

Validate records at runtime without adding a schema dependency. Associate `run_scenario.args.name` with the created scenario name. Return null when create result has `error`, missing ID/name/origin, or invalid magnitude. Complete status requires numeric totals.

- [ ] **Step 4: Write failing card component tests**

Assert READY details/button/busy/error states and RUN COMPLETE totals/View button. Use real markup, not snapshots.

- [ ] **Step 5: Implement the square terminal card**

Use existing terminal primitives. READY invokes `onRun(scenarioId)`; COMPLETE invokes `onView(scenarioId)`. Render formatted magnitude/unit honestly and totals through the existing financial formatter.

- [ ] **Step 6: Run Task 2 tests and full frontend tests**

Run:

```bash
cd revamp/frontend
npm test -- app/lib/chat-actions.test.ts app/components/chat-scenario-card.test.tsx
npm test
```

Expected: focused and full suites pass.

- [ ] **Step 7: Commit Task 2**

```bash
git add revamp/frontend/app/lib/api.ts \
  revamp/frontend/app/lib/chat-actions.ts \
  revamp/frontend/app/lib/chat-actions.test.ts \
  revamp/frontend/app/components/chat-scenario-card.tsx \
  revamp/frontend/app/components/chat-scenario-card.test.tsx
git commit -m "feat(revamp): add scenario action cards for chat"
```

---

### Task 3: Integrate Copilot cards with shared scenario propagation

**Files:**
- Modify: `revamp/frontend/app/page.tsx`
- Modify: `revamp/frontend/app/components/market-terminal.test.tsx`

**Interfaces:**
- Consumes `scenarioCardFromActions` and `ChatScenarioCard` from Task 2.
- Produces `runScenarioById(id: string) -> Promise<void>` shared by Scenario Book and Copilot.
- Produces assistant message view-model `{ role, content, actions }`.

- [ ] **Step 1: Write failing state/runner tests at pure seams**

Assert assistant actions stay attached to their response, create-only invokes Run with the exact scenario ID, complete invokes View without a second API run, and card failures remain local.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `cd revamp/frontend && npm test -- app/components/market-terminal.test.tsx`

Expected: FAIL because message/action and ID-driven runner seams are absent.

- [ ] **Step 3: Refactor the scenario runner**

Extract the current `run` body into `runScenarioById(scenarioId)`. Capture the scenario snapshot by ID, select that scenario, preserve mutation locking, origin pulse, propagation timers, drawer follow, totals, errors, and reduced motion. Scenario Book calls it with the current selection.

- [ ] **Step 4: Store and render chat actions**

Attach `res.actions` only to the corresponding assistant message. Render one card from recognized successful actions. Maintain per-card busy/error state keyed by scenario ID.

- [ ] **Step 5: Wire Run and View**

- Run calls `runScenarioById(id)` and closes/de-emphasizes Copilot so propagation is visible.
- View selects the scenario ID, refreshes graph/scenario data, and closes Copilot without calling `api.runScenario`.
- Existing generic `onGraphChanged` behavior remains for ingestion and other mutating tools.

- [ ] **Step 6: Run all automated gates**

```bash
cd revamp/frontend
npm test
npm run lint
npm run build
git diff --check
```

Expected: all commands exit 0.

- [ ] **Step 7: Run browser verification**

At 390×844 and 1440×900 verify:

- a full SEC archive URL wraps with no document-level horizontal overflow;
- a long chat URL wraps without widening the Copilot;
- custom scrollbar classes are present on Evidence and Chat scrollers;
- create-only action shows READY and Run triggers the normal line propagation;
- create-plus-run shows totals and View does not issue another scenario-run request;
- card error remains inside the card;
- Risk Tape still scrolls horizontally when needed.

Capture `/tmp/safe-content-chat-card.png`.

- [ ] **Step 8: Commit only Task 3 hunks**

Inspect `page.tsx` diff and preserve the user's node-ignite changes as unstaged.

```bash
git add -p revamp/frontend/app/page.tsx
git add revamp/frontend/app/components/market-terminal.test.tsx
git commit -m "feat(revamp): run chat scenarios through the graph"
```
