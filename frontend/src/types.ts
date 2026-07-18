export type StressStatus = "stable" | "exposed" | "stressed" | "critical";

export interface GraphNode {
  data: {
    id: string;
    label: string;
    sectorGroup: string;
    revenue: number;
    revenueLoss: number;
    stressStatus: StressStatus;
  };
}

export interface GraphEdge {
  data: {
    id: string;
    source: string;
    target: string;
    annualFlowBase: number;
    confidenceScore: number;
    estimateMethod: string;
  };
}

export interface EdgePulse {
  relationshipId: string;
  source: string;
  target: string;
  roundIndex: number;
  revenueLoss: number;
}

export interface GraphPayload {
  nodes: GraphNode[];
  edges: GraphEdge[];
  pulses: EdgePulse[];
  summary: {
    scenarioLanguage: "estimated impact under scenario";
    totalRevenueLost: number;
    stressedCompanyCount: number;
  };
}
