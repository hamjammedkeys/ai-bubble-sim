import type { CSSProperties } from "react";
import type { DeskMetrics } from "../lib/dashboard";
import { TerminalLabel, TerminalStatus } from "./terminal";

export function RiskTape({
  metrics,
  scenarioName,
  identifiableHopCount,
}: {
  metrics: DeskMetrics;
  scenarioName: string | null;
  identifiableHopCount: number | null;
}) {
  const idle = metrics.impactTotal == null;

  return (
    <div style={tapeStyle} aria-live="polite">
      <TerminalLabel style={labelStyle}>Risk tape</TerminalLabel>
      {idle ? (
        <TerminalStatus style={idleStyle}>Select and run a scenario</TerminalStatus>
      ) : (
        <div className="num" style={summaryStyle}>
          <strong style={scenarioStyle}>{scenarioName ?? "Scenario"}</strong>
          <span>produced</span>
          <TerminalStatus tone="impact">{billions(metrics.impactTotal)} accounting impact</TerminalStatus>
          <span>and</span>
          <TerminalStatus tone="exposure">{billions(metrics.exposureTotal)} exposure at risk</TerminalStatus>
          <span>with</span>
          <TerminalStatus>{identifiableHopCount ?? "—"} identifiable hops</TerminalStatus>
          <span>·</span>
          <TerminalStatus tone={metrics.evidenceCoverage === 100 ? "pass" : "neutral"}>
            {metrics.evidenceCoverage == null ? "—" : `${metrics.evidenceCoverage}%`} evidence coverage
          </TerminalStatus>
        </div>
      )}
    </div>
  );
}

function billions(value: number | null): string {
  return value == null ? "—" : `$${value.toFixed(1)}B`;
}

const tapeStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 16,
  height: "100%",
  minWidth: "max-content",
  padding: "0 18px",
};

const labelStyle: CSSProperties = {
  paddingRight: 16,
  borderRight: "1px solid var(--hairline)",
};

const idleStyle: CSSProperties = { color: "var(--muted)", letterSpacing: ".04em" };

const summaryStyle: CSSProperties = {
  display: "flex",
  alignItems: "baseline",
  gap: 8,
  color: "var(--muted)",
  fontSize: 11.5,
  whiteSpace: "nowrap",
};

const scenarioStyle: CSSProperties = { color: "var(--text)", fontSize: 12 };
