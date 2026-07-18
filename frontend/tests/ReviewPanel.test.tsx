import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { ReviewPanel } from "../src/components/ReviewPanel";

const takeOrPayView = {
  candidate: {
    candidate_id: "coreweave-s1a-take_or_pay",
    relationship_type: "take_or_pay",
    source_company_id: "openai",
    target_company_id: "coreweave",
    quoted_text: "OpenAI has committed to purchase $11.9 billion from CoreWeave.",
    status: "proposed"
  },
  verification: {
    checks: [
      { name: "quoted_text", passed: true, detail: "quote present" },
      { name: "arithmetic", passed: true, detail: "ok" }
    ],
    mechanically_valid: true,
    semantic_interpretation: "pending_human_review"
  },
  highlight: { start: 0, end: 60 }
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => ({ ok: true, json: async () => ({ candidates: [takeOrPayView] }) }))
  );
});
afterEach(() => vi.unstubAllGlobals());

test("analyze renders a blue-striped candidate with its checklist", async () => {
  render(<ReviewPanel onDecision={() => {}} />);
  fireEvent.click(screen.getByRole("button", { name: /analyze filing/i }));
  await waitFor(() => screen.getByText(/take_or_pay/i));
  // existence assertions (getBy* throws if missing)
  screen.getByText(/pending human review/i);
  screen.getByRole("button", { name: /approve/i });
  screen.getByRole("button", { name: /reject/i });
  expect(screen.getByText(/quoted_text/i)).not.toBeNull();
});
