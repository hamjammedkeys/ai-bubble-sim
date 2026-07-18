import type { Core, CytoscapeOptions } from "cytoscape";
import { render, screen } from "@testing-library/react";
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

const evidenceGraph = {
  scenario: {
    incrementalGaapLoss: 10_000_000_000,
    creditStatus: "severe_distress",
    defaultStatus: "not_defaulted",
    language: "calculated Impact plus activated Exposure; downstream loss not identifiable"
  },
  nodes: [
    { companyId: "openai", label: "OpenAI", quantifiedImpact: null, activatedExposure: null, epistemicState: "source", rankingEligible: false, tierSummary: [] },
    { companyId: "msft", label: "Microsoft", quantifiedImpact: -2_700_000_000, activatedExposure: null, epistemicState: "quantified_impact", rankingEligible: true, tierSummary: ["solid_red"] },
    { companyId: "coreweave", label: "CoreWeave", quantifiedImpact: null, activatedExposure: 11_900_000_000, epistemicState: "exposure_detected", rankingEligible: false, tierSummary: ["solid_orange", "dashed_amber"] },
    { companyId: "nvda", label: "NVIDIA", quantifiedImpact: null, activatedExposure: null, epistemicState: "not_identifiable", rankingEligible: false, tierSummary: ["diffuse_amber"] }
  ],
  edges: [
    { relationshipId: "impact", source: "openai", target: "msft", structureType: "equity_method", tier: "solid_red", resultKind: "impact", value: -2_700_000_000, basis: "calculated", provenance: {}, sourceAccession: "acc-1" },
    { relationshipId: "exposure", source: "openai", target: "coreweave", structureType: "take_or_pay", tier: "solid_orange", resultKind: "exposure", value: 11_900_000_000, basis: "reported", provenance: {}, sourceAccession: "acc-2" },
    { relationshipId: "guardrail", source: "openai", target: "coreweave", structureType: "take_or_pay", tier: "dashed_amber", resultKind: "realized_loss_unidentifiable", value: null, basis: "not identifiable", provenance: {}, sourceAccession: "acc-2" },
    { relationshipId: "dissolve", source: "coreweave", target: "nvda", structureType: "behavioural", tier: "diffuse_amber", resultKind: "behavioural", value: null, basis: "not identifiable", provenance: {}, sourceAccession: "acc-2" }
  ],
  reviewCandidates: [
    { candidateId: "candidate-1", sourceId: "acc-2", sourceAccession: "acc-2", sourceCompanyId: "msft", targetCompanyId: "coreweave", relationshipType: "take_or_pay", quotedText: "Proposal", numericToken: null, value: null, unit: null, period: null, supportedRule: "rule", unsupportedInference: "inference", status: "proposed" }
  ],
  auditLog: [],
  ranking: []
};

beforeEach(() => {
  captured.instances.length = 0;
  captured.options.length = 0;
});

afterEach(() => {
  vi.useRealTimers();
});

describe("NetworkMap", () => {
  it("maps each evidence tier to a distinct Cytoscape visual style", () => {
    render(<NetworkMap evidence={evidenceGraph as never} replayToken={0} onSelectNode={vi.fn()} />);

    const cy = captured.instances[0];
    expect(screen.getByLabelText("AI supply-chain network map")).toBeTruthy();
    expect(cy.edges().map((edge) => edge.id())).toEqual([
      "impact",
      "exposure",
      "guardrail",
      "dissolve",
      "candidate-candidate-1"
    ]);
    const styles = captured.options[0].style as Array<{
      selector: string;
      style: Record<string, unknown>;
    }>;
    const styleFor = (selector: string) => styles.find((style) => style.selector === selector)?.style;
    expect(styleFor(".tier-solid_red")).toMatchObject({ "line-color": "#c9383a" });
    expect(styleFor(".tier-solid_orange")).toMatchObject({ "line-color": "#e06c24" });
    expect(styleFor(".tier-dashed_amber")).toMatchObject({ "line-style": "dashed" });
    expect(styleFor(".tier-diffuse_amber")).toMatchObject({ "line-style": "dotted", opacity: 0.28 });
    expect(cy.getElementById("candidate-candidate-1").hasClass("blue_striped")).toBe(true);
  });

  it("keeps an unlinked candidate out of Cytoscape", () => {
    const unlinkedEvidence = {
      ...evidenceGraph,
      reviewCandidates: [{ ...evidenceGraph.reviewCandidates[0], targetCompanyId: null }]
    };

    render(<NetworkMap evidence={unlinkedEvidence as never} replayToken={0} onSelectNode={vi.fn()} />);

    const cy = captured.instances[0];
    expect(cy.getElementById("candidate-candidate-1").empty()).toBe(true);
  });
});
