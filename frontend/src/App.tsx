import { useCallback, useEffect, useState } from "react";
import { runCloudSlowdown } from "./api";
import { CompanyPanel } from "./components/CompanyPanel";
import { NetworkMap } from "./components/NetworkMap";
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
  const [error, setError] = useState<string | null>(null);

  const runScenario = useCallback(async () => {
    setError(null);
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
      setError("Unable to load scenario results.");
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
          {error && <p className="api-error" role="alert">{error}</p>}
          <ResultsPanel graph={graph} />
        </aside>
        <NetworkMap graph={graph} replayToken={replayToken} onSelectNode={setSelectedNode} />
        <aside className="right-rail">
          <CompanyPanel node={selectedNode} />
        </aside>
      </section>
    </main>
  );
}
