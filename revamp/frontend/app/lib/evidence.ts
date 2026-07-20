import type { Edge, EdgeDetail } from "./api";

export type EdgeDetailRequest = { edgeId: string; version: number };
export type EdgeDetailSelection = { selectedEdgeId: string | null; version: number };

export function shouldAcceptEdgeDetail(
  request: EdgeDetailRequest,
  current: EdgeDetailSelection,
): boolean {
  return request.version === current.version && request.edgeId === current.selectedEdgeId;
}

export function detailAfterReview(current: EdgeDetail | null, reviewed: Edge): EdgeDetail {
  return {
    ...(current?.id === reviewed.id
      ? current
      : {
          passage_text: null,
          document_title: null,
          document_url: null,
        }),
    ...reviewed,
  };
}

export type EvidenceDeskMode = "evidence" | "company" | "results" | "queue";

export function isGraphActivationKey(key: string): boolean {
  return key === "Enter" || key === " ";
}

export function dataRequestErrorMessage(error: string): string {
  return `Data request failed. Previously loaded data remains available where possible. (${error})`;
}

export function evidenceDeskMode(input: {
  edge: boolean;
  company: boolean;
  result: boolean;
}): EvidenceDeskMode {
  if (input.edge) return "evidence";
  if (input.company) return "company";
  if (input.result) return "results";
  return "queue";
}

export type VerificationState = "pass" | "flag" | "neutral" | "unavailable";
export type VerificationRow = {
  key: string;
  label: string;
  display: string;
  state: VerificationState;
};

const VERIFICATION_CHECKS: Array<{ key: string; label: string }> = [
  { key: "passage_found", label: "Passage found" },
  { key: "match_score", label: "Passage match" },
  { key: "number_found", label: "Number found" },
  { key: "entities_found", label: "Entities found" },
  { key: "unit_allowed", label: "Unit allowed" },
  { key: "arithmetic_ok", label: "Arithmetic re-derived" },
  { key: "source_valid", label: "Source valid" },
];

export function verificationOverall(
  verification: Record<string, unknown>,
): Extract<VerificationState, "pass" | "flag" | "unavailable"> {
  if (verification.overall === "pass") return "pass";
  if (verification.overall === "flag") return "flag";
  return "unavailable";
}

export function verificationRows(verification: Record<string, unknown>): VerificationRow[] {
  return VERIFICATION_CHECKS.map(({ key, label }) => {
    const value = verification[key];
    if (value === true) return { key, label, display: "PASS", state: "pass" };
    if (value === false) return { key, label, display: "FLAG", state: "flag" };
    if (typeof value === "number") {
      return { key, label, display: `${value.toFixed(1)}%`, state: "neutral" };
    }
    return { key, label, display: "UNAVAILABLE", state: "unavailable" };
  });
}
