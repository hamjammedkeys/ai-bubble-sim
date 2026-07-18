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
