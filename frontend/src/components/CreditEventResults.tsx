import type { CreditEventEdge, CreditEventResult } from "../reviewApi";

function billions(value: number): string {
  return (Math.abs(value) / 1e9).toLocaleString(undefined, { maximumFractionDigits: 1 });
}

function describe(edge: CreditEventEdge): string {
  if (edge.value === null) return "not identifiable from evidence";
  if (edge.result_kind === "impact") return `impact -$${billions(edge.value)}B (forced loss)`;
  if (edge.result_kind === "exposure")
    return `exposure up to $${billions(edge.value)}B (not a realized loss)`;
  return edge.basis;
}

export function CreditEventResults({ result }: { result: CreditEventResult }) {
  if (result.edges.length === 0) return null;
  return (
    <section className="credit-event-results">
      <h2>OpenAI credit event</h2>
      <ul>
        {result.edges.map((edge) => (
          <li key={edge.relationship_id} className={`tier-${edge.tier}`}>
            <strong>
              {edge.source} → {edge.target}
            </strong>{" "}
            · {edge.basis} — {describe(edge)}
          </li>
        ))}
      </ul>
    </section>
  );
}
