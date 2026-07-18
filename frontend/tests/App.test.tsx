import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import App, { SCENARIO_LANGUAGE } from "../src/App";
import { CompanyPanel } from "../src/components/CompanyPanel";

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

const company = (id: string, label: string) => ({
  data: {
    id,
    label,
    sectorGroup: "Cloud",
    revenue: 100,
    revenueLoss: 12,
    stressStatus: "stressed" as const
  }
});

const graphWith = (...nodes: ReturnType<typeof company>[]) => ({ ...graphResponse, nodes });

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((resolvePromise, rejectPromise) => {
    resolve = resolvePromise;
    reject = rejectPromise;
  });
  return { promise, resolve, reject };
}

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
    expect(within(screen.getByText("Total revenue lost").parentElement!).getByText("inferred")).toBeTruthy();
    expect(screen.getByLabelText("AI supply-chain network map")).toBeTruthy();

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledTimes(1);
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

  it("allows only the latest scenario response to update the dashboard", async () => {
    const olderSuccess = deferred<Response>();
    const olderFailure = deferred<Response>();
    const newer = deferred<Response>();
    const fetchMock = vi.fn()
      .mockReturnValueOnce(olderSuccess.promise)
      .mockReturnValueOnce(olderFailure.promise)
      .mockReturnValueOnce(newer.promise);
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    fireEvent.change(screen.getByLabelText("Shock"), { target: { value: "0.4" } });
    fireEvent.change(screen.getByLabelText("Shock"), { target: { value: "0.2" } });
    await waitFor(() => expect(fetchMock).toHaveBeenCalledTimes(3));
    newer.resolve({ ok: true, json: async () => graphWith(company("new", "New Company")) } as Response);
    expect(await screen.findByRole("option", { name: "New Company" })).toBeTruthy();

    olderSuccess.resolve({
      ok: true,
      json: async () => graphWith(company("old", "Old Company"))
    } as Response);
    olderFailure.reject(new Error("stale failure"));
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
    expect(screen.getByRole("option", { name: "New Company" })).toBeTruthy();
    expect(screen.queryByRole("option", { name: "Old Company" })).toBeNull();
  });

  it("preserves selection by ID across refresh and clears it when absent or on failure", async () => {
    const first = graphWith(company("kept", "Original label"), company("gone", "Gone"));
    const refreshed = graphWith(company("kept", "Updated label"));
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({ ok: true, json: async () => first })
      .mockResolvedValueOnce({ ok: true, json: async () => refreshed })
      .mockRejectedValueOnce(new Error("offline"));
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const selector = await screen.findByRole("combobox", { name: "Inspect company" });
    fireEvent.change(selector, { target: { value: "kept" } });
    expect(screen.getByRole("heading", { name: "Original label" })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Run shock" }));
    expect(await screen.findByRole("heading", { name: "Updated label" })).toBeTruthy();

    fireEvent.click(screen.getByRole("button", { name: "Run shock" }));
    expect(await screen.findByRole("alert")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Updated label" })).toBeNull();
    expect((screen.getByRole("combobox", { name: "Inspect company" }) as HTMLSelectElement).value).toBe("");
  });

  it("clears selection when a successful refresh no longer contains its company", async () => {
    const fetchMock = vi.fn()
      .mockResolvedValueOnce({
        ok: true,
        json: async () => graphWith(company("removed", "Removed Company"))
      })
      .mockResolvedValueOnce({ ok: true, json: async () => graphWith(company("other", "Other")) });
    vi.stubGlobal("fetch", fetchMock);
    render(<App />);

    const selector = await screen.findByRole("combobox", { name: "Inspect company" });
    fireEvent.change(selector, { target: { value: "removed" } });
    fireEvent.click(screen.getByRole("button", { name: "Run shock" }));

    await waitFor(() => expect(screen.queryByRole("heading", { name: "Removed Company" })).toBeNull());
    expect((screen.getByRole("combobox", { name: "Inspect company" }) as HTMLSelectElement).value).toBe("");
  });

  it("renders the frontend-owned scenario phrase even when the API phrase is malformed", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...graphResponse,
        summary: { ...graphResponse.summary, scenarioLanguage: "guaranteed prediction" }
      })
    }));
    render(<App />);

    await waitFor(() => expect(screen.getAllByText(SCENARIO_LANGUAGE)).toHaveLength(2));
    expect(screen.queryByText("guaranteed prediction")).toBeNull();
  });

  it("provides a keyboard-operable company selector synchronized with selection", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
      ok: true,
      json: async () => graphWith(company("one", "Company One"), company("two", "Company Two"))
    }));
    render(<App />);

    const selector = await screen.findByRole("combobox", { name: "Inspect company" });
    selector.focus();
    fireEvent.keyDown(selector, { key: "ArrowDown" });
    fireEvent.change(selector, { target: { value: "two" } });
    expect(screen.getByRole("heading", { name: "Company Two" })).toBeTruthy();
    expect((selector as HTMLSelectElement).value).toBe("two");

    fireEvent.change(selector, { target: { value: "" } });
    expect(screen.getByRole("heading", { name: "Company" })).toBeTruthy();
    expect((selector as HTMLSelectElement).value).toBe("");
  });
});

describe("CompanyPanel", () => {
  it("labels selected-company revenue loss as inferred", () => {
    render(
      <CompanyPanel
        nodes={[]}
        node={{
          data: {
            id: "company-1",
            label: "Example Company",
            sectorGroup: "Cloud",
            revenue: 100,
            revenueLoss: 12,
            stressStatus: "stressed"
          }
        }}
        onSelectNode={vi.fn()}
      />
    );

    expect(within(screen.getByText("Revenue loss").parentElement!).getByText("inferred")).toBeTruthy();
  });
});
