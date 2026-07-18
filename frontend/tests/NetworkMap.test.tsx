import type { Core, CytoscapeOptions } from "cytoscape";
import { act, render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const captured = vi.hoisted(() => ({
  instances: [] as Core[],
  options: [] as CytoscapeOptions[]
}));

vi.mock("cytoscape", async (importOriginal) => {
  const actual = await importOriginal<typeof import("cytoscape")>();
  return {
    ...actual,
    default: (options: CytoscapeOptions) => {
      captured.options.push(options);
      const realCytoscape = (actual as unknown as {
        default: (options: CytoscapeOptions) => Core;
      }).default;
      const instance = realCytoscape(options);
      captured.instances.push(instance);
      return instance;
    }
  };
});

import { NetworkMap } from "../src/components/NetworkMap";
import type { GraphPayload } from "../src/types";

const graph: GraphPayload = {
  nodes: [
    {
      data: {
        id: "supplier",
        label: "Supplier",
        sectorGroup: "Cloud",
        revenue: 100,
        revenueLoss: 10,
        stressStatus: "stressed"
      }
    },
    {
      data: {
        id: "customer",
        label: "Customer",
        sectorGroup: "Software",
        revenue: 64,
        revenueLoss: 4,
        stressStatus: "exposed"
      }
    }
  ],
  edges: [
    {
      data: {
        id: "supplier-customer",
        source: "supplier",
        target: "customer",
        annualFlowBase: 20,
        confidenceScore: 0.8,
        estimateMethod: "inferred"
      }
    }
  ],
  pulses: [
    {
      relationshipId: "supplier-customer",
      source: "supplier",
      target: "customer",
      roundIndex: 0,
      revenueLoss: 4
    }
  ],
  summary: {
    scenarioLanguage: "estimated impact under scenario",
    totalRevenueLost: 14,
    stressedCompanyCount: 2
  }
};

beforeEach(() => {
  captured.instances.length = 0;
  captured.options.length = 0;
});

afterEach(() => {
  vi.useRealTimers();
});

describe("NetworkMap", () => {
  it("loads graph elements into a real headless Cytoscape instance", () => {
    render(<NetworkMap graph={graph} replayToken={0} onSelectNode={vi.fn()} />);

    const cy = captured.instances[0];
    expect(screen.getByLabelText("AI supply-chain network map")).toBeTruthy();
    expect(captured.options[0].headless).toBe(true);
    expect(captured.options[0].layout).toMatchObject({ name: "preset" });
    expect(cy.nodes().map((node) => node.id())).toEqual(["supplier", "customer"]);
    expect(cy.edges().map((edge) => edge.id())).toEqual(["supplier-customer"]);
  });

  it("selects a graph node and clears selection on a background tap", () => {
    const onSelectNode = vi.fn();
    render(<NetworkMap graph={graph} replayToken={0} onSelectNode={onSelectNode} />);
    const cy = captured.instances[0];

    cy.getElementById("supplier").emit("tap");
    expect(onSelectNode).toHaveBeenLastCalledWith(graph.nodes[0]);

    cy.emit("tap");
    expect(onSelectNode).toHaveBeenLastCalledWith(null);
  });

  it("adds and removes the pulse class using the replay timers", () => {
    vi.useFakeTimers();
    render(<NetworkMap graph={graph} replayToken={0} onSelectNode={vi.fn()} />);
    const edge = captured.instances[0].getElementById("supplier-customer");

    act(() => vi.advanceTimersByTime(0));
    expect(edge.hasClass("pulse")).toBe(true);

    act(() => vi.advanceTimersByTime(650));
    expect(edge.hasClass("pulse")).toBe(false);
  });

  it("clears an active pulse before restarting replay", () => {
    vi.useFakeTimers();
    const onSelectNode = vi.fn();
    const { rerender } = render(
      <NetworkMap graph={graph} replayToken={0} onSelectNode={onSelectNode} />
    );
    const edge = captured.instances[0].getElementById("supplier-customer");
    act(() => vi.advanceTimersByTime(0));
    expect(edge.hasClass("pulse")).toBe(true);

    rerender(<NetworkMap graph={graph} replayToken={1} onSelectNode={onSelectNode} />);

    expect(edge.hasClass("pulse")).toBe(false);
    act(() => vi.advanceTimersByTime(0));
    expect(edge.hasClass("pulse")).toBe(true);
  });

  it("cancels stale pulse callbacks and removes active classes on unmount", () => {
    vi.useFakeTimers();
    const { unmount } = render(
      <NetworkMap graph={graph} replayToken={0} onSelectNode={vi.fn()} />
    );
    const cy = captured.instances[0];
    const edge = cy.getElementById("supplier-customer");
    act(() => vi.advanceTimersByTime(0));
    expect(edge.hasClass("pulse")).toBe(true);

    unmount();

    expect(edge.hasClass("pulse")).toBe(false);
    expect(vi.getTimerCount()).toBe(0);
    expect(() => vi.runAllTimers()).not.toThrow();
  });
});
