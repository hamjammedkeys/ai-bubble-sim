import type { GraphNode } from "../types";

interface Props {
  nodes: GraphNode[];
  node: GraphNode | null;
  onSelectNode: (node: GraphNode | null) => void;
}

export function CompanyPanel({ nodes, node, onSelectNode }: Props) {
  const selector = (
    <label>
      Inspect company
      <select
        value={node?.data.id ?? ""}
        onChange={(event) => {
          const id = event.target.value;
          onSelectNode(nodes.find((candidate) => candidate.data.id === id) ?? null);
        }}
      >
        <option value="">None selected</option>
        {nodes.map((candidate) => (
          <option key={candidate.data.id} value={candidate.data.id}>{candidate.data.label}</option>
        ))}
      </select>
    </label>
  );

  if (!node) {
    return (
      <section className="panel">
        <h2>Company</h2>
        {selector}
        <p>Select a node to inspect estimated impact and source basis.</p>
      </section>
    );
  }

  return (
    <section className="panel">
      <h2>{node.data.label}</h2>
      {selector}
      <dl>
        <div>
          <dt>Status</dt>
          <dd>{node.data.stressStatus}</dd>
        </div>
        <div>
          <dt>Revenue loss</dt>
          <dd>
            ${Math.round(node.data.revenueLoss).toLocaleString()}M
            <span className="estimate-basis">inferred</span>
          </dd>
        </div>
      </dl>
      <p className="assumption">Estimate label and evidence snippets attach here as extraction coverage grows.</p>
    </section>
  );
}
