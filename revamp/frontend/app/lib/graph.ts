import dagre from "@dagrejs/dagre";
import type { Edge as ApiEdge, EdgeResult, Entity } from "./api";

export const NODE_W = 184;
export const NODE_H = 60;

export function reactFlowNodeDimensions() {
  return { width: NODE_W, height: NODE_H };
}

export type VisualState = "grey" | "impact" | "exposure" | "amber" | "candidate";
export type GraphFilters = Record<VisualState, boolean>;
export type GraphLayerVisibility = {
  impact: boolean;
  exposure: boolean;
  unresolved: boolean;
  candidate: boolean;
  inactive: boolean;
};

export type GraphFocus = { edgeIds: Set<string>; nodeIds: Set<string> };

export function graphFocusFor(
  edges: ApiEdge[],
  edgeId: string | null,
  entityId: string | null,
): GraphFocus | null {
  if (edgeId) {
    const edge = edges.find((candidate) => candidate.id === edgeId);
    if (!edge) return null;
    return {
      edgeIds: new Set([edge.id]),
      nodeIds: new Set(
        [edge.source_entity_id, edge.target_entity_id].filter(
          (id): id is string => id !== null,
        ),
      ),
    };
  }

  if (!entityId) return null;
  const localEdges = edges.filter(
    (edge) => edge.source_entity_id === entityId || edge.target_entity_id === entityId,
  );
  return {
    edgeIds: new Set(localEdges.map((edge) => edge.id)),
    nodeIds: new Set([
      entityId,
      ...localEdges.flatMap((edge) =>
        [edge.source_entity_id, edge.target_entity_id].filter(
          (id): id is string => id !== null,
        ),
      ),
    ]),
  };
}

export function edgeVisible(visualState: VisualState, filters: GraphFilters): boolean {
  return filters[visualState];
}

export function graphFiltersForLayers(layers: GraphLayerVisibility): GraphFilters {
  return {
    impact: layers.impact,
    exposure: layers.exposure,
    amber: layers.unresolved,
    candidate: layers.candidate,
    grey: layers.inactive,
  };
}

// Map a scenario result's visual_state, or an at-rest edge, to our grammar.
export function visualStateFor(edge: ApiEdge, result?: EdgeResult): VisualState {
  if (edge.status === "candidate") return "candidate";
  if (!result) return "grey"; // approved but not activated by the current scenario
  switch (result.visual_state) {
    case "solid_red":
      return "impact";
    case "solid_orange":
      return "exposure";
    case "dashed_amber":
      return "amber";
    default:
      return "grey";
  }
}

export type GraphEdgeGroup = {
  id: string;
  source: string;
  target: string;
  edges: ApiEdge[];
  representative: ApiEdge;
  visualState: VisualState;
  visible: boolean;
};

const VISUAL_PRIORITY: Record<VisualState, number> = {
  impact: 5,
  exposure: 4,
  amber: 3,
  candidate: 2,
  grey: 1,
};

export function groupGraphEdges(
  edges: ApiEdge[],
  results: Record<string, EdgeResult>,
  filters?: GraphFilters,
): GraphEdgeGroup[] {
  const groups = new Map<string, GraphEdgeGroup>();

  for (const edge of edges) {
    if (!edge.source_entity_id || !edge.target_entity_id) continue;

    const source = edge.source_entity_id;
    const target = edge.target_entity_id;
    const id = `${source}->${target}`;
    const visualState = visualStateFor(edge, results[edge.id]);
    const group = groups.get(id);

    if (!group) {
      groups.set(id, {
        id,
        source,
        target,
        edges: [edge],
        representative: edge,
        visualState,
        visible: true,
      });
      continue;
    }

    group.edges.push(edge);
    if (VISUAL_PRIORITY[visualState] > VISUAL_PRIORITY[group.visualState]) {
      group.representative = edge;
      group.visualState = visualState;
    }
  }

  if (filters) {
    for (const group of groups.values()) {
      const visibleMembers = group.edges
        .map((edge) => ({ edge, visualState: visualStateFor(edge, results[edge.id]) }))
        .filter((member) => edgeVisible(member.visualState, filters));
      group.visible = visibleMembers.length > 0;
      for (const member of visibleMembers) {
        if (
          !edgeVisible(group.visualState, filters) ||
          VISUAL_PRIORITY[member.visualState] > VISUAL_PRIORITY[group.visualState]
        ) {
          group.representative = member.edge;
          group.visualState = member.visualState;
        }
      }
    }
  }

  return [...groups.values()];
}

export const STROKE: Record<VisualState, string> = {
  grey: "#3a424e",
  impact: "#e5484d",
  exposure: "#f5a623",
  amber: "#c99a3b",
  candidate: "#4c8dff",
};

export function edgeClassName(v: VisualState): string {
  if (v === "candidate") return "edge-candidate";
  if (v === "amber") return "edge-amber";
  return "";
}

export function edgeWidth(v: VisualState): number {
  return v === "impact" || v === "exposure" ? 3 : v === "grey" ? 1.5 : 2;
}

// Layered left-to-right layout so the graph reads as an exposure chain
// (investor → model → cloud → gpu → foundry → equipment).
export function layout(
  entities: Entity[],
  edges: ApiEdge[],
): Record<string, { x: number; y: number }> {
  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: "LR", nodesep: 90, ranksep: 220, marginx: 40, marginy: 40, ranker: "network-simplex" });

  for (const e of entities) g.setNode(e.id, { width: NODE_W, height: NODE_H });
  for (const edge of edges) {
    if (edge.source_entity_id && edge.target_entity_id) {
      g.setEdge(edge.source_entity_id, edge.target_entity_id);
    }
  }
  dagre.layout(g);

  const pos: Record<string, { x: number; y: number }> = {};
  for (const e of entities) {
    const n = g.node(e.id);
    if (n) pos[e.id] = { x: n.x - NODE_W / 2, y: n.y - NODE_H / 2 };
  }
  return pos;
}

export const ENTITY_LABEL: Record<string, string> = {
  investor: "Investor",
  model_company: "AI model",
  cloud_provider: "Cloud / data-center",
  gpu_maker: "GPU / semiconductor",
  foundry: "Foundry",
  equipment_maker: "Equipment",
  application_company: "Application",
};
