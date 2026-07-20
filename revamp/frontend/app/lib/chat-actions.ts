export type ChatAction = {
  tool: string;
  args: unknown;
  result: unknown;
};

export type ChatScenarioTotals = {
  impact_total: number;
  exposure_total: number;
  unresolved_count: number;
};

export type ChatCompletedRun = {
  totals: ChatScenarioTotals;
  results: EdgeResult[];
};

type ChatScenarioCardBase = {
  scenarioId: string;
  name: string;
  originEntity: string;
  magnitude: number;
  unit: string | null;
};

export type ChatScenarioCardModel =
  | (ChatScenarioCardBase & { status: "ready" })
  | (ChatScenarioCardBase & {
      status: "complete";
      totals: ChatScenarioTotals;
      run: ChatCompletedRun;
    });

export function scenarioCardFromActions(actions: ChatAction[]): ChatScenarioCardModel | null {
  for (let index = 0; index < actions.length; index += 1) {
    const created = createdScenario(actions[index]);
    if (!created) continue;

    const run = actions.slice(index + 1).map(completedRun(created.name)).find(Boolean);
    return run
      ? { ...created, status: "complete", totals: run.totals, run }
      : { ...created, status: "ready" };
  }

  return null;
}

function createdScenario(action: ChatAction): ChatScenarioCardBase | null {
  if (action.tool !== "create_scenario" || !isRecord(action.result) || "error" in action.result) {
    return null;
  }

  const scenarioId = nonBlankString(action.result.scenario_id);
  const name = nonBlankString(action.result.name);
  const originEntity = nonBlankString(action.result.origin_entity);
  const magnitude = finiteNumber(action.result.magnitude);
  if (!scenarioId || !name || !originEntity || magnitude == null) return null;

  return { scenarioId, name, originEntity, magnitude, unit: scenarioUnit(action.args) };
}

function completedRun(scenarioName: string) {
  return (action: ChatAction): ChatCompletedRun | null => {
    if (
      action.tool !== "run_scenario" ||
      !isRecord(action.args) ||
      nonBlankString(action.args.name) !== scenarioName ||
      !isRecord(action.result) ||
      "error" in action.result ||
      !isRecord(action.result.totals) ||
      !Array.isArray(action.result.results)
    ) {
      return null;
    }

    const impactTotal = finiteNumber(action.result.totals.impact_total);
    const exposureTotal = finiteNumber(action.result.totals.exposure_total);
    const unresolvedCount = finiteNumber(action.result.totals.unresolved_count);
    if (
      impactTotal == null ||
      exposureTotal == null ||
      unresolvedCount == null ||
      !Number.isInteger(unresolvedCount) ||
      unresolvedCount < 0
    ) {
      return null;
    }

    const results = action.result.results.map(edgeResult).filter((result) => result !== null);
    if (results.length !== action.result.results.length) return null;

    const totals = {
      impact_total: impactTotal,
      exposure_total: exposureTotal,
      unresolved_count: unresolvedCount,
    };
    return { totals, results };
  };
}

function edgeResult(value: unknown): EdgeResult | null {
  if (!isRecord(value)) return null;
  const edgeId = nonBlankString(value.edge_id);
  const source = nonBlankString(value.source_entity);
  const target = nonBlankString(value.target_entity);
  const relationship = nonBlankString(value.relationship_type);
  const kind = value.kind;
  const label = stringValue(value.label);
  const caveat = stringValue(value.caveat);
  const evidenceClass = nonBlankString(value.evidence_class);
  const visualState = nonBlankString(value.visual_state);
  const resultValue = nullableFiniteNumber(value.value);
  const realizedLoss = nullableFiniteNumber(value.realized_loss);
  const unit = nullableString(value.unit);
  if (
    !edgeId || !source || !target || !relationship ||
    (kind !== "impact" && kind !== "exposure" && kind !== "unresolved") ||
    label == null || caveat == null || !evidenceClass || !visualState ||
    resultValue === undefined || realizedLoss === undefined || unit === undefined
  ) return null;

  return {
    edge_id: edgeId,
    source_entity: source,
    target_entity: target,
    relationship_type: relationship,
    kind,
    value: resultValue,
    unit,
    label,
    caveat,
    realized_loss: realizedLoss,
    evidence_class: evidenceClass,
    visual_state: visualState,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function scenarioUnit(args: unknown): string | null {
  if (!isRecord(args)) return null;
  if (!Object.hasOwn(args, "unit")) return "usd_billions";
  return nonBlankString(args.unit);
}

function nonBlankString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function finiteNumber(value: unknown): number | null {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

function nullableFiniteNumber(value: unknown): number | null | undefined {
  return value === null ? null : finiteNumber(value) ?? undefined;
}

function nullableString(value: unknown): string | null | undefined {
  return value === null ? null : stringValue(value) ?? undefined;
}

function stringValue(value: unknown): string | null {
  return typeof value === "string" ? value : null;
}
import type { EdgeResult } from "./api";
