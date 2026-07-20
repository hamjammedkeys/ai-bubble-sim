import type { Edge, EdgeResult, Entity, Scenario, ScenarioRun } from "./api";

export type DeskMetrics = {
  entityCount: number;
  approvedEdgeCount: number;
  candidateCount: number;
  impactTotal: number | null;
  exposureTotal: number | null;
  unresolvedCount: number | null;
  evidenceCoverage: number | null;
};

export type DeskRunSnapshot = {
  scenarioId: string;
  results: Record<string, EdgeResult>;
  totals: ScenarioRun["totals"];
};

export function toDeskRunSnapshot(run: ScenarioRun): DeskRunSnapshot {
  return {
    scenarioId: run.scenario_id,
    results: Object.fromEntries(run.results.map((result) => [result.edge_id, result])),
    totals: run.totals,
  };
}

export function identifiableHopCount(results: EdgeResult[]): number {
  return results.filter(
    (result) =>
      (result.kind === "impact" || result.kind === "exposure") && result.value != null,
  ).length;
}

export function deskScenarioId(
  selectedScenarioId: string | null,
  run: Pick<DeskRunSnapshot, "scenarioId"> | null,
): string | null {
  return run?.scenarioId ?? selectedScenarioId;
}

export function selectedScenarioAfterCreate(
  currentScenarioId: string | null,
  createdScenarioId: string,
  mutationLocked: boolean,
): string | null {
  return mutationLocked ? currentScenarioId : createdScenarioId;
}

export function scenarioOriginEntityId(
  scenario: Scenario | null,
  entities: Entity[],
  edges: Edge[],
  firstResultEdgeId?: string,
): string | null {
  const origin = scenario?.origin_entity?.trim().toLocaleLowerCase();
  if (origin) {
    return entities.find((entity) =>
      entity.id.toLocaleLowerCase() === origin ||
      entity.name.trim().toLocaleLowerCase() === origin ||
      entity.aliases?.some((alias) => alias.trim().toLocaleLowerCase() === origin),
    )?.id ?? null;
  }

  // Compatibility with older API responses that predate origin_entity.
  return edges.find((edge) => edge.id === firstResultEdgeId)?.source_entity_id ?? null;
}

export function evidenceCoverage(edges: Edge[]): number | null {
  const visibleEdges = edges.filter(
    (edge) => edge.status === "approved" || edge.status === "candidate",
  );

  if (visibleEdges.length === 0) return null;

  const passingEdges = visibleEdges.filter((edge) => edge.verification?.overall === "pass");
  if (passingEdges.length === visibleEdges.length) return 100;
  return Math.floor((passingEdges.length / visibleEdges.length) * 1000) / 10;
}

export function deriveDeskMetrics(
  entities: Entity[],
  edges: Edge[],
  totals: ScenarioRun["totals"] | null,
): DeskMetrics {
  return {
    entityCount: entities.length,
    approvedEdgeCount: edges.filter((edge) => edge.status === "approved").length,
    candidateCount: edges.filter((edge) => edge.status === "candidate").length,
    impactTotal: totals?.impact_total ?? null,
    exposureTotal: totals?.exposure_total ?? null,
    unresolvedCount: totals?.unresolved_count ?? null,
    evidenceCoverage: evidenceCoverage(edges),
  };
}

export function orderedResultIds(results: EdgeResult[]): string[] {
  const kindOrder = { impact: 0, exposure: 1, unresolved: 2 };
  return results
    .map((result, index) => ({ result, index }))
    .sort((a, b) => kindOrder[a.result.kind] - kindOrder[b.result.kind] || a.index - b.index)
    .map(({ result }) => result.edge_id);
}
