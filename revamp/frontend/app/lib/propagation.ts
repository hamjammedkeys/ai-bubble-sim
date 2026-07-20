import type { EdgeResult } from "./api";
import { orderedResultIds } from "./dashboard";

export type PropagationFrame = {
  edgeId: string;
  kind: EdgeResult["kind"];
  delayMs: number;
};

export type PropagationDecision = {
  immediateEdgeIds: string[];
  scheduledFrames: readonly PropagationFrame[];
};

export function propagationFrames(results: EdgeResult[]): PropagationFrame[] {
  const resultsById = new Map(results.map((result) => [result.edge_id, result]));

  return orderedResultIds(results).map((edgeId, index) => ({
    edgeId,
    kind: resultsById.get(edgeId)!.kind,
    delayMs: index * 700,
  }));
}

export function propagationDecision(
  frames: readonly PropagationFrame[],
  prefersReducedMotion: boolean,
): PropagationDecision {
  return prefersReducedMotion
    ? {
        immediateEdgeIds: frames.map((frame) => frame.edgeId),
        scheduledFrames: [],
      }
    : { immediateEdgeIds: [], scheduledFrames: frames };
}

export function isPropagationComplete(
  resultIds: string[],
  revealedResultIds: ReadonlySet<string>,
): boolean {
  return resultIds.every((resultId) => revealedResultIds.has(resultId));
}
