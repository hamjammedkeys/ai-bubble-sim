import { useState } from "react";
import { approve, propose, reject, type CandidateView } from "../reviewApi";

const DEFAULT_FILING =
  "Microsoft accounted for 62% of our revenue in 2024. " +
  "OpenAI has committed to purchase $11.9 billion of compute capacity from CoreWeave " +
  "through 2030 to secure dedicated capacity.";

function Highlighted({ view }: { view: CandidateView }) {
  return <mark className="evidence-quote">{view.candidate.quoted_text}</mark>;
}

export function ReviewPanel({ onDecision }: { onDecision: () => void }) {
  const [filing, setFiling] = useState(DEFAULT_FILING);
  const [views, setViews] = useState<CandidateView[]>([]);

  async function analyze() {
    const body = await propose({
      source_id: "coreweave-s1a",
      source_accession: "0001640147-25-000001",
      source_company_id: "openai",
      target_company_id: "coreweave",
      filing_text: filing
    });
    setViews(body.candidates);
  }

  async function decide(view: CandidateView, ok: boolean) {
    const body = {
      candidate_id: view.candidate.candidate_id,
      reviewer_id: "judge",
      reason: ok ? "confirmed in the quoted passage" : "over-interpretation beyond the disclosure"
    };
    await (ok ? approve(body) : reject(body));
    setViews((current) =>
      current.map((v) =>
        v.candidate.candidate_id === view.candidate.candidate_id
          ? { ...v, candidate: { ...v.candidate, status: ok ? "approved" : "rejected" } }
          : v
      )
    );
    onDecision();
  }

  return (
    <section className="review-panel">
      <h2>Live filing extraction</h2>
      <textarea
        aria-label="filing text"
        value={filing}
        onChange={(e) => setFiling(e.target.value)}
        rows={5}
      />
      <button type="button" onClick={() => void analyze()}>
        Analyze filing
      </button>
      {views.map((view) => (
        <article className="candidate-card" key={view.candidate.candidate_id}>
          <p className="candidate-line">
            {view.candidate.source_company_id} → {view.candidate.target_company_id} ·{" "}
            {view.candidate.relationship_type} · <em>{view.candidate.status}</em>
          </p>
          <p className="candidate-quote">
            <Highlighted view={view} />
          </p>
          <ul className="check-list">
            {view.verification.checks.map((check) => (
              <li key={check.name} data-passed={check.passed}>
                {check.passed ? "✓" : "✗"} {check.name}
              </li>
            ))}
          </ul>
          <p className="semantic-pending">Semantic: pending human review</p>
          <div className="decision-row">
            <button type="button" onClick={() => void decide(view, true)}>
              Approve
            </button>
            <button type="button" onClick={() => void decide(view, false)}>
              Reject
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
