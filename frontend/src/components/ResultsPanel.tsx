import type { EvidencePayload, ReviewAction } from "../types";
import { reviewVisualState } from "../types";

interface Props {
  evidence: EvidencePayload;
  onReviewDecision: (candidateId: string, action: ReviewAction) => void;
  reviewBusy: boolean;
}

function formatMillions(value: number): string {
  const prefix = value < 0 ? "-$" : "$";
  return `${prefix}${Math.round(Math.abs(value) / 1_000_000).toLocaleString()}M`;
}

export function ResultsPanel({ evidence, onReviewDecision, reviewBusy }: Props) {
  const impacts = evidence.edges.filter((edge) => edge.resultKind === "impact" && edge.value !== null);
  const exposures = evidence.edges.filter((edge) => edge.resultKind === "exposure" && edge.value !== null);
  const guardrails = evidence.edges.filter((edge) => edge.tier === "dashed_amber");
  const dissolves = evidence.edges.filter((edge) => edge.tier === "diffuse_amber");

  return (
    <section className="panel results-panel">
      <h2>Evidence Results</h2>
      <p className="scenario-language">{evidence.scenario.language}</p>
      <dl>
        {impacts.map((edge) => (
          <div className="evidence-result impact" key={edge.relationshipId}>
            <dt>Calculated Impact</dt>
            <dd>{formatMillions(edge.value!)}</dd>
          </div>
        ))}
        {exposures.map((edge) => (
          <div className="evidence-result exposure" key={edge.relationshipId}>
            <dt>Activated Exposure</dt>
            <dd>{formatMillions(edge.value!)}</dd>
          </div>
        ))}
        {guardrails.map((edge) => (
          <div className="evidence-result guardrail" key={edge.relationshipId}>
            <dt>Realized loss: not identifiable</dt>
            <dd>{edge.basis}</dd>
          </div>
        ))}
        {dissolves.map((edge) => (
          <div className="evidence-result dissolve" key={edge.relationshipId}>
            <dt>Behavioural dissolve</dt>
            <dd>{edge.basis}</dd>
          </div>
        ))}
      </dl>
      {evidence.reviewCandidates.map((candidate) => (
        <article
          className={`review-candidate ${reviewVisualState(candidate)}`}
          key={candidate.candidateId}
        >
          <p>Pending human review</p>
          <small>{candidate.quotedText}</small>
          <div className="review-actions">
            <button
              type="button"
              onClick={() => onReviewDecision(candidate.candidateId, "approve")}
              disabled={reviewBusy}
            >
              Approve candidate
            </button>
            <button
              type="button"
              onClick={() => onReviewDecision(candidate.candidateId, "reject")}
              disabled={reviewBusy}
            >
              Reject candidate
            </button>
          </div>
        </article>
      ))}
    </section>
  );
}
