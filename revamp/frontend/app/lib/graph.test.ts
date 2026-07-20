import { describe, expect, it } from "vitest";
import type { Edge, EdgeResult } from "./api";
import {
  graphFiltersForLayers,
  groupGraphEdges,
  NODE_H,
  NODE_W,
  reactFlowNodeDimensions,
} from "./graph";

describe("React Flow node dimensions", () => {
  it("pins the measured node size so hover updates do not hide nodes for remeasurement", () => {
    expect(reactFlowNodeDimensions()).toEqual({
      width: NODE_W,
      height: NODE_H,
      measured: { width: NODE_W, height: NODE_H },
    });
  });
});

describe("graph edge grouping", () => {
  it("groups directed company pairs and selects the highest-priority representative", () => {
    const edge = (id: string, source_entity_id: string, target_entity_id: string, status = "approved") =>
      ({ id, source_entity_id, target_entity_id, status }) as Edge;
    const candidateEdge = edge("candidate", "source", "target", "candidate");
    const exposureEdge = edge("exposure", "source", "target");
    const impactEdge = edge("impact", "source", "target");
    const reverseEdge = edge("reverse", "target", "source");

    const groups = groupGraphEdges(
      [candidateEdge, exposureEdge, impactEdge, reverseEdge],
      {
        exposure: { edge_id: "exposure", visual_state: "solid_orange" } as EdgeResult,
        impact: { edge_id: "impact", visual_state: "solid_red" } as EdgeResult,
      },
    );

    expect(groups).toHaveLength(2);
    expect(groups[0].edges.map((edge) => edge.id)).toEqual([
      "candidate",
      "exposure",
      "impact",
    ]);
    expect(groups[0].representative.id).toBe("impact");
    expect(groups[0].visualState).toBe("impact");
  });

  it("uses the highest-priority visible member for a mixed-state group", () => {
    const impactEdge = {
      id: "impact",
      source_entity_id: "source",
      target_entity_id: "target",
      status: "approved",
    } as Edge;
    const exposureEdge = {
      id: "exposure",
      source_entity_id: "source",
      target_entity_id: "target",
      status: "approved",
    } as Edge;
    const results = {
      impact: { edge_id: "impact", visual_state: "solid_red" } as EdgeResult,
      exposure: { edge_id: "exposure", visual_state: "solid_orange" } as EdgeResult,
    };
    const layers = {
      unresolved: false,
      candidate: false,
      inactive: false,
    };

    const exposureOnly = groupGraphEdges(
      [impactEdge, exposureEdge],
      results,
      graphFiltersForLayers({ ...layers, impact: false, exposure: true }),
    )[0];
    const impactOnly = groupGraphEdges(
      [impactEdge, exposureEdge],
      results,
      graphFiltersForLayers({ ...layers, impact: true, exposure: false }),
    )[0];

    expect(exposureOnly.visible).toBe(true);
    expect(exposureOnly.representative.id).toBe("exposure");
    expect(exposureOnly.visualState).toBe("exposure");
    expect(impactOnly.visible).toBe(true);
    expect(impactOnly.representative.id).toBe("impact");
    expect(impactOnly.visualState).toBe("impact");
  });
});
