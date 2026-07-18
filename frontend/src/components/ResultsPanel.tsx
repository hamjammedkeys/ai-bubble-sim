import { useState } from "react";
import type { EvidencePayload, ReviewAction, ReviewCandidate } from "../types";
import { reviewVisualState } from "../types";

interface Props {
  evidence: EvidencePayload;
  onReviewDecision: (candidateId: string, action: ReviewAction) => void;
  onReviewEdit: (candidate: ReviewCandidate) => void;
  reviewBusy: boolean;
}

function formatMillions(value: number): string {
  const prefix = value < 0 ? "-$" : "$";
  return `${prefix}${Math.round(Math.abs(value) / 1_000_000).toLocaleString()}M`;
}

export function ResultsPanel({
  evidence,
  onReviewDecision,
  onReviewEdit,
  reviewBusy
}: Props) {
  const [editingCandidateId, setEditingCandidateId] = useState<string | null>(null);
  const [editedQuote, setEditedQuote] = useState("");
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
          <p>
            {candidate.targetCompanyId === null
              ? "Unlinked candidate — target company unresolved"
              : "Pending human review"}
          </p>
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
            <button
              type="button"
              onClick={() => {
                setEditingCandidateId(candidate.candidateId);
                setEditedQuote(candidate.quotedText);
              }}
              disabled={reviewBusy}
            >
              Edit candidate
            </button>
          </div>
          {editingCandidateId === candidate.candidateId && (
            <form
              className="review-edit"
              onSubmit={(event) => {
                event.preventDefault();
                onReviewEdit({ ...candidate, quotedText: editedQuote });
              }}
            >
              <label>
                Candidate quote
                <textarea
                  value={editedQuote}
                  onChange={(event) => setEditedQuote(event.target.value)}
                  disabled={reviewBusy}
                />
              </label>
              <button type="submit" disabled={reviewBusy}>Submit edit</button>
            </form>
          )}
        </article>
      ))}
      {evidence.auditLog.length > 0 && (
        <section className="audit-log" aria-label="Audit log">
          <h3>Audit log</h3>
          <ul>
            {evidence.auditLog.map((entry) => (
              <li key={entry.auditId}>
                <strong>{entry.toStatus}</strong>: {entry.reason}
              </li>
            ))}
          </ul>
        </section>
      )}
    </section>
  );
}
