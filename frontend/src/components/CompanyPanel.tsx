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
