import { describe, expect, it } from "vitest";
import { formatFinancialValue } from "./format";

describe("formatFinancialValue", () => {
  it("formats every supported currency scale", () => {
    expect(formatFinancialValue(8, "usd_billions")).toBe("$8.0B");
    expect(formatFinancialValue(8, "usd_millions")).toBe("$8.0M");
    expect(formatFinancialValue(8, "usd")).toBe("$8.0");
  });

  it("formats percentages and ownership without currency", () => {
    expect(formatFinancialValue(15, "percent")).toBe("15%");
    expect(formatFinancialValue(27.5, "ownership_pct")).toBe("27.5%");
  });

  it("formats shares and unitless or unknown values without currency", () => {
    expect(formatFinancialValue(1_250, "shares")).toBe("1,250 shares");
    expect(formatFinancialValue(12.5, null)).toBe("12.5");
    expect(formatFinancialValue(12.5, "widgets")).toBe("12.5");
  });

  it("uses an em dash for absent values regardless of unit", () => {
    expect(formatFinancialValue(null, "usd_billions")).toBe("—");
    expect(formatFinancialValue(null, null)).toBe("—");
  });
});
