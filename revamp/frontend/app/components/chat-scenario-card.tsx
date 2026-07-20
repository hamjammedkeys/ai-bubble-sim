"use client";

import type { CSSProperties } from "react";
import type { ChatCompletedRun, ChatScenarioCardModel } from "../lib/chat-actions";
import { formatFinancialValue } from "../lib/format";
import {
  TerminalButton,
  TerminalLabel,
  TerminalMetric,
  TerminalPanel,
  TerminalStatus,
} from "./terminal";

export type ChatScenarioCardProps = {
  model: ChatScenarioCardModel;
  onRun: (scenarioId: string) => void;
  onView: (scenarioId: string, run: ChatCompletedRun) => void;
  running?: boolean;
  error?: string | null;
};

export function ChatScenarioCard({
  model,
  onRun,
  onView,
  running = false,
  error = null,
}: ChatScenarioCardProps) {
  const complete = model.status === "complete";

  return (
    <TerminalPanel className="content-safe" style={cardStyle}>
      <div style={headerStyle}>
        <TerminalLabel>Scenario</TerminalLabel>
        <TerminalStatus tone={complete ? "pass" : "neutral"}>
          {complete ? "RUN COMPLETE" : "READY"}
        </TerminalStatus>
      </div>

      <strong className="content-safe" style={nameStyle}>{model.name}</strong>

      <div style={detailGridStyle}>
        <TerminalMetric label="Origin" value={model.originEntity} style={metricStyle} />
        <TerminalMetric
          label="Magnitude"
          value={formatMagnitude(model.magnitude, model.unit)}
          tone="impact"
          style={metricStyle}
        />
      </div>

      {complete && (
        <div style={totalsGridStyle}>
          <TerminalMetric
            label="Accounting impact"
            value={formatFinancialValue(model.totals.impact_total, null)}
            tone="impact"
            style={metricStyle}
          />
          <TerminalMetric
            label="Exposure at risk"
            value={formatFinancialValue(model.totals.exposure_total, null)}
            tone="exposure"
            style={metricStyle}
          />
          <TerminalMetric
            label="Unresolved"
            value={String(model.totals.unresolved_count)}
            style={metricStyle}
          />
        </div>
      )}

      {error && <p role="alert" className="content-safe" style={errorStyle}>{error}</p>}

      <TerminalButton
        type="button"
        tone={complete ? "exposure" : "impact"}
        disabled={!complete && running}
        onClick={() => complete ? onView(model.scenarioId, model.run) : onRun(model.scenarioId)}
        style={buttonStyle}
      >
        {complete ? "View on graph" : running ? "Running…" : "Run scenario"}
      </TerminalButton>
    </TerminalPanel>
  );
}

const knownMagnitudeUnits = new Set([
  "usd_billions",
  "usd_millions",
  "usd",
  "percent",
  "ownership_pct",
  "shares",
]);

function formatMagnitude(magnitude: number, unit: string | null): string {
  const formatted = formatFinancialValue(magnitude, unit);
  return unit && !knownMagnitudeUnits.has(unit) ? `${formatted} ${unit}` : formatted;
}

const cardStyle: CSSProperties = {
  display: "grid",
  minWidth: 0,
  gap: 10,
  padding: 12,
  borderRadius: 0,
};

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
  minWidth: 0,
};

const nameStyle: CSSProperties = {
  color: "var(--text)",
  fontSize: 13,
  lineHeight: 1.35,
};

const detailGridStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(100px, 1fr))",
  gap: 1,
  minWidth: 0,
  background: "var(--hairline)",
};

const totalsGridStyle: CSSProperties = {
  ...detailGridStyle,
  gridTemplateColumns: "repeat(auto-fit, minmax(88px, 1fr))",
};

const metricStyle: CSSProperties = {
  minWidth: 0,
  padding: "8px 9px",
  background: "var(--bg)",
};

const errorStyle: CSSProperties = {
  margin: 0,
  color: "var(--impact)",
  fontSize: 11,
  lineHeight: 1.4,
};

const buttonStyle: CSSProperties = {
  width: "100%",
  padding: "9px 10px",
  border: "1px solid currentColor",
  borderRadius: 0,
  background: "var(--surface-raised)",
  fontSize: 12,
  fontWeight: 700,
  cursor: "pointer",
};
