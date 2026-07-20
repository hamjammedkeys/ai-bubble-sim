"use client";

import { useState, type CSSProperties } from "react";
import type { Entity, Scenario } from "../lib/api";
import { TerminalButton, TerminalLabel, TerminalPanel, TerminalStatus } from "./terminal";

export type ScenarioLayer = "impact" | "exposure" | "unresolved" | "candidate" | "inactive";
export type ScenarioLayers = Record<ScenarioLayer, boolean>;

export const INITIAL_SCENARIO_LAYERS: ScenarioLayers = {
  impact: true,
  exposure: true,
  unresolved: true,
  candidate: true,
  inactive: true,
};

export type ScenarioBookProps = {
  scenarios: Scenario[];
  selectedId: string | null;
  entities: Entity[];
  phase: 0 | 1 | 2;
  running: boolean;
  layers: ScenarioLayers;
  onSelect: (id: string) => void;
  onCreate: (name: string, origin: string, magnitude: number) => Promise<void>;
  onRun: () => void;
  onReset: () => void;
  onLayerChange: (layer: ScenarioLayer, enabled: boolean) => void;
  createError?: string | null;
};

const layerOptions: Array<{ id: ScenarioLayer; label: string; color: string }> = [
  { id: "impact", label: "Impact", color: "var(--impact)" },
  { id: "exposure", label: "Exposure", color: "var(--exposure)" },
  { id: "unresolved", label: "Unresolved", color: "var(--amber)" },
  { id: "candidate", label: "Candidate", color: "var(--candidate)" },
  { id: "inactive", label: "Inactive", color: "var(--muted)" },
];

export function ScenarioBook({
  scenarios,
  selectedId,
  entities,
  phase,
  running,
  layers,
  onSelect,
  onCreate,
  onRun,
  onReset,
  onLayerChange,
  createError = null,
}: ScenarioBookProps) {
  const [showNew, setShowNew] = useState(false);
  const [name, setName] = useState("");
  const [origin, setOrigin] = useState("");
  const [magnitude, setMagnitude] = useState("10");
  const [busy, setBusy] = useState(false);
  const [localCreateError, setLocalCreateError] = useState<string | null>(null);

  const submit = async () => {
    if (!origin || !name) return;
    setBusy(true);
    setLocalCreateError(null);
    try {
      await onCreate(name, origin, Number.parseFloat(magnitude) || 0);
      setShowNew(false);
      setName("");
    } catch (error) {
      setLocalCreateError(`Scenario creation failed — ${String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const runIsActive = phase !== 0;
  const mutationDisabled = running || runIsActive;

  return (
    <div style={bookStyle}>
      <div style={sectionHeaderStyle}>
        <TerminalLabel>Scenario book</TerminalLabel>
        <TerminalStatus tone={runIsActive ? "pass" : "neutral"}>
          {runIsActive ? "RUN ACTIVE" : "IDLE"}
        </TerminalStatus>
      </div>

      <div style={scenarioListStyle}>
        {scenarios.length === 0 && <p style={emptyStyle}>No scenarios available.</p>}
        {scenarios.map((scenario) => {
          const active = scenario.id === selectedId;
          return (
            <button
              key={scenario.id}
              type="button"
              aria-current={active ? "true" : undefined}
              disabled={mutationDisabled}
              onClick={() => onSelect(scenario.id)}
              className="terminal-focus"
              style={scenarioRowStyle(active)}
            >
              <span style={scenarioNameStyle}>{scenario.name ?? "Scenario"}</span>
              {scenario.description && <span style={scenarioDescriptionStyle}>{scenario.description}</span>}
            </button>
          );
        })}
      </div>

      <div style={actionStyle}>
        {runIsActive ? (
          <TerminalButton type="button" onClick={onReset} style={secondaryButtonStyle}>
            Reset scenario
          </TerminalButton>
        ) : (
          <TerminalButton
            type="button"
            tone="impact"
            onClick={onRun}
            disabled={running || !selectedId}
            style={primaryButtonStyle}
          >
            {running ? "Running…" : "Run scenario"}
          </TerminalButton>
        )}

        {!mutationDisabled && (
          <TerminalButton
            type="button"
            onClick={() => setShowNew((visible) => !visible)}
            aria-expanded={showNew}
            style={newButtonStyle}
          >
            {showNew ? "− Cancel" : "+ New scenario"}
          </TerminalButton>
        )}
      </div>

      {(localCreateError ?? createError) && (
        <p role="alert" style={createErrorStyle}>{localCreateError ?? createError}</p>
      )}

      {showNew && !mutationDisabled && (
        <TerminalPanel style={formStyle}>
          <input
            aria-label="Scenario name"
            placeholder="Scenario name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            style={inputStyle}
          />
          <select
            aria-label="Shock origin"
            value={origin}
            onChange={(event) => setOrigin(event.target.value)}
            style={inputStyle}
          >
            <option value="">Shock origin…</option>
            {entities.map((entity) => (
              <option key={entity.id} value={entity.name}>
                {entity.name}
              </option>
            ))}
          </select>
          <label style={magnitudeStyle}>
            <span className="num" style={prefixStyle}>+$</span>
            <input
              aria-label="Shock magnitude in billions"
              type="number"
              value={magnitude}
              onChange={(event) => setMagnitude(event.target.value)}
              className="num"
              style={{ ...inputStyle, width: 72 }}
            />
            <span>B GAAP loss</span>
          </label>
          <TerminalButton
            type="button"
            tone="impact"
            onClick={() => void submit()}
            disabled={busy || !origin || !name}
            style={primaryButtonStyle}
          >
            {busy ? "Creating…" : "Create & select"}
          </TerminalButton>
          <p style={noteStyle}>
            The engine quantifies only directly touched evidence. Further hops remain unresolved—never
            invented.
          </p>
        </TerminalPanel>
      )}

      <fieldset style={layerFieldsetStyle}>
        <legend style={legendStyle}>Layers</legend>
        {layerOptions.map((layer) => (
          <label key={layer.id} style={layerRowStyle}>
            <span style={{ ...layerMarkStyle, background: layer.color }} aria-hidden="true" />
            <span>{layer.label}</span>
            <input
              type="checkbox"
              checked={layers[layer.id]}
              onChange={(event) => onLayerChange(layer.id, event.target.checked)}
              className="terminal-focus"
              style={{ marginLeft: "auto", accentColor: layer.color }}
            />
          </label>
        ))}
      </fieldset>
    </div>
  );
}

const bookStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  minHeight: "100%",
};

const sectionHeaderStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 12,
  padding: "15px 14px 11px",
  borderBottom: "1px solid var(--hairline)",
};

const scenarioListStyle: CSSProperties = { padding: "8px 8px 0" };

const emptyStyle: CSSProperties = {
  margin: 0,
  padding: "10px 6px",
  color: "var(--muted)",
  fontSize: 12,
};

function scenarioRowStyle(active: boolean): CSSProperties {
  return {
    display: "flex",
    flexDirection: "column",
    gap: 3,
    width: "100%",
    marginBottom: 5,
    padding: "10px 11px",
    border: `1px solid ${active ? "var(--exposure)" : "var(--hairline)"}`,
    borderRadius: 0,
    background: active ? "var(--surface-raised)" : "var(--bg)",
    color: "var(--text)",
    textAlign: "left",
    cursor: "pointer",
    opacity: 1,
  };
}

const scenarioNameStyle: CSSProperties = { fontSize: 12.5, fontWeight: 650 };

const scenarioDescriptionStyle: CSSProperties = {
  overflow: "hidden",
  color: "var(--muted)",
  fontSize: 10.5,
  lineHeight: 1.35,
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const actionStyle: CSSProperties = {
  display: "grid",
  gap: 6,
  padding: "8px",
};

const primaryButtonStyle: CSSProperties = {
  width: "100%",
  padding: "9px 10px",
  border: "1px solid var(--impact)",
  borderRadius: 0,
  background: "color-mix(in srgb, var(--impact) 14%, var(--surface))",
  fontSize: 12,
  fontWeight: 700,
  cursor: "pointer",
};

const secondaryButtonStyle: CSSProperties = {
  width: "100%",
  padding: "9px 10px",
  border: "1px solid var(--hairline)",
  borderRadius: 0,
  background: "var(--surface-raised)",
  color: "var(--text)",
  fontSize: 12,
  fontWeight: 700,
  cursor: "pointer",
};

const newButtonStyle: CSSProperties = {
  padding: "7px 8px",
  border: 0,
  borderRadius: 0,
  background: "transparent",
  color: "var(--muted)",
  fontSize: 11.5,
  textAlign: "left",
  cursor: "pointer",
};

const formStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 7,
  margin: "0 8px 8px",
  padding: 9,
};

const inputStyle: CSSProperties = {
  width: "100%",
  padding: "7px 8px",
  border: "1px solid var(--hairline)",
  borderRadius: 0,
  background: "var(--bg)",
  color: "var(--text)",
  fontSize: 12,
};

const magnitudeStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 7,
  color: "var(--muted)",
  fontSize: 11,
};

const prefixStyle: CSSProperties = { color: "var(--muted)", fontSize: 11 };

const noteStyle: CSSProperties = {
  margin: 0,
  color: "var(--muted)",
  fontSize: 10.5,
  lineHeight: 1.4,
};

const createErrorStyle: CSSProperties = {
  margin: "0 8px 8px",
  padding: "8px 9px",
  border: "1px solid var(--impact)",
  color: "var(--impact)",
  fontSize: 11,
  lineHeight: 1.4,
};

const layerFieldsetStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 0,
  margin: "10px 8px 14px",
  padding: 0,
  border: "1px solid var(--hairline)",
};

const legendStyle: CSSProperties = {
  marginLeft: 8,
  padding: "0 5px",
  color: "var(--muted)",
  font: "600 0.625rem/1 var(--font-plex-mono)",
  letterSpacing: ".1em",
  textTransform: "uppercase",
};

const layerRowStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 8,
  minHeight: 34,
  padding: "0 9px",
  borderBottom: "1px solid var(--hairline)",
  color: "var(--text)",
  fontSize: 11.5,
  cursor: "pointer",
};

const layerMarkStyle: CSSProperties = { width: 13, height: 2, flex: "0 0 auto" };
