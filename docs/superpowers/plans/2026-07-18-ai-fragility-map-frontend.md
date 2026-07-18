# AI Fragility Map Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the custom web dashboard for AI Fragility Map: first-screen network map, scenario controls, ripple-through-map animation, results panel, and company inspection panel.

**Architecture:** A Vite React TypeScript frontend consumes the backend graph API and renders the directed AI supply-chain graph with Cytoscape.js. The app opens directly on the working map and treats the red ripple animation as the hero interaction. Playwright verifies the dashboard opens and can run a shock.

**Tech Stack:** Vite, React, TypeScript, Cytoscape.js, Vitest, Testing Library, Playwright.

## Global Constraints

- Dashboard opens directly on the working network map.
- Ripple animation is the hero interaction.
- Real public company names are allowed in the UI.
- Every estimate must be visibly labeled as exact, percentage-derived, range-derived, or inferred.
- Scenario language must say "estimated impact under scenario", not "predicted loss".
- Controls must stay compact so the map remains visually dominant.
- Do not build a marketing landing page.
- Keep `.superpowers/` untracked.

---

## Backend API Contract

The frontend consumes:

```http
POST /api/scenario/cloud-slowdown
Content-Type: application/json
```

Request:

```json
{
  "shock_percentage": 0.3,
  "pass_through_rate": 0.8,
  "propagation_factor": 0.5,
  "max_rounds": 3
}
```

Response:

```ts
interface GraphPayload {
  nodes: Array<{
    data: {
      id: string;
      label: string;
      sectorGroup: string;
      revenue: number;
      revenueLoss: number;
      stressStatus: "stable" | "exposed" | "stressed" | "critical";
    };
  }>;
  edges: Array<{
    data: {
      id: string;
      source: string;
      target: string;
      annualFlowBase: number;
      confidenceScore: number;
      estimateMethod: string;
    };
  }>;
  pulses: Array<{
    relationshipId: string;
    source: string;
    target: string;
    roundIndex: number;
    revenueLoss: number;
  }>;
  summary: {
    scenarioLanguage: "estimated impact under scenario";
    totalRevenueLost: number;
    stressedCompanyCount: number;
  };
}
```

---

## Frontend File Structure

```text
package.json
frontend/
  package.json
  index.html
  tsconfig.json
  vite.config.ts
  src/
    main.tsx
    App.tsx
    api.ts
    types.ts
    styles.css
    components/
      NetworkMap.tsx
      ScenarioControls.tsx
      ResultsPanel.tsx
      CompanyPanel.tsx
  tests/
    App.test.tsx
e2e/
  dashboard.spec.ts
README.md
```

---

### Task 1: Vite React Dashboard Shell

**Files:**
- Create: `package.json`
- Create: `frontend/package.json`
- Create: `frontend/index.html`
- Create: `frontend/tsconfig.json`
- Create: `frontend/vite.config.ts`
- Create: `frontend/src/main.tsx`
- Create: `frontend/src/App.tsx`
- Create: `frontend/src/api.ts`
- Create: `frontend/src/types.ts`
- Create: `frontend/src/styles.css`
- Create: `frontend/tests/App.test.tsx`

**Interfaces:**
- Produces: `GraphPayload`, `GraphNode`, `GraphEdge`, `EdgePulse`, `StressStatus` TypeScript types.
- Produces: `runCloudSlowdown(params) -> Promise<GraphPayload>`.
- Produces first-screen app shell with title, scenario language, controls, map area, results panel, and company panel.

- [ ] **Step 1: Write failing frontend smoke test**

Create `frontend/tests/App.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

describe("App", () => {
  it("opens on the working AI fragility map", async () => {
    render(<App />);

    expect(await screen.findByText("AI Fragility Map")).toBeTruthy();
    expect(screen.getByText("estimated impact under scenario")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Run shock" })).toBeTruthy();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run:

```bash
npm --prefix frontend run test -- --run
```

Expected: FAIL because the frontend project does not exist.

- [ ] **Step 3: Add root and frontend package files**

Create root `package.json`:

```json
{
  "name": "ai-fragility-map-workspace",
  "private": true,
  "scripts": {
    "dev": "npm --prefix frontend run dev",
    "test": "npm --prefix frontend run test",
    "e2e": "playwright test"
  },
  "devDependencies": {
    "@playwright/test": "^1.46.0"
  }
}
```

Create `frontend/package.json`:

```json
{
  "name": "ai-fragility-map-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite --host 127.0.0.1",
    "build": "vite build",
    "test": "vitest"
  },
  "dependencies": {
    "@vitejs/plugin-react": "^4.3.1",
    "cytoscape": "^3.30.2",
    "vite": "^5.4.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@testing-library/jest-dom": "^6.4.8",
    "@types/react": "^18.3.3",
    "@types/react-dom": "^18.3.0",
    "jsdom": "^24.1.1",
    "typescript": "^5.5.4",
    "vitest": "^2.0.5"
  }
}
```

- [ ] **Step 4: Add Vite configuration**

Create `frontend/index.html`:

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>AI Fragility Map</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

Create `frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["DOM", "DOM.Iterable", "ES2020"],
    "allowJs": false,
    "skipLibCheck": true,
    "esModuleInterop": true,
    "allowSyntheticDefaultImports": true,
    "strict": true,
    "forceConsistentCasingInFileNames": true,
    "module": "ESNext",
    "moduleResolution": "Node",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx"
  },
  "include": ["src", "tests"]
}
```

Create `frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000"
    }
  },
  test: {
    environment: "jsdom",
    globals: true
  }
});
```

- [ ] **Step 5: Add types and API client**

Create `frontend/src/types.ts`:

```ts
export type StressStatus = "stable" | "exposed" | "stressed" | "critical";

export interface GraphNode {
  data: {
    id: string;
    label: string;
    sectorGroup: string;
    revenue: number;
    revenueLoss: number;
    stressStatus: StressStatus;
  };
}

export interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    annualFlowBase: number;
    confidenceScore: number;
    estimateMethod: string;
  };
}

export interface EdgePulse {
  relationshipId: string;
  source: string;
  target: string;
  roundIndex: number;
  revenueLoss: number;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
  pulses: EdgePulse[];
  summary: {
    scenarioLanguage: string;
    totalRevenueLost: number;
    stressedCompanyCount: number;
  };
}
```

Create `frontend/src/api.ts`:

```ts
import type { GraphPayload } from "./types";

export async function runCloudSlowdown(params: {
  shock_percentage: number;
  pass_through_rate: number;
  propagation_factor: number;
  max_rounds: number;
}): Promise<GraphPayload> {
  const response = await fetch("/api/scenario/cloud-slowdown", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params)
  });
  if (!response.ok) {
    throw new Error(`Scenario request failed: ${response.status}`);
  }
  return response.json();
}
```

- [ ] **Step 6: Add app shell without graph rendering**

Create `frontend/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./styles.css";

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

Create `frontend/src/App.tsx`:

```tsx
import { useState } from "react";
import type { GraphPayload } from "./types";

const initialGraph: GraphPayload = {
  nodes: [],
  edges: [],
  pulses: [],
  summary: {
    scenarioLanguage: "estimated impact under scenario",
    totalRevenueLost: 0,
    stressedCompanyCount: 0
  }
};

export default function App() {
  const [graph] = useState<GraphPayload>(initialGraph);

  return (
    <main className="app-shell">
      <header className="topbar">
        <h1>AI Fragility Map</h1>
        <span>{graph.summary.scenarioLanguage}</span>
      </header>
      <section className="workspace">
        <aside className="left-rail">
          <section className="panel controls">
            <h2>Cloud AI Spending Slowdown</h2>
            <button type="button">Run shock</button>
          </section>
        </aside>
        <section className="network-map" aria-label="AI supply-chain network map" />
        <aside className="right-rail">
          <section className="panel">
            <h2>Company</h2>
            <p>Select a node to inspect estimated impact and source basis.</p>
          </section>
        </aside>
      </section>
    </main>
  );
}
```

Create `frontend/src/styles.css`:

```css
* {
  box-sizing: border-box;
}

body {
  margin: 0;
  font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
  background: #eef3f7;
  color: #102033;
}

button,
select {
  font: inherit;
}

.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.topbar {
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  background: #ffffff;
  border-bottom: 1px solid #d9e2eb;
}

.topbar h1 {
  margin: 0;
  font-size: 22px;
}

.topbar span {
  color: #54677d;
  font-size: 14px;
}

.workspace {
  flex: 1;
  display: grid;
  grid-template-columns: 280px minmax(0, 1fr) 300px;
  min-height: 0;
}

.left-rail,
.right-rail {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.panel {
  background: #ffffff;
  border: 1px solid #d9e2eb;
  border-radius: 8px;
  padding: 14px;
}

.panel h2 {
  margin: 0 0 12px;
  font-size: 15px;
}

.controls button {
  width: 100%;
  min-height: 36px;
  border: 0;
  border-radius: 6px;
  background: #d64b4b;
  color: white;
  font-weight: 700;
  cursor: pointer;
}

.network-map {
  min-height: calc(100vh - 64px);
  background: #f8fbfd;
  border-left: 1px solid #d9e2eb;
  border-right: 1px solid #d9e2eb;
}
```

- [ ] **Step 7: Run frontend smoke test**

Run:

```bash
npm --prefix frontend install
npm --prefix frontend run test -- --run
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add package.json frontend
git commit -m "feat: add frontend dashboard shell"
```

---

### Task 2: Dashboard Panels And Scenario State

**Files:**
- Modify: `frontend/src/App.tsx`
- Create: `frontend/src/components/ScenarioControls.tsx`
- Create: `frontend/src/components/ResultsPanel.tsx`
- Create: `frontend/src/components/CompanyPanel.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/tests/App.test.tsx`

**Interfaces:**
- Produces: `ScenarioControls({ shock, onShockChange, onRun })`.
- Produces: `ResultsPanel({ graph })`.
- Produces: `CompanyPanel({ node })`.
- Produces app state for shock percentage, selected company, replay token, and graph payload.

- [ ] **Step 1: Extend smoke test**

Modify `frontend/tests/App.test.tsx`:

```tsx
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import App from "../src/App";

describe("App", () => {
  it("opens on the working AI fragility map", async () => {
    render(<App />);

    expect(await screen.findByText("AI Fragility Map")).toBeTruthy();
    expect(screen.getByText("estimated impact under scenario")).toBeTruthy();
    expect(screen.getByRole("button", { name: "Run shock" })).toBeTruthy();
    expect(screen.getByText("Cloud AI Spending Slowdown")).toBeTruthy();
    expect(screen.getByText("Scenario Results")).toBeTruthy();
    expect(screen.getByText("Company")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Add panel components**

Create `frontend/src/components/ScenarioControls.tsx`:

```tsx
interface Props {
  shock: number;
  onShockChange: (value: number) => void;
  onRun: () => void;
}

export function ScenarioControls({ shock, onShockChange, onRun }: Props) {
  return (
    <section className="panel controls">
      <h2>Cloud AI Spending Slowdown</h2>
      <label>
        Shock
        <select value={shock} onChange={(event) => onShockChange(Number(event.target.value))}>
          <option value={0.2}>20%</option>
          <option value={0.3}>30%</option>
          <option value={0.4}>40%</option>
        </select>
      </label>
      <button type="button" onClick={onRun}>Run shock</button>
      <p className="assumption">Pass-through 80% · Propagation 50% · 3 rounds</p>
    </section>
  );
}
```

Create `frontend/src/components/ResultsPanel.tsx`:

```tsx
import type { GraphPayload } from "../types";

interface Props {
  graph: GraphPayload;
}

export function ResultsPanel({ graph }: Props) {
  return (
    <section className="panel">
      <h2>Scenario Results</h2>
      <p className="scenario-language">{graph.summary.scenarioLanguage}</p>
      <dl>
        <div>
          <dt>Total revenue lost</dt>
          <dd>${Math.round(graph.summary.totalRevenueLost).toLocaleString()}M</dd>
        </div>
        <div>
          <dt>Stressed companies</dt>
          <dd>{graph.summary.stressedCompanyCount}</dd>
        </div>
      </dl>
    </section>
  );
}
```

Create `frontend/src/components/CompanyPanel.tsx`:

```tsx
import type { GraphNode } from "../types";

interface Props {
  node: GraphNode | null;
}

export function CompanyPanel({ node }: Props) {
  if (!node) {
    return (
      <section className="panel">
        <h2>Company</h2>
        <p>Select a node to inspect estimated impact and source basis.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>{node.data.label}</h2>
      <dl>
        <div>
          <dt>Status</dt>
          <dd>{node.data.stressStatus}</dd>
        </div>
        <div>
          <dt>Revenue loss</dt>
          <dd>${Math.round(node.data.revenueLoss).toLocaleString()}M</dd>
        </div>
      </dl>
      <p className="assumption">Estimate label and evidence snippets attach here as extraction coverage grows.</p>
    </section>
  );
}
```

- [ ] **Step 3: Wire panels into App**

Replace `frontend/src/App.tsx`:

```tsx
import { useCallback, useEffect, useState } from "react";
import { runCloudSlowdown } from "./api";
import { CompanyPanel } from "./components/CompanyPanel";
import { ResultsPanel } from "./components/ResultsPanel";
import { ScenarioControls } from "./components/ScenarioControls";
import type { GraphNode, GraphPayload } from "./types";

const initialGraph: GraphPayload = {
  nodes: [],
  edges: [],
  pulses: [],
  summary: {
    scenarioLanguage: "estimated impact under scenario",
    totalRevenueLost: 0,
    stressedCompanyCount: 0
  }
};

export default function App() {
  const [graph, setGraph] = useState<GraphPayload>(initialGraph);
  const [shock, setShock] = useState(0.3);
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null);
  const [replayToken, setReplayToken] = useState(0);

  const runScenario = useCallback(async () => {
    try {
      const payload = await runCloudSlowdown({
        shock_percentage: shock,
        pass_through_rate: 0.8,
        propagation_factor: 0.5,
        max_rounds: 3
      });
      setGraph(payload);
      setReplayToken((value) => value + 1);
    } catch {
      setGraph(initialGraph);
    }
  }, [shock]);

  useEffect(() => {
    void runScenario();
  }, [runScenario]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <h1>AI Fragility Map</h1>
        <span>{graph.summary.scenarioLanguage}</span>
      </header>
      <section className="workspace">
        <aside className="left-rail">
          <ScenarioControls shock={shock} onShockChange={setShock} onRun={runScenario} />
          <ResultsPanel graph={graph} />
        </aside>
        <section
          className="network-map"
          aria-label="AI supply-chain network map"
          data-replay-token={replayToken}
        />
        <aside className="right-rail">
          <CompanyPanel node={selectedNode} />
        </aside>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Extend styles**

Append to `frontend/src/styles.css`:

```css
.controls label {
  display: grid;
  gap: 6px;
  color: #455a70;
  font-size: 13px;
}

.controls select,
.controls button {
  width: 100%;
  min-height: 36px;
}

.controls button {
  margin-top: 12px;
}

.assumption,
.scenario-language {
  color: #5f7187;
  font-size: 13px;
}

dl {
  display: grid;
  gap: 10px;
  margin: 0;
}

dt {
  color: #607086;
  font-size: 12px;
}

dd {
  margin: 2px 0 0;
  font-weight: 700;
}

@media (max-width: 980px) {
  .workspace {
    grid-template-columns: 1fr;
  }

  .left-rail,
  .right-rail {
    order: 2;
  }

  .network-map {
    min-height: 60vh;
    order: 1;
  }
}
```

- [ ] **Step 5: Verify and commit**

Run:

```bash
npm --prefix frontend run test -- --run
```

Expected: PASS.

Commit:

```bash
git add frontend/src frontend/tests/App.test.tsx
git commit -m "feat: add dashboard panels and scenario state"
```

---

### Task 3: Cytoscape Network Map And Ripple Animation

**Files:**
- Create: `frontend/src/components/NetworkMap.tsx`
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`
- Modify: `frontend/tests/App.test.tsx`

**Interfaces:**
- Produces: `NetworkMap({ graph, replayToken, onSelectNode })`.
- Consumes: `graph.nodes`, `graph.edges`, and `graph.pulses`.
- Replays red edge pulses whenever `replayToken` changes.

- [ ] **Step 1: Add map expectation to test**

Modify `frontend/tests/App.test.tsx` so the test also checks:

```tsx
expect(screen.getByLabelText("AI supply-chain network map")).toBeTruthy();
```

- [ ] **Step 2: Create NetworkMap component**

Create `frontend/src/components/NetworkMap.tsx`:

```tsx
import cytoscape, { Core } from "cytoscape";
import { useEffect, useRef } from "react";
import type { GraphNode, GraphPayload } from "../types";

interface Props {
  graph: GraphPayload;
  replayToken: number;
  onSelectNode: (node: GraphNode | null) => void;
}

const statusColors: Record<string, string> = {
  stable: "#2f7d59",
  exposed: "#e0a423",
  stressed: "#d66a2a",
  critical: "#b72d3a"
};

export function NetworkMap({ graph, replayToken, onSelectNode }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;
    cyRef.current?.destroy();
    const cy = cytoscape({
      container: containerRef.current,
      elements: [...graph.nodes, ...graph.edges],
      layout: { name: "breadthfirst", directed: true, spacingFactor: 1.35 },
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": (element) => statusColors[element.data("stressStatus")] ?? "#65758b",
            color: "#102033",
            "font-size": 11,
            "text-valign": "bottom",
            "text-margin-y": 8,
            width: (element) => Math.max(36, Math.min(86, Math.sqrt(element.data("revenue")) / 2)),
            height: (element) => Math.max(36, Math.min(86, Math.sqrt(element.data("revenue")) / 2))
          }
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#91a3b7",
            "target-arrow-color": "#91a3b7",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.55
          }
        },
        {
          selector: ".pulse",
          style: {
            width: 7,
            "line-color": "#d64b4b",
            "target-arrow-color": "#d64b4b",
            opacity: 1
          }
        }
      ]
    });

    cy.on("tap", "node", (event) => {
      const id = event.target.id();
      onSelectNode(graph.nodes.find((node) => node.data.id === id) ?? null);
    });
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectNode(null);
    });
    cyRef.current = cy;
    return () => cy.destroy();
  }, [graph, onSelectNode]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    graph.pulses.forEach((pulse, index) => {
      window.setTimeout(() => {
        const edge = cy.getElementById(pulse.relationshipId);
        edge.addClass("pulse");
        window.setTimeout(() => edge.removeClass("pulse"), 650);
      }, index * 420);
    });
  }, [graph.pulses, replayToken]);

  return <div className="network-map" ref={containerRef} aria-label="AI supply-chain network map" />;
}
```

- [ ] **Step 3: Use NetworkMap in App**

In `frontend/src/App.tsx`, add:

```tsx
import { NetworkMap } from "./components/NetworkMap";
```

Replace the temporary map section with:

```tsx
<NetworkMap graph={graph} replayToken={replayToken} onSelectNode={setSelectedNode} />
```

- [ ] **Step 4: Verify and commit**

Run:

```bash
npm --prefix frontend run test -- --run
```

Expected: PASS.

Commit:

```bash
git add frontend/src/components/NetworkMap.tsx frontend/src/App.tsx frontend/src/styles.css frontend/tests/App.test.tsx
git commit -m "feat: animate ripple network map"
```

---

### Task 4: End-To-End Verification And Frontend Docs

**Files:**
- Create: `e2e/dashboard.spec.ts`
- Modify: `README.md`
- Modify: `package.json`

**Interfaces:**
- Produces Playwright test verifying the dashboard opens and shock replay is usable.
- Produces local workflow docs for API plus frontend.

- [ ] **Step 1: Add Playwright test**

Create `e2e/dashboard.spec.ts`:

```ts
import { expect, test } from "@playwright/test";

test("dashboard opens on the map and runs a shock", async ({ page }) => {
  await page.goto("http://127.0.0.1:5173");

  await expect(page.getByText("AI Fragility Map")).toBeVisible();
  await expect(page.getByText("estimated impact under scenario")).toBeVisible();
  await page.getByRole("button", { name: "Run shock" }).click();
  await expect(page.getByLabel("AI supply-chain network map")).toBeVisible();
});
```

- [ ] **Step 2: Update README**

Replace `README.md`:

```markdown
# AI Fragility Map

AI Fragility Map is a data-first polished demo that shows estimated ripple effects from a cloud/platform AI infrastructure spending slowdown.

## Backend

```bash
make install
make refresh
make api
```

## Frontend

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Open `http://127.0.0.1:5173`.

## Test

```bash
make test
npm --prefix frontend run test -- --run
```

With the API and frontend running:

```bash
npm run e2e
```

## Product Guardrails

- The first screen is the working map.
- The ripple animation is the hero interaction.
- Outputs are estimated impact under scenario, not predictions.
- Confidence is evidence quality and is not multiplied into economic impact.
```

- [ ] **Step 3: Run verification**

Run:

```bash
npm --prefix frontend run test -- --run
```

Expected: PASS.

Run in one terminal:

```bash
uvicorn fragility_map.api.server:app --port 8000
```

Run in another terminal:

```bash
npm --prefix frontend run dev
```

Run in a third terminal:

```bash
npm run e2e
```

Expected: Playwright test passes.

- [ ] **Step 4: Commit**

```bash
git add e2e/dashboard.spec.ts README.md package.json
git commit -m "test: add frontend end-to-end verification"
```

---

## Frontend Self-Review

- Spec coverage: first-screen dashboard, ripple animation, compact controls, results panel, company panel, scenario language, and E2E test are covered.
- Scan result: plan contains concrete files, commands, interfaces, tests, and code blocks for code-changing steps.
- Type consistency: `GraphPayload`, `GraphNode`, `EdgePulse`, component props, and API response fields match the backend contract at the top of this plan.

## Execution Handoff

Frontend plan complete and saved to `docs/superpowers/plans/2026-07-18-ai-fragility-map-frontend.md`.
