import type { CSSProperties, ReactNode } from "react";
import type { DeskMetrics } from "../lib/dashboard";
import { TerminalMetric, TerminalStatus } from "./terminal";

export type DataStatus = "loading" | "live" | "degraded";

export type ExposureDeskProps = {
  header: ReactNode;
  marketStrip: ReactNode;
  scenarioBook: ReactNode;
  network: ReactNode;
  evidence: ReactNode;
  riskTape: ReactNode;
};

export function ExposureDesk({
  header,
  marketStrip,
  scenarioBook,
  network,
  evidence,
  riskTape,
}: ExposureDeskProps) {
  return (
    <main className="exposure-desk" style={deskStyle}>
      <header className="terminal-header" style={headerStyle}>
        {header}
      </header>
      <section className="market-strip" aria-label="Market summary" style={stripStyle}>
        {marketStrip}
      </section>
      <section className="desk-workspace" style={workspaceStyle}>
        <aside className="scenario-column" style={scenarioStyle}>
          {scenarioBook}
        </aside>
        <section className="network-column" aria-label="Network projection" style={networkStyle}>
          {network}
        </section>
        <aside className="evidence-column" aria-label="Evidence desk" style={evidenceStyle}>
          {evidence}
        </aside>
      </section>
      <footer className="risk-tape" style={riskStyle}>
        {riskTape}
      </footer>
    </main>
  );
}

export function MarketStrip({
  metrics,
  scenarioName,
}: {
  metrics: DeskMetrics;
  scenarioName: string | null;
}) {
  return (
    <div style={marketGridStyle}>
      <TerminalMetric label="Active scenario" value={scenarioName} style={metricStyle} />
      <TerminalMetric label="Network entities" value={String(metrics.entityCount)} style={metricStyle} />
      <TerminalMetric label="Evidence edges" value={String(metrics.approvedEdgeCount)} style={metricStyle} />
      <TerminalMetric
        label="Candidates"
        value={String(metrics.candidateCount)}
        tone="candidate"
        style={metricStyle}
      />
      <TerminalMetric
        label="Accounting impact"
        value={billions(metrics.impactTotal)}
        tone="impact"
        style={metricStyle}
      />
      <TerminalMetric
        label="Exposure at risk"
        value={billions(metrics.exposureTotal)}
        tone="exposure"
        style={metricStyle}
      />
      <TerminalMetric
        label="Unresolved hops"
        value={metrics.unresolvedCount == null ? null : String(metrics.unresolvedCount)}
        style={metricStyle}
      />
      <TerminalMetric
        label="Evidence coverage"
        value={metrics.evidenceCoverage == null ? null : `${metrics.evidenceCoverage}%`}
        tone={metrics.evidenceCoverage === 100 ? "pass" : "neutral"}
        style={{ ...metricStyle, borderRight: 0 }}
      />
    </div>
  );
}

export function TerminalDataStatus({ status }: { status: DataStatus }) {
  if (status === "loading") {
    return <TerminalStatus>○ LOADING</TerminalStatus>;
  }

  if (status === "degraded") {
    return <TerminalStatus tone="impact">● DEGRADED</TerminalStatus>;
  }

  return <TerminalStatus tone="pass">● DATA LIVE</TerminalStatus>;
}

function billions(value: number | null): string | null {
  return value == null ? null : `$${value.toFixed(1)}B`;
}

const deskStyle: CSSProperties = {
  display: "grid",
  gridTemplateRows: "58px 64px minmax(0, 1fr) 52px",
  height: "100vh",
  minWidth: 0,
  overflow: "hidden",
  background: "var(--bg)",
};

const headerStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 24,
  minWidth: 0,
  padding: "0 18px",
  borderBottom: "1px solid var(--hairline)",
  background: "var(--surface)",
};

const stripStyle: CSSProperties = {
  minWidth: 0,
  overflowX: "auto",
  borderBottom: "1px solid var(--hairline)",
  background: "var(--bg)",
};

const workspaceStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "250px minmax(0, 1fr) 360px",
  minWidth: 0,
  minHeight: 0,
};

const scenarioStyle: CSSProperties = {
  minWidth: 0,
  overflowY: "auto",
  borderRight: "1px solid var(--hairline)",
  background: "var(--surface)",
};

const networkStyle: CSSProperties = {
  position: "relative",
  minWidth: 0,
  minHeight: 0,
  overflow: "hidden",
};

const evidenceStyle: CSSProperties = {
  minWidth: 0,
  overflowY: "auto",
  borderLeft: "1px solid var(--hairline)",
  background: "var(--surface)",
};

const riskStyle: CSSProperties = {
  minWidth: 0,
  overflowX: "auto",
  borderTop: "1px solid var(--hairline)",
  background: "var(--surface)",
};

const marketGridStyle: CSSProperties = {
  display: "grid",
  gridAutoFlow: "column",
  gridAutoColumns: "minmax(132px, 1fr)",
  alignItems: "stretch",
  height: "100%",
  minWidth: 1080,
};

const metricStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  justifyContent: "center",
  gap: 7,
  minWidth: 0,
  padding: "0 14px",
  borderRight: "1px solid var(--hairline)",
  fontSize: 15,
  fontWeight: 650,
  whiteSpace: "nowrap",
};
