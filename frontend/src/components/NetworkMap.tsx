import cytoscape, { type Core } from "cytoscape";
import { useEffect, useRef } from "react";
import type { EvidenceNode, EvidencePayload } from "../types";

interface Props {
  evidence: EvidencePayload;
  replayToken: number;
  onSelectNode: (node: EvidenceNode | null) => void;
}

const stateColors: Record<string, string> = {
  quantified_impact: "#c9383a",
  exposure_detected: "#e06c24",
  not_identifiable: "#bf842a"
};

function graphElements(evidence: EvidencePayload) {
  const knownCompanies = new Set(evidence.nodes.map((node) => node.companyId));
  const inferredNodes = evidence.edges.flatMap((edge) => [edge.source, edge.target])
    .filter((companyId) => !knownCompanies.has(companyId));
  const nodes = [
    ...evidence.nodes.map((node) => ({
      data: {
        id: node.companyId,
        label: node.label,
        epistemicState: node.epistemicState
      }
    })),
    ...[...new Set(inferredNodes)].map((companyId) => ({
      data: { id: companyId, label: companyId, epistemicState: "source" }
    }))
  ];
  const edges = evidence.edges.map((edge) => ({
    data: {
      id: edge.relationshipId,
      source: edge.source,
      target: edge.target,
      tier: edge.tier
    },
    classes: `tier-${edge.tier}`
  }));
  const candidateEdges = evidence.reviewCandidates.map((candidate) => ({
    data: {
      id: `candidate-${candidate.candidateId}`,
      source: candidate.sourceCompanyId,
      target: candidate.targetCompanyId,
      tier: "blue_striped"
    },
    classes: "blue_striped"
  }));
  return [...nodes, ...edges, ...candidateEdges];
}

export function NetworkMap({ evidence, replayToken, onSelectNode }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const isTest = import.meta.env.MODE === "test";

  useEffect(() => {
    if (!containerRef.current) return;

    cyRef.current?.destroy();
    const cy = cytoscape({
      container: containerRef.current,
      headless: isTest,
      elements: graphElements(evidence),
      layout: isTest
        ? { name: "preset" }
        : { name: "breadthfirst", directed: true, spacingFactor: 1.35 },
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": (element) => stateColors[element.data("epistemicState")] ?? "#65758b",
            color: "#102033",
            "font-size": 11,
            "text-valign": "bottom",
            "text-margin-y": 8,
            width: 48,
            height: 48
          }
        },
        {
          selector: "edge",
          style: {
            width: 3,
            "line-color": "#91a3b7",
            "target-arrow-color": "#91a3b7",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.8
          }
        },
        {
          selector: ".tier-solid_red",
          style: { "line-color": "#c9383a", "target-arrow-color": "#c9383a" }
        },
        {
          selector: ".tier-solid_orange",
          style: { "line-color": "#e06c24", "target-arrow-color": "#e06c24" }
        },
        {
          selector: ".tier-dashed_amber",
          style: {
            "line-color": "#bf842a",
            "target-arrow-color": "#bf842a",
            "line-style": "dashed"
          }
        },
        {
          selector: ".tier-diffuse_amber",
          style: {
            "line-color": "#bf842a",
            "target-arrow-color": "#bf842a",
            "line-style": "dotted",
            opacity: 0.28
          }
        },
        {
          selector: ".blue_striped",
          style: {
            "line-color": "#2573b7",
            "target-arrow-color": "#2573b7",
            "line-style": "dashed",
            opacity: 0.85
          }
        }
      ]
    });

    cy.on("tap", "node", (event) => {
      const id = event.target.id();
      onSelectNode(evidence.nodes.find((node) => node.companyId === id) ?? null);
    });
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectNode(null);
    });
    cyRef.current = cy;

    return () => {
      cy.destroy();
      if (cyRef.current === cy) cyRef.current = null;
    };
  }, [evidence, onSelectNode, replayToken]);

  return <div className="network-map" ref={containerRef} aria-label="AI supply-chain network map" />;
}
