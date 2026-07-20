const plainNumber = new Intl.NumberFormat("en-US", {
  maximumFractionDigits: 2,
});

export function formatFinancialValue(value: number | null, unit: string | null): string {
  if (value == null) return "—";

  switch (unit) {
    case "usd_billions":
      return `$${value.toFixed(1)}B`;
    case "usd_millions":
      return `$${value.toFixed(1)}M`;
    case "usd":
      return `$${value.toFixed(1)}`;
    case "percent":
    case "ownership_pct":
      return `${plainNumber.format(value)}%`;
    case "shares":
      return `${plainNumber.format(value)} shares`;
    default:
      return plainNumber.format(value);
  }
}
