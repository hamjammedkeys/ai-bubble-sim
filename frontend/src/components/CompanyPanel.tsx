import type { EvidenceNode } from "../types";

interface Props {
  nodes: EvidenceNode[];
  node: EvidenceNode | null;
  onSelectNode: (node: EvidenceNode | null) => void;
}

function formatMillions(value: number): string {
  const prefix = value < 0 ? "-$" : "$";
  return `${prefix}${Math.round(Math.abs(value) / 1_000_000).toLocaleString()}M`;
}

export function CompanyPanel({ nodes, node, onSelectNode }: Props) {
  const selector = (
    <label>
      Inspect company
      <select
        value={node?.companyId ?? ""}
        onChange={(event) => {
          const id = event.target.value;
          onSelectNode(nodes.find((candidate) => candidate.companyId === id) ?? null);
        }}
      >
        <option value="">None selected</option>
        {nodes.map((candidate) => (
          <option key={candidate.companyId} value={candidate.companyId}>{candidate.label}</option>
        ))}
      </select>
    </label>
  );

  if (!node) {
    return (
      <section className="panel">
        <h2>Company</h2>
        {selector}
        <p>Select a node to inspect its epistemic state and evidence basis.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>{node.label}</h2>
      {selector}
      <dl>
        <div>
          <dt>Epistemic state</dt>
          <dd>{node.epistemicState}</dd>
        </div>
        {node.quantifiedImpact !== null && (
          <div>
            <dt>Calculated Impact</dt>
            <dd>{formatMillions(node.quantifiedImpact)}</dd>
          </div>
        )}
        {node.activatedExposure !== null && (
          <div>
            <dt>Activated Exposure</dt>
            <dd>{formatMillions(node.activatedExposure)}</dd>
          </div>
        )}
        {node.rankingEligible && (
          <div className="ranking-control">
            <dt>Ranking</dt>
            <dd>Eligible for quantified-impact ranking</dd>
          </div>
        )}
      </dl>
    </section>
  );
}
