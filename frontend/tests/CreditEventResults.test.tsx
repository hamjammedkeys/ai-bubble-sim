import { render, screen } from "@testing-library/react";
import { expect, test } from "vitest";
import { CreditEventResults } from "../src/components/CreditEventResults";

const result = {
  edges: [
    {
      relationship_id: "openai-msft-equity",
      source: "openai",
      target: "msft",
      tier: "solid_red",
      result_kind: "impact",
      value: -2_700_000_000,
      basis: "equity-method"
    },
    {
      relationship_id: "coreweave-s1a-take_or_pay",
      source: "openai",
      target: "coreweave",
      tier: "solid_orange",
      result_kind: "exposure",
      value: 11_900_000_000,
      basis: "take-or-pay"
    }
  ],
  nodes: {
    msft: {
      quantified_impact: -2_700_000_000,
      activated_exposure: null,
      epistemic_state: "quantified_impact"
    },
    coreweave: {
      quantified_impact: null,
      activated_exposure: 11_900_000_000,
      epistemic_state: "exposure_detected"
    }
  }
};

test("renders impact in red and exposure as not-a-loss in orange", () => {
  render(<CreditEventResults result={result} />);
  screen.getByText(/not a realized loss/i);
  const orange = screen.getByText(/take-or-pay/i).closest(".tier-solid_orange");
  expect(orange).not.toBeNull();
  const red = screen.getByText(/equity-method/i).closest(".tier-solid_red");
  expect(red).not.toBeNull();
});
