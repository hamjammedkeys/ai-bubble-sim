import { useCallback, useEffect, useRef, useState } from "react";
import { runCloudSlowdown } from "./api";
import { CompanyPanel } from "./components/CompanyPanel";
import { NetworkMap } from "./components/NetworkMap";
import { ResultsPanel } from "./components/ResultsPanel";
import { ReviewPanel } from "./components/ReviewPanel";
import { ScenarioControls } from "./components/ScenarioControls";
import type { GraphNode, GraphPayload } from "./types";

export const SCENARIO_LANGUAGE = "estimated impact under scenario" as const;

const initialGraph: GraphPayload = {
  nodes: [],
  edges: [],
  pulses: [],
  summary: {
    scenarioLanguage: SCENARIO_LANGUAGE,
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
  const requestSequence = useRef(0);

  const runScenario = useCallback(async () => {
    const requestId = ++requestSequence.current;
    setError(null);
    try {
      const payload = await runCloudSlowdown({
        shock_percentage: shock,
        pass_through_rate: 0.8,
        propagation_factor: 0.5,
        max_rounds: 3
      });
      if (requestId !== requestSequence.current) return;
      const safePayload: GraphPayload = {
        ...payload,
        summary: { ...payload.summary, scenarioLanguage: SCENARIO_LANGUAGE }
      };
      setGraph(safePayload);
      setSelectedNode((selected) =>
        selected
          ? safePayload.nodes.find((node) => node.data.id === selected.data.id) ?? null
          : null
      );
      setReplayToken((value) => value + 1);
    } catch {
      if (requestId !== requestSequence.current) return;
      setGraph(initialGraph);
      setSelectedNode(null);
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
        <span>{SCENARIO_LANGUAGE}</span>
      </header>
      <section className="workspace">
        <aside className="left-rail">
          <ScenarioControls shock={shock} onShockChange={setShock} onRun={runScenario} />
          {error && <p className="api-error" role="alert">{error}</p>}
          <ResultsPanel graph={graph} />
          <ReviewPanel onDecision={() => void runScenario()} />
        </aside>
        <NetworkMap graph={graph} replayToken={replayToken} onSelectNode={setSelectedNode} />
        <aside className="right-rail">
          <CompanyPanel nodes={graph.nodes} node={selectedNode} onSelectNode={setSelectedNode} />
        </aside>
      </section>
    </main>
  );
}
