import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import App from "../src/App";

const graphResponse = {
  nodes: [],
  edges: [],
  pulses: [],
  summary: {
    scenarioLanguage: "estimated impact under scenario",
    totalRevenueLost: 0,
    stressedCompanyCount: 0
  }
};

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("opens on the working AI fragility map", async () => {
    const fetchMock = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => graphResponse
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect(await screen.findByText("AI Fragility Map")).toBeTruthy();
    expect(screen.getAllByText("estimated impact under scenario")).toHaveLength(2);
    expect(screen.getByRole("button", { name: "Run shock" })).toBeTruthy();
    expect(screen.getByText("Cloud AI Spending Slowdown")).toBeTruthy();
    expect(screen.getByText("Scenario Results")).toBeTruthy();
    expect(screen.getByText("Company")).toBeTruthy();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
      expect(screen.getByLabelText("AI supply-chain network map").getAttribute("data-replay-token")).toBe("1");
    });
  });

  it("keeps the initial graph and shows an error when the scenario request fails", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("network unavailable"));
    vi.stubGlobal("fetch", fetchMock);

    render(<App />);

    expect((await screen.findByRole("alert")).textContent).toBe("Unable to load scenario results.");
    expect(screen.getAllByText("estimated impact under scenario")).toHaveLength(2);
    expect(screen.getByText("$0M")).toBeTruthy();
    expect(screen.getByText("0")).toBeTruthy();
  });
});
