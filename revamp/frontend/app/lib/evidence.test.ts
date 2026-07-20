import { describe, expect, it } from "vitest";
import {
  detailAfterReview,
  evidenceDeskMode,
  shouldAcceptEdgeDetail,
  isGraphActivationKey,
  dataRequestErrorMessage,
  verificationOverall,
  verificationRows,
} from "./evidence";

describe("edge detail request persistence", () => {
  it("rejects stale detail from an earlier selection or pre-review request", () => {
    expect(
      shouldAcceptEdgeDetail(
        { edgeId: "edge-a", version: 1 },
        { selectedEdgeId: "edge-b", version: 2 },
      ),
    ).toBe(false);
    expect(
      shouldAcceptEdgeDetail(
        { edgeId: "edge-a", version: 1 },
        { selectedEdgeId: "edge-a", version: 2 },
      ),
    ).toBe(false);
  });

  it("accepts only the current request and preserves detail through review", () => {
    expect(
      shouldAcceptEdgeDetail(
        { edgeId: "edge-a", version: 2 },
        { selectedEdgeId: "edge-a", version: 2 },
      ),
    ).toBe(true);

    const current = {
      id: "edge-a",
      passage_text: "Exact filing passage",
      document_title: "10-K",
      document_url: "https://example.com/10-k",
      status: "candidate",
    } as never;
    const reviewed = { id: "edge-a", status: "rejected" } as never;

    expect(detailAfterReview(current, reviewed)).toMatchObject({
      id: "edge-a",
      status: "rejected",
      passage_text: "Exact filing passage",
      document_title: "10-K",
    });
  });
});

describe("mechanical verification presentation", () => {
  it("distinguishes explicit pass, explicit flag, and missing data", () => {
    expect(verificationOverall({ overall: "pass" })).toBe("pass");
    expect(verificationOverall({ overall: "flag" })).toBe("flag");
    expect(verificationOverall({})).toBe("unavailable");

    const rows = verificationRows({
      passage_found: true,
      number_found: false,
    });
    expect(rows).toHaveLength(7);
    expect(rows.find((row) => row.key === "passage_found")).toMatchObject({
      display: "PASS",
      state: "pass",
    });
    expect(rows.find((row) => row.key === "number_found")).toMatchObject({
      display: "FLAG",
      state: "flag",
    });
    expect(rows.find((row) => row.key === "entities_found")).toMatchObject({
      display: "UNAVAILABLE",
      state: "unavailable",
    });
  });

  it("renders a complete fixed row set for missing and partial objects", () => {
    expect(verificationRows({}).map((row) => row.state)).toEqual(
      Array(7).fill("unavailable"),
    );
    expect(verificationRows({ match_score: 97.5 })).toEqual(
      expect.arrayContaining([
        expect.objectContaining({ key: "match_score", display: "97.5%", state: "neutral" }),
        expect.objectContaining({ key: "source_valid", display: "UNAVAILABLE", state: "unavailable" }),
      ]),
    );
  });
});

it("keeps Evidence Desk mode priority stable", () => {
  expect(evidenceDeskMode({ edge: true, company: true, result: true })).toBe("evidence");
  expect(evidenceDeskMode({ edge: false, company: true, result: true })).toBe("company");
  expect(evidenceDeskMode({ edge: false, company: false, result: true })).toBe("results");
  expect(evidenceDeskMode({ edge: false, company: false, result: false })).toBe("queue");
});

it("recognizes Enter and Space as graph inspection activation keys", () => {
  expect(isGraphActivationKey("Enter")).toBe(true);
  expect(isGraphActivationKey(" ")).toBe(true);
  expect(isGraphActivationKey("Escape")).toBe(false);
});

it("describes global request failures without assuming an endpoint or cause", () => {
  const message = dataRequestErrorMessage("/scenarios/abc/run → 500");

  expect(message).toContain("Data request failed");
  expect(message).not.toContain("localhost");
  expect(message).not.toContain("Cannot reach");
});
