import type {
  CompoundCreditEventRequest,
  EvidencePayload,
  ReviewAction,
  ReviewDecisionBody,
  ReviewEditBody
} from "./types";

async function readEvidence(response: Response, message: string): Promise<EvidencePayload> {
  if (!response.ok) {
    throw new Error(`${message}: ${response.status}`);
  }
  return response.json() as Promise<EvidencePayload>;
}

export async function runCompoundCreditEvent(
  request: CompoundCreditEventRequest
): Promise<EvidencePayload> {
  const response = await fetch("/api/v2/scenario/compound-credit-event", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      incremental_gaap_loss: request.incrementalGaapLoss,
      credit_status: request.creditStatus,
      default_status: request.defaultStatus
    })
  });
  return readEvidence(response, "Compound credit event request failed");
}

export async function listReviewCandidates(): Promise<EvidencePayload> {
  return readEvidence(
    await fetch("/api/v2/review/candidates"),
    "Review candidates request failed"
  );
}

export async function submitReviewDecision(
  candidateId: string,
  action: ReviewAction,
  body: ReviewDecisionBody
): Promise<EvidencePayload> {
  const response = await fetch(`/api/v2/review/${candidateId}/${action}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reviewer_id: body.reviewerId, reason: body.reason })
  });
  return readEvidence(response, "Review decision request failed");
}

export async function submitReviewEdit(
  candidateId: string,
  body: ReviewEditBody
): Promise<EvidencePayload> {
  const candidate = body.candidate;
  const response = await fetch(`/api/v2/review/${candidateId}/edit`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      reviewer_id: body.reviewerId,
      reason: body.reason,
      candidate: {
        candidate_id: candidate.candidateId,
        source_id: candidate.sourceId,
        source_accession: candidate.sourceAccession,
        source_company_id: candidate.sourceCompanyId,
        target_company_id: candidate.targetCompanyId,
        relationship_type: candidate.relationshipType,
        quoted_text: candidate.quotedText,
        numeric_token: candidate.numericToken,
        value: candidate.value,
        unit: candidate.unit,
        period: candidate.period,
        supported_rule: candidate.supportedRule,
        unsupported_inference: candidate.unsupportedInference,
        status: candidate.status
      }
    })
  });
  return readEvidence(response, "Review edit request failed");
}
