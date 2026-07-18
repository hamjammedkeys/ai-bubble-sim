import { expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { NetworkMap } from "../src/components/NetworkMap";

it("renders the Cytoscape network map surface", () => {
  render(
    <NetworkMap
      graph={{
        nodes: [],
        edges: [],
        pulses: [],
        summary: {
          scenarioLanguage: "estimated impact under scenario",
          totalRevenueLost: 0,
          stressedCompanyCount: 0
        }
      }}
      replayToken={0}
      onSelectNode={vi.fn()}
    />
  );

  expect(screen.getByLabelText("AI supply-chain network map")).toBeTruthy();
});
