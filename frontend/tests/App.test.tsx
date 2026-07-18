import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";

const evidencePayload = {
  scenario: {
    incrementalGaapLoss: 10_000_000_000,
    creditStatus: "severe_distress",
    defaultStatus: "not_defaulted",
    language: "calculated Impact plus activated Exposure; downstream loss not identifiable"
  },
  nodes: [
    {
      companyId: "msft",
      label: "Microsoft",
      quantifiedImpact: -2_700_000_000,
      activatedExposure: null,
      epistemicState: "quantified_impact",
      rankingEligible: true,
      tierSummary: ["solid_red"]
    },
    {
      companyId: "coreweave",
      label: "CoreWeave",
      quantifiedImpact: null,
      activatedExposure: 11_900_000_000,
      epistemicState: "exposure_detected",
      rankingEligible: false,
      tierSummary: ["solid_orange", "dashed_amber"]
    },
    {
      companyId: "nvda",
      label: "NVIDIA",
      quantifiedImpact: null,
      activatedExposure: null,
      epistemicState: "not_identifiable",
      rankingEligible: false,
      tierSummary: ["diffuse_amber"]
    }
  ],
  edges: [
    {
      relationshipId: "openai-msft",
      source: "openai",
      target: "msft",
      structureType: "equity_method",
      tier: "solid_red",
      resultKind: "impact",
      value: -2_700_000_000,
      basis: "equity-method share of stated GAAP loss",
      provenance: { relationship: "reported", magnitude: "reported", propagation: "calculated", timing: "constrained_estimate" },
      sourceAccession: "openai-10k-2025"
    },
    {
      relationshipId: "openai-coreweave",
      source: "openai",
      target: "coreweave",
      structureType: "take_or_pay",
      tier: "solid_orange",
      resultKind: "exposure",
      value: 11_900_000_000,
      basis: "take-or-pay contract envelope activated (not a realized loss)",
      provenance: { relationship: "reported", magnitude: "reported", propagation: "calculated", timing: "constrained_estimate" },
      sourceAccession: "coreweave-s1a-2025"
    },
    {
      relationshipId: "openai-coreweave-realized-loss",
      source: "openai",
      target: "coreweave",
      structureType: "take_or_pay",
      tier: "dashed_amber",
      resultKind: "realized_loss_unidentifiable",
      value: null,
      basis: "activated take-or-pay exposure; realized loss not identifiable without EAD, PD, LGD, timing",
      provenance: { relationship: "reported", magnitude: "reported", propagation: "calculated", timing: "constrained_estimate" },
      sourceAccession: "coreweave-s1a-2025"
    },
    {
      relationshipId: "coreweave-nvda",
      source: "coreweave",
      target: "nvda",
      structureType: "behavioural",
      tier: "diffuse_amber",
      resultKind: "behavioural",
      value: null,
      basis: "documented dependency; magnitude not identifiable from evidence",
      provenance: { relationship: "reported", magnitude: "reported", propagation: "calculated", timing: "constrained_estimate" },
      sourceAccession: "coreweave-s1a-2025"
    }
  ],
  reviewCandidates: [
    {
      candidateId: "candidate-1",
      sourceId: "msft-filing",
      sourceAccession: "acc-1",
      sourceCompanyId: "msft",
      targetCompanyId: "coreweave",
      relationshipType: "take_or_pay",
      quotedText: "Reported commitment.",
      numericToken: "$4 billion",
      value: 4_000_000_000,
      unit: "USD",
      period: "through 2030",
      supportedRule: "reported purchase commitment envelope",
      unsupportedInference: "counterparty mapping awaits review",
      status: "proposed"
    }
  ],
  auditLog: [],
  ranking: [{ companyId: "msft", magnitude: 2_700_000_000 }]
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("renders evidence tiers without turning exposure into loss", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => evidencePayload }));

    render(<App />);

    expect(await screen.findByText("Calculated Impact")).toBeTruthy();
    expect(screen.getByText("Activated Exposure")).toBeTruthy();
    expect(screen.getByText("Realized loss: not identifiable")).toBeTruthy();
    expect(screen.getByText("Behavioural dissolve")).toBeTruthy();
    expect(screen.getByText("Pending human review")).toBeTruthy();
    expect(screen.queryByText("$11,900M loss")).toBeNull();
  });

  it("submits review decisions and refreshes the evidence graph", async () => {
    const reviewedPayload = {
      ...evidencePayload,
      reviewCandidates: [],
      auditLog: [
        {
          auditId: "audit-1",
          candidateId: "candidate-1",
          fromStatus: "proposed",
          toStatus: "approved",
          reviewerId: "dashboard-reviewer",
          reason: "Quote and amount confirmed",
          verificationValid: true,
          createdAt: "2026-07-18T00:00:00Z"
        }
      ]
    };
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => evidencePayload })
      .mockResolvedValueOnce({ ok: true, json: async () => evidencePayload })
      .mockResolvedValueOnce({ ok: true, json: async () => reviewedPayload })
      .mockResolvedValueOnce({ ok: true, json: async () => evidencePayload })
      .mockResolvedValueOnce({ ok: true, json: async () => reviewedPayload });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    fireEvent.click(await screen.findByRole("button", { name: "Approve candidate" }));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v2/review/candidate-1/approve",
        expect.objectContaining({ method: "POST" })
      );
    });
    expect(await screen.findByText("Quote and amount confirmed")).toBeTruthy();
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v2/scenario/compound-credit-event",
      expect.objectContaining({ method: "POST" })
    );
  });
});
