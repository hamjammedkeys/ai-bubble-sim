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
          <dd>
            ${Math.round(graph.summary.totalRevenueLost).toLocaleString()}M
            <span className="estimate-basis">inferred</span>
          </dd>
        </div>
        <div>
          <dt>Stressed companies</dt>
          <dd>{graph.summary.stressedCompanyCount}</dd>
        </div>
      </dl>
    </section>
  );
}
