export interface VerificationCheck {
  name: string;
  passed: boolean;
  detail: string;
}

export interface CandidateView {
  candidate: {
    candidate_id: string;
    relationship_type: string;
    source_company_id: string;
    target_company_id: string;
    quoted_text: string;
    status: string;
  };
  verification: {
    checks: VerificationCheck[];
    mechanically_valid: boolean;
    semantic_interpretation: string;
  };
  highlight: { start: number; end: number } | null;
}

async function postJson<T>(url: string, body: unknown): Promise<T> {
  const response = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body)
  });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function propose(req: {
  source_id: string;
  source_accession: string;
  source_company_id: string;
  target_company_id: string;
  filing_text: string;
}): Promise<{ candidates: CandidateView[] }> {
  return postJson("/api/extraction/propose", req);
}

export function approve(body: { candidate_id: string; reviewer_id: string; reason: string }) {
  return postJson("/api/extraction/approve", body);
}

export function reject(body: { candidate_id: string; reviewer_id: string; reason: string }) {
  return postJson("/api/extraction/reject", body);
}

export interface CreditEventEdge {
  relationship_id: string;
  source: string;
  target: string;
  tier: string;
  result_kind: string;
  value: number | null;
  basis: string;
}

export interface CreditEventResult {
  edges: CreditEventEdge[];
  nodes: Record<
    string,
    {
      quantified_impact: number | null;
      activated_exposure: number | null;
      epistemic_state: string;
    }
  >;
}

export function runCreditEvent(): Promise<CreditEventResult> {
  return postJson("/api/scenario/credit-event", {});
}
