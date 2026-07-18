import cytoscape, { type Core, type NodeSingular } from "cytoscape";
import { useEffect, useRef } from "react";
import type { GraphNode, GraphPayload } from "../types";

interface Props {
  graph: GraphPayload;
  replayToken: number;
  onSelectNode: (node: GraphNode | null) => void;
}

const statusColors: Record<string, string> = {
  stable: "#2f7d59",
  exposed: "#e0a423",
  stressed: "#d66a2a",
  critical: "#b72d3a"
};

export function NetworkMap({ graph, replayToken, onSelectNode }: Props) {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const cyRef = useRef<Core | null>(null);
  const isTest = import.meta.env.MODE === "test";

  useEffect(() => {
    if (!containerRef.current) return;

    cyRef.current?.destroy();
    const cy = cytoscape({
      container: containerRef.current,
      headless: isTest,
      elements: [...graph.nodes, ...graph.edges],
      layout: isTest
        ? { name: "preset" }
        : { name: "breadthfirst", directed: true, spacingFactor: 1.35 },
      style: [
        {
          selector: "node",
          style: {
            label: "data(label)",
            "background-color": (element) => statusColors[element.data("stressStatus")] ?? "#65758b",
            color: "#102033",
            "font-size": 11,
            "text-valign": "bottom",
            "text-margin-y": 8,
            width: (element: NodeSingular) => Math.max(36, Math.min(86, Math.sqrt(element.data("revenue")) / 2)),
            height: (element: NodeSingular) => Math.max(36, Math.min(86, Math.sqrt(element.data("revenue")) / 2))
          }
        },
        {
          selector: "edge",
          style: {
            width: 2,
            "line-color": "#91a3b7",
            "target-arrow-color": "#91a3b7",
            "target-arrow-shape": "triangle",
            "curve-style": "bezier",
            opacity: 0.55
          }
        },
        {
          selector: ".pulse",
          style: {
            width: 7,
            "line-color": "#d64b4b",
            "target-arrow-color": "#d64b4b",
            opacity: 1
          }
        }
      ]
    });

    cy.on("tap", "node", (event) => {
      const id = event.target.id();
      onSelectNode(graph.nodes.find((node) => node.data.id === id) ?? null);
    });
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectNode(null);
    });
    cyRef.current = cy;

    return () => {
      cy.elements(".pulse").removeClass("pulse");
      cy.destroy();
      if (cyRef.current === cy) cyRef.current = null;
    };
  }, [graph, onSelectNode]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;

    const timeouts: number[] = [];
    graph.pulses.forEach((pulse, index) => {
      timeouts.push(window.setTimeout(() => {
        const edge = cy.getElementById(pulse.relationshipId);
        edge.addClass("pulse");
        timeouts.push(window.setTimeout(() => edge.removeClass("pulse"), 650));
      }, index * 420));
    });

    return () => {
      timeouts.forEach(window.clearTimeout);
      if (!cy.destroyed()) cy.elements(".pulse").removeClass("pulse");
    };
  }, [graph.pulses, replayToken]);

  return <div className="network-map" ref={containerRef} aria-label="AI supply-chain network map" />;
}
