import { describe, expect, it } from "vitest";
import { scenarioCardFromActions, type ChatAction } from "./chat-actions";

const createAction: ChatAction = {
  tool: "create_scenario",
  args: {
    name: "OpenAI shock",
    origin_entity: "OpenAI",
    magnitude: 10,
    unit: "usd_billions",
  },
  result: {
    scenario_id: "scenario-1",
    name: "OpenAI shock",
    origin_entity: "OpenAI",
    magnitude: 10,
  },
};

const runAction: ChatAction = {
  tool: "run_scenario",
  args: { name: "OpenAI shock" },
  result: {
    totals: {
      impact_total: 2.7,
      exposure_total: 36.8,
      unresolved_count: 3,
    },
    results: [{
      edge_id: "edge-1",
      source_entity: "OpenAI",
      target_entity: "Microsoft",
      relationship_type: "investment",
      kind: "impact",
      value: 2.7,
      unit: "usd_billions",
      label: "Accounting impact",
      caveat: "",
      realized_loss: 2.7,
      evidence_class: "reported",
      visual_state: "impact",
    }],
  },
};

describe("scenarioCardFromActions", () => {
  it("returns a ready card for a successful create action", () => {
    expect(scenarioCardFromActions([createAction])).toEqual({
      scenarioId: "scenario-1",
      status: "ready",
      name: "OpenAI shock",
      originEntity: "OpenAI",
      magnitude: 10,
      unit: "usd_billions",
    });
  });

  it("uses the backend usd_billions default when create args omit unit", () => {
    const action = {
      ...createAction,
      args: {
        name: "OpenAI shock",
        origin_entity: "OpenAI",
        magnitude: 10,
      },
    };

    expect(scenarioCardFromActions([action])).toMatchObject({ unit: "usd_billions" });
  });

  it("preserves an explicit nonblank create unit exactly", () => {
    const action = {
      ...createAction,
      args: { ...(createAction.args as Record<string, unknown>), unit: " custom_units " },
    };

    expect(scenarioCardFromActions([action])).toMatchObject({ unit: " custom_units " });
  });

  it("returns a complete card for a successful same-name run", () => {
    expect(scenarioCardFromActions([createAction, runAction])).toEqual({
      scenarioId: "scenario-1",
      status: "complete",
      name: "OpenAI shock",
      originEntity: "OpenAI",
      magnitude: 10,
      unit: "usd_billions",
      totals: {
        impact_total: 2.7,
        exposure_total: 36.8,
        unresolved_count: 3,
      },
      run: {
        totals: {
          impact_total: 2.7,
          exposure_total: 36.8,
          unresolved_count: 3,
        },
        results: expect.arrayContaining([expect.objectContaining({ edge_id: "edge-1", kind: "impact" })]),
      },
    });
  });

  it("keeps the card ready when a run graph result is malformed", () => {
    const malformed = {
      ...runAction,
      result: {
        ...(runAction.result as Record<string, unknown>),
        results: [{ edge_id: "edge-1", kind: "impact" }],
      },
    };

    expect(scenarioCardFromActions([createAction, malformed])).toMatchObject({ status: "ready" });
  });

  it("ignores malformed create results", () => {
    const validResult = createAction.result as Record<string, unknown>;

    for (const result of [
      null,
      { ...validResult, scenario_id: "" },
      { ...validResult, name: null },
      { ...validResult, origin_entity: 42 },
      { ...validResult, magnitude: Number.NaN },
    ]) {
      expect(scenarioCardFromActions([{ ...createAction, result }])).toBeNull();
    }
  });

  it("ignores create tool errors", () => {
    expect(
      scenarioCardFromActions([
        { ...createAction, result: { error: "scenario creation failed" } },
      ]),
    ).toBeNull();
  });

  it("keeps the card ready when run results are malformed or for another scenario", () => {
    const malformedRun = {
      ...runAction,
      result: {
        totals: {
          impact_total: 2.7,
          exposure_total: "36.8",
          unresolved_count: 3,
        },
      },
    };
    const otherRun = { ...runAction, args: { name: "Different scenario" } };

    expect(scenarioCardFromActions([createAction, malformedRun])).toMatchObject({ status: "ready" });
    expect(scenarioCardFromActions([createAction, otherRun])).toMatchObject({ status: "ready" });
  });

  it("does not associate scenario names that differ only by whitespace", () => {
    const spacedCreate = {
      ...createAction,
      result: { ...(createAction.result as Record<string, unknown>), name: "OpenAI shock " },
    };

    expect(scenarioCardFromActions([spacedCreate, runAction])).toMatchObject({
      status: "ready",
      name: "OpenAI shock ",
    });
  });

  it("requires unresolved totals to be nonnegative integers", () => {
    for (const unresolvedCount of [-1, 1.5]) {
      const invalidRun = {
        ...runAction,
        result: {
          totals: {
            impact_total: 2.7,
            exposure_total: 36.8,
            unresolved_count: unresolvedCount,
          },
        },
      };

      expect(scenarioCardFromActions([createAction, invalidRun])).toMatchObject({ status: "ready" });
    }
  });

  it("keeps the card ready when the run tool returns an error", () => {
    expect(
      scenarioCardFromActions([
        createAction,
        { ...runAction, result: { error: "scenario run failed" } },
      ]),
    ).toMatchObject({ status: "ready" });
  });

  it("ignores unrelated actions", () => {
    expect(
      scenarioCardFromActions([
        { tool: "graph_summary", args: {}, result: { companies: [] } },
      ]),
    ).toBeNull();
  });
});
