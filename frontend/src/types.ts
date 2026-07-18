export type EvidenceTier = "solid_red" | "solid_orange" | "dashed_amber" | "diffuse_amber";
export type ReviewVisualState = "verified" | "blue_striped";
export type ReviewAction = "approve" | "reject";

export interface EvidenceNode {
  companyId: string;
  label: string;
  quantifiedImpact: number | null;
  activatedExposure: number | null;
  epistemicState: string;
  rankingEligible: boolean;
  tierSummary: EvidenceTier[];
}

export interface EvidenceEdge {
  relationshipId: string;
  source: string;
  target: string;
  structureType: string;
  tier: EvidenceTier;
  resultKind: string;
  value: number | null;
  basis: string;
  provenance: Record<string, string>;
  sourceAccession: string | null;
}

export interface ReviewCandidate {
  candidateId: string;
  sourceId: string;
  sourceAccession: string;
  sourceCompanyId: string;
  targetCompanyId: string;
  relationshipType: string;
  quotedText: string;
  numericToken: string | null;
  value: number | null;
  unit: string | null;
  period: string | null;
  supportedRule: string;
  unsupportedInference: string;
  status: string;
  verificationChecks?: Array<{ name: string; passed: boolean; detail: string }>;
  mechanicallyValid?: boolean;
}

export interface AuditEntry {
  auditId: string;
  candidateId: string;
  fromStatus: string;
  toStatus: string;
  reviewerId: string;
  reason: string;
  verificationValid: boolean;
  createdAt: string;
}

export interface EvidencePayload {
  scenario: {
    incrementalGaapLoss: number | null;
    creditStatus: string | null;
    defaultStatus: string | null;
    language: string;
  };
  nodes: EvidenceNode[];
  edges: EvidenceEdge[];
  reviewCandidates: ReviewCandidate[];
  auditLog: AuditEntry[];
  ranking: Array<{ companyId: string; magnitude: number }>;
}

export interface CompoundCreditEventRequest {
  incrementalGaapLoss: number;
  creditStatus: "normal" | "severe_distress";
  defaultStatus: "not_defaulted" | "defaulted";
}

export interface ReviewDecisionBody {
  reviewerId: string;
  reason: string;
}

export function reviewVisualState(candidate: ReviewCandidate): ReviewVisualState {
  return candidate.status === "approved" ? "verified" : "blue_striped";
}
