import { describe, expect, it } from "vitest";
import {
  deskScenarioId,
  deriveDeskMetrics,
  evidenceCoverage,
  identifiableHopCount,
  scenarioOriginEntityId,
  orderedResultIds,
  selectedScenarioAfterCreate,
  toDeskRunSnapshot,
} from "./dashboard";
import { edgeVisible, graphFiltersForLayers, graphFocusFor, type GraphFilters } from "./graph";

it("hides only disabled visual layers", () => {
  const filters: GraphFilters = {
    grey: true,
    impact: true,
    exposure: false,
    amber: true,
    candidate: true,
  };

  expect(edgeVisible("exposure", filters)).toBe(false);
  expect(edgeVisible("impact", filters)).toBe(true);
});

it("maps UI layer names to graph visual states without dropping a layer", () => {
  expect(
    graphFiltersForLayers({
      impact: false,
      exposure: true,
      unresolved: false,
      candidate: true,
      inactive: false,
    }),
  ).toEqual({
    impact: false,
    exposure: true,
    amber: false,
    candidate: true,
    grey: false,
  });
});

it("focuses a node and only its local relationships and counterparties", () => {
  const edges = [
    { id: "local", source_entity_id: "amazon", target_entity_id: "anthropic" },
    { id: "remote", source_entity_id: "microsoft", target_entity_id: "openai" },
  ] as never[];

  const focus = graphFocusFor(edges, null, "anthropic");

  expect([...focus!.edgeIds]).toEqual(["local"]);
  expect([...focus!.nodeIds]).toEqual(["anthropic", "amazon"]);
});

describe("deriveDeskMetrics", () => {
  it("keeps result-dependent metrics null before a scenario run", () => {
    expect(deriveDeskMetrics([], [], null)).toEqual({
      entityCount: 0,
      approvedEdgeCount: 0,
      candidateCount: 0,
      impactTotal: null,
      exposureTotal: null,
      unresolvedCount: null,
      evidenceCoverage: null,
    });
  });

  it("separates network counts from scenario totals", () => {
    const entities = [{ id: "amazon" }, { id: "anthropic" }] as never[];
    const edges = [
      { id: "approved", status: "approved", verification: { overall: "pass" } },
      { id: "candidate", status: "candidate", verification: { overall: "flag" } },
    ] as never[];
    const totals = { impact_total: 2.7, exposure_total: 8, unresolved_count: 3 };
    expect(deriveDeskMetrics(entities, edges, totals)).toMatchObject({
      entityCount: 2,
      approvedEdgeCount: 1,
      candidateCount: 1,
      impactTotal: 2.7,
      exposureTotal: 8,
      unresolvedCount: 3,
      evidenceCoverage: 50,
    });
  });
});

it("orders structural results before unresolved results", () => {
  const results = [
    { edge_id: "u", kind: "unresolved" },
    { edge_id: "e", kind: "exposure" },
    { edge_id: "i", kind: "impact" },
  ] as never[];
  expect(orderedResultIds(results)).toEqual(["i", "e", "u"]);
});

it("returns null coverage for an empty graph", () => {
  expect(evidenceCoverage([])).toBeNull();
});

it("binds scenario identity to the totals and results returned by that run", () => {
  const run = {
    scenario_id: "scenario-a",
    run_id: "run-a",
    results: [{ edge_id: "edge-a", kind: "impact" }],
    totals: { impact_total: 2.7, exposure_total: 8, unresolved_count: 1 },
  };

  expect(toDeskRunSnapshot(run as never)).toEqual({
    scenarioId: "scenario-a",
    results: { "edge-a": run.results[0] },
    totals: run.totals,
  });
});

it("counts only quantified impact and exposure results as identifiable hops", () => {
  const results = [
    { kind: "impact", value: 2.7 },
    { kind: "exposure", value: 0 },
    { kind: "impact", value: null },
    { kind: "unresolved", value: null },
  ] as never[];

  expect(identifiableHopCount(results)).toBe(2);
});

it("uses the run-bound scenario for displays once results exist", () => {
  expect(deskScenarioId("scenario-b", { scenarioId: "scenario-a" })).toBe("scenario-a");
  expect(deskScenarioId("scenario-b", null)).toBe("scenario-b");
});

it("does not round partial evidence coverage up to a complete pass", () => {
  const edges = Array.from({ length: 200 }, (_, index) => ({
    status: "approved",
    verification: { overall: index < 199 ? "pass" : "flag" },
  })) as never[];

  expect(evidenceCoverage(edges)).toBe(99.5);

  const nearlyComplete = Array.from({ length: 2_000 }, (_, index) => ({
    status: "approved",
    verification: { overall: index < 1_999 ? "pass" : "flag" },
  })) as never[];
  expect(evidenceCoverage(nearlyComplete)).toBeLessThan(100);
});

it("does not select a newly created scenario while scenario mutation is locked", () => {
  expect(selectedScenarioAfterCreate("scenario-a", "scenario-b", true)).toBe("scenario-a");
  expect(selectedScenarioAfterCreate("scenario-a", "scenario-b", false)).toBe("scenario-b");
});

it("resolves the scenario origin itself even when it is the first result target", () => {
  const scenario = { id: "scenario-a", origin_entity: "Anthropic" } as never;
  const entities = [
    { id: "amazon", name: "Amazon" },
    { id: "anthropic", name: "Anthropic" },
  ] as never[];
  const edges = [
    { id: "investment", source_entity_id: "amazon", target_entity_id: "anthropic" },
  ] as never[];

  expect(scenarioOriginEntityId(scenario, entities, edges, "investment")).toBe("anthropic");
});
