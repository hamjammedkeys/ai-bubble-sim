"use client";

import {
  useLayoutEffect,
  useRef,
  useState,
  type CSSProperties,
  type ReactNode,
  type RefObject,
} from "react";
import {
  api,
  type Edge,
  type EdgeDetail,
  type EdgeResult,
  type Entity,
} from "../lib/api";
import {
  evidenceDeskMode,
  verificationOverall,
  verificationRows,
  type VerificationRow,
} from "../lib/evidence";
import { formatFinancialValue } from "../lib/format";
import { ENTITY_LABEL } from "../lib/graph";
import { TerminalButton, TerminalLabel, TerminalStatus } from "./terminal";

export type EvidenceDeskProps = {
  selectedEdge: Edge | null;
  selectedEdgeGroup: Edge[];
  selectedEntity: Entity | null;
  detail: EdgeDetail | null;
  detailError?: string | null;
  result?: EdgeResult;
  structuralResults: EdgeResult[];
  assumptionResults: EdgeResult[];
  hasActiveResult: boolean;
  propagationInProgress: boolean;
  edges: Edge[];
  entityName: (id: string | null) => string;
  onCloseSelection: () => void;
  onSelectEdge: (id: string) => void;
  onGraphChanged: () => Promise<void> | void;
  onEdgeReviewed: (edge: Edge) => Promise<void> | void;
};

type RelationshipNavigationControl = "previous" | "next" | "chip";

export function relationshipNavigationFocusTarget<T extends { disabled: boolean }>(
  requestedControl: T | null,
  selectedChip: T | null,
): T | null {
  return requestedControl && !requestedControl.disabled ? requestedControl : selectedChip;
}

export function EvidenceDesk({
  selectedEdge,
  selectedEdgeGroup,
  selectedEntity,
  detail,
  detailError = null,
  result,
  structuralResults,
  assumptionResults,
  hasActiveResult,
  propagationInProgress,
  edges,
  entityName,
  onCloseSelection,
  onSelectEdge,
  onGraphChanged,
  onEdgeReviewed,
}: EvidenceDeskProps) {
  const inspectorRootRef = useRef<HTMLDivElement>(null);
  const pendingRelationshipFocusRef = useRef<{
    edgeId: string;
    control: RelationshipNavigationControl;
  } | null>(null);
  const mode = evidenceDeskMode({
    edge: selectedEdge !== null,
    company: selectedEntity !== null,
    result: hasActiveResult,
  });

  useLayoutEffect(() => {
    const pending = pendingRelationshipFocusRef.current;
    const root = inspectorRootRef.current;
    if (!pending || !root || selectedEdge?.id !== pending.edgeId) return;

    const buttons = Array.from(root.querySelectorAll<HTMLButtonElement>("button"));
    const selectedChip = buttons.find(
      (button) => button.dataset.relationshipEdgeId === selectedEdge.id,
    ) ?? null;
    const requestedControl = pending.control === "chip"
      ? null
      : buttons.find(
        (button) => button.dataset.relationshipControl === pending.control,
      ) ?? null;
    pendingRelationshipFocusRef.current = null;
    relationshipNavigationFocusTarget(requestedControl, selectedChip)?.focus({
      preventScroll: true,
    });
  }, [selectedEdge?.id]);

  const navigateRelationship = (
    id: string,
    control: RelationshipNavigationControl,
  ) => {
    pendingRelationshipFocusRef.current = id === selectedEdge?.id
      ? null
      : { edgeId: id, control };
    onSelectEdge(id);
  };

  if (mode === "evidence" && selectedEdge) {
    return (
      <EvidenceInspector
        key={selectedEdge.id}
        focusRootRef={inspectorRootRef}
        edge={selectedEdge}
        edgeGroup={selectedEdgeGroup}
        detail={detail}
        detailError={detailError}
        result={result}
        entityName={entityName}
        onClose={onCloseSelection}
        onNavigateEdge={navigateRelationship}
        onReviewed={onEdgeReviewed}
      />
    );
  }

  if (mode === "company" && selectedEntity) {
    return (
      <CompanyPanel
        entity={selectedEntity}
        edges={edges}
        entityName={entityName}
        onClose={onCloseSelection}
        onSelectEdge={onSelectEdge}
      />
    );
  }

  if (mode === "results") {
    if (propagationInProgress) {
      return (
        <div aria-live="polite" style={{ padding: 18 }}>
          <TerminalStatus tone="exposure">PROPAGATION IN PROGRESS</TerminalStatus>
          <p style={{ margin: "12px 0 0", color: "var(--muted)", fontSize: 13, lineHeight: 1.5 }}>
            Evidence conclusions will appear after every activated relationship has been traced.
          </p>
        </div>
      );
    }
    return <SplitResults structural={structuralResults} assumption={assumptionResults} />;
  }

  return (
    <>
      <IngestPanel onIngested={onGraphChanged} />
      <ReviewQueue
        edges={edges.filter((edge) => edge.status === "candidate")}
        entityName={entityName}
        onSelect={onSelectEdge}
        onReviewed={onEdgeReviewed}
      />
    </>
  );
}

function EvidenceInspector({
  focusRootRef,
  edge,
  edgeGroup,
  detail,
  detailError,
  result,
  entityName,
  onClose,
  onNavigateEdge,
  onReviewed,
}: {
  focusRootRef: RefObject<HTMLDivElement | null>;
  edge: Edge;
  edgeGroup: Edge[];
  detail: EdgeDetail | null;
  detailError: string | null;
  result?: EdgeResult;
  entityName: (id: string | null) => string;
  onClose: () => void;
  onNavigateEdge: (id: string, control: RelationshipNavigationControl) => void;
  onReviewed: (edge: Edge) => Promise<void> | void;
}) {
  const [busy, setBusy] = useState<"approve" | "reject" | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);
  const verification = (edge.verification ?? {}) as Record<string, unknown>;
  const overall = verificationOverall(verification);
  const checks = verificationRows(verification);
  const groupIndex = edgeGroup.findIndex((member) => member.id === edge.id);

  const review = async (kind: "approve" | "reject") => {
    setBusy(kind);
    setReviewError(null);
    try {
      const reviewed = await (kind === "approve" ? api.approve(edge.id) : api.reject(edge.id));
      await onReviewed(reviewed);
    } catch (error) {
      setReviewError(`${kind === "approve" ? "Approval" : "Rejection"} failed — ${String(error)}`);
    } finally {
      setBusy(null);
    }
  };

  return (
    <div ref={focusRootRef} className="content-safe terminal-scrollbar">
      <DeskHeader label="Evidence" onClose={onClose} />
      <div className="content-safe" style={panelBodyStyle}>
        {edgeGroup.length > 1 && groupIndex >= 0 && (
          <div
            aria-label="Relationships in this company pair"
            role="group"
            style={relationshipNavigatorStyle}
          >
            <div style={relationshipNavigatorRowStyle}>
              <button
                type="button"
                className="terminal-focus"
                data-relationship-control="previous"
                disabled={groupIndex === 0}
                onClick={() => onNavigateEdge(edgeGroup[groupIndex - 1].id, "previous")}
                style={relationshipNavigatorButtonStyle}
              >
                Previous
              </button>
              <span className="num" style={relationshipNavigatorCountStyle}>
                Relationship {groupIndex + 1} of {edgeGroup.length}
              </span>
              <button
                type="button"
                className="terminal-focus"
                data-relationship-control="next"
                disabled={groupIndex === edgeGroup.length - 1}
                onClick={() => onNavigateEdge(edgeGroup[groupIndex + 1].id, "next")}
                style={relationshipNavigatorButtonStyle}
              >
                Next
              </button>
            </div>
            <div style={relationshipChipListStyle}>
              {edgeGroup.map((member, index) => (
                <button
                  key={member.id}
                  type="button"
                  className="terminal-focus"
                  aria-label={`${member.relationship_type.replace(/_/g, " ")}, relationship ${index + 1} of ${edgeGroup.length}`}
                  aria-current={member.id === edge.id ? "true" : undefined}
                  data-relationship-edge-id={member.id}
                  onClick={() => onNavigateEdge(member.id, "chip")}
                  style={relationshipChipStyle(member.id === edge.id)}
                >
                  {member.relationship_type.replace(/_/g, " ")}
                </button>
              ))}
            </div>
          </div>
        )}
        <div style={{ fontSize: 15, fontWeight: 700 }}>
          {entityName(edge.source_entity_id)} → {entityName(edge.target_entity_id)}
        </div>
        <Badge status={edge.status} evidence={edge.evidence_class} />
        {detailError && <p role="alert" className="content-safe" style={errorStyle}>{detailError}</p>}
        {detail?.passage_text && (
          <blockquote className="content-safe" style={passageStyle}>&ldquo;{detail.passage_text}&rdquo;</blockquote>
        )}
        {detail?.document_title && (
          <DocumentLink title={detail.document_title} url={detail.document_url} />
        )}
        <Field label="Relationship" value={edge.relationship_type.replace(/_/g, " ")} />
        <Field label="Metric" value={edge.metric ?? "—"} />
        <Field label="Value" mono value={formatFinancialValue(edge.value, edge.unit)} />
        <Field label="Period" mono value={edge.period ?? "—"} />
        {result && (
          <Field
            label="Scenario result"
            mono
            value={
              result.value != null
                ? `${formatFinancialValue(result.value, result.unit)} · ${result.kind}`
                : `unknown · ${result.kind}`
            }
          />
        )}
        {edge.permitted_operation && (
          <Field label="Permitted operation" value={edge.permitted_operation} />
        )}
        {edge.unsupported_operation && (
          <Field label="Unsupported operation" value={edge.unsupported_operation} />
        )}

        <div style={{ marginTop: 16 }}>
          <div style={verificationHeaderStyle}>
            <TerminalLabel>Mechanical checks</TerminalLabel>
            <TerminalStatus tone={verificationTone(overall)}>
              {overall.toUpperCase()}
            </TerminalStatus>
          </div>
          <div style={checkListStyle}>
            {checks.map((check) => (
              <CheckRow
                key={check.key}
                label={check.label}
                display={check.display}
                state={check.state}
              />
            ))}
          </div>
        </div>

        {edge.status === "candidate" && (
          <div style={reviewBlockStyle}>
            <p style={semanticNoteStyle}>
              Mechanical checks validate the citation shape. Semantic approval remains a human decision.
            </p>
            <div style={reviewActionsStyle}>
              <ReviewButton
                kind="approve"
                busy={busy}
                onClick={() => void review("approve")}
              />
              <ReviewButton
                kind="reject"
                busy={busy}
                onClick={() => void review("reject")}
              />
            </div>
          </div>
        )}

        {edge.status !== "candidate" && (
          <TerminalStatus tone={edge.status === "approved" ? "pass" : "impact"} style={finalStateStyle}>
            REVIEW {edge.status.toUpperCase()}
          </TerminalStatus>
        )}
        {reviewError && <PanelError>{reviewError}</PanelError>}
      </div>
    </div>
  );
}

function CheckRow({
  label,
  display,
  state,
}: Omit<VerificationRow, "key">) {
  return (
    <div style={checkRowStyle}>
      <span>{label}</span>
      <TerminalStatus tone={verificationTone(state)}>{display}</TerminalStatus>
    </div>
  );
}

function verificationTone(state: VerificationRow["state"]): "pass" | "impact" | "neutral" {
  if (state === "pass") return "pass";
  if (state === "flag") return "impact";
  return "neutral";
}

function ReviewButton({
  kind,
  busy,
  onClick,
}: {
  kind: "approve" | "reject";
  busy: "approve" | "reject" | null;
  onClick: () => void;
}) {
  const approve = kind === "approve";
  return (
    <TerminalButton
      type="button"
      tone={approve ? "pass" : "impact"}
      disabled={busy !== null}
      onClick={onClick}
      style={reviewButtonStyle(approve)}
    >
      {busy === kind ? `${approve ? "Approving" : "Rejecting"}…` : approve ? "Approve" : "Reject"}
    </TerminalButton>
  );
}

function CompanyPanel({
  entity,
  edges,
  entityName,
  onClose,
  onSelectEdge,
}: {
  entity: Entity;
  edges: Edge[];
  entityName: (id: string | null) => string;
  onClose: () => void;
  onSelectEdge: (id: string) => void;
}) {
  const outgoing = edges.filter((edge) => edge.source_entity_id === entity.id);
  const incoming = edges.filter((edge) => edge.target_entity_id === entity.id);
  const exposure = [...outgoing, ...incoming]
    .filter(
      (edge) =>
        edge.unit === "usd_billions" && edge.status === "approved" && edge.value != null,
    )
    .reduce((sum, edge) => sum + (edge.value ?? 0), 0);

  const line = (edge: Edge, direction: "out" | "in") => {
    const other =
      direction === "out" ? edge.target_entity_id : edge.source_entity_id;
    return (
      <button
        key={`${edge.id}-${direction}`}
        type="button"
        className="terminal-focus"
        onClick={() => onSelectEdge(edge.id)}
        style={relationshipRowStyle}
      >
        <span style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
          <span>
            {direction === "out" ? "→ " : "← "}
            {entityName(other)}
          </span>
          <span
            className="num"
            style={{ color: edge.status === "candidate" ? "var(--candidate)" : "var(--text)" }}
          >
            {formatFinancialValue(edge.value, edge.unit)}
          </span>
        </span>
        <span style={relationshipMetaStyle}>
          {edge.relationship_type.replace(/_/g, " ")} · {edge.status}
        </span>
      </button>
    );
  };

  return (
    <div>
      <DeskHeader label="Company" onClose={onClose} />
      <div className="content-safe" style={panelBodyStyle}>
        <div style={{ fontSize: 17, fontWeight: 700 }}>{entity.name}</div>
        <div className="num" style={companyTypeStyle}>
          {(ENTITY_LABEL[entity.entity_type ?? ""] ?? entity.entity_type ?? "—").toUpperCase()}
        </div>
        <div style={{ display: "flex", gap: 20, marginTop: 14 }}>
          <Metric label="Relationships" value={String(outgoing.length + incoming.length)} />
          <Metric
            label="Disclosed exposure"
            value={exposure > 0 ? formatFinancialValue(exposure, "usd_billions") : "—"}
            accent="var(--exposure)"
          />
        </div>
        {outgoing.length > 0 && <MiniTitle>Outgoing</MiniTitle>}
        {outgoing.map((edge) => line(edge, "out"))}
        {incoming.length > 0 && <MiniTitle>Incoming</MiniTitle>}
        {incoming.map((edge) => line(edge, "in"))}
      </div>
    </div>
  );
}

function SplitResults({
  structural,
  assumption,
}: {
  structural: EdgeResult[];
  assumption: EdgeResult[];
}) {
  return (
    <div style={{ display: "flex", flexDirection: "column", height: "100%" }}>
      <SectionTitle>Structural impact · evidence-backed</SectionTitle>
      <div style={structuralResultsStyle}>
        {structural.length === 0 && <Empty>No structural edge is touched by this shock.</Empty>}
        {structural.map((result) => (
          <ResultRow key={result.edge_id} result={result} />
        ))}
      </div>
      <SectionTitle>Assumption-dependent · no number</SectionTitle>
      <div style={{ padding: "0 18px 18px" }}>
        {assumption.length === 0 && <Empty>Nothing reached beyond the evidence.</Empty>}
        {assumption.map((result) => (
          <ResultRow key={result.edge_id} result={result} muted />
        ))}
      </div>
    </div>
  );
}

function ResultRow({ result, muted }: { result: EdgeResult; muted?: boolean }) {
  const color =
    result.kind === "impact"
      ? "var(--impact)"
      : result.kind === "exposure"
        ? "var(--exposure)"
        : "var(--amber)";
  return (
    <div className="content-safe" style={resultRowStyle}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", gap: 8, minWidth: 0 }}>
        <span className="content-safe" style={{ fontSize: 13, fontWeight: 600 }}>
          {result.source_entity} → {result.target_entity}
        </span>
        <span className="num" style={{ fontSize: 15, fontWeight: 700, color: muted ? "var(--muted)" : color }}>
          {result.value != null ? formatFinancialValue(result.value, result.unit) : "unknown"}
        </span>
      </div>
      <div className="content-safe" style={resultMetaStyle}>
        {result.relationship_type.replace(/_/g, " ")} · {result.kind}
      </div>
      <div className="content-safe" style={{ fontSize: 11.5, color: muted ? "var(--muted)" : "var(--text)", marginTop: 6, lineHeight: 1.45 }}>
        {result.caveat}
      </div>
    </div>
  );
}

function IngestPanel({ onIngested }: { onIngested: () => Promise<void> | void }) {
  const [open, setOpen] = useState(false);
  const [mode, setMode] = useState<"url" | "text">("url");
  const [title, setTitle] = useState("");
  const [url, setUrl] = useState("");
  const [text, setText] = useState("");
  const [provider, setProvider] = useState("fallback");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const ready = mode === "url" ? Boolean(url) : Boolean(title && text);

  const extract = async () => {
    if (!ready) return;
    setBusy(true);
    setMessage(null);
    try {
      setMessage(mode === "url" ? "Reading filing…" : "Extracting…");
      const document =
        mode === "url"
          ? await api.documentFromUrl({ url, title: title || undefined })
          : await api.createDocument({ title, raw_text: text });
      const response = await api.extractDocument(document.id, provider);
      setMessage(
        `${response.candidates_created} candidate${response.candidates_created === 1 ? "" : "s"} found via ${response.provider}`,
      );
      setText("");
      setUrl("");
      setTitle("");
      await onIngested();
    } catch (error) {
      setMessage(`Failed — ${String(error)}`);
    } finally {
      setBusy(false);
    }
  };

  const tab = (tabMode: "url" | "text", label: string) => (
    <button
      type="button"
      onClick={() => setMode(tabMode)}
      className="terminal-focus"
      style={ingestTabStyle(mode === tabMode)}
    >
      {label}
    </button>
  );

  return (
    <div style={{ borderBottom: "1px solid var(--hairline)" }}>
      <button
        type="button"
        onClick={() => setOpen((visible) => !visible)}
        className="terminal-focus"
        aria-expanded={open}
        style={ingestToggleStyle}
      >
        {open ? "− Ingest a filing" : "+ Ingest a filing"}
      </button>
      {open && (
        <div style={ingestFormStyle}>
          <div style={{ display: "flex", gap: 6 }}>
            {tab("url", "From SEC URL")}
            {tab("text", "Paste text")}
          </div>
          <input
            aria-label="Filing title"
            placeholder="Filing title (optional)"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            style={inputStyle}
          />
          {mode === "url" ? (
            <input
              aria-label="SEC filing URL"
              placeholder="https://www.sec.gov/Archives/edgar/…"
              value={url}
              onChange={(event) => setUrl(event.target.value)}
              style={inputStyle}
            />
          ) : (
            <textarea
              aria-label="Filing text"
              placeholder="Paste the filing passage(s) here…"
              value={text}
              onChange={(event) => setText(event.target.value)}
              rows={5}
              style={{ ...inputStyle, resize: "vertical", fontFamily: "inherit" }}
            />
          )}
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <select
              aria-label="Extraction provider"
              value={provider}
              onChange={(event) => setProvider(event.target.value)}
              style={{ ...inputStyle, flex: 1 }}
            >
              <option value="fallback">fallback (offline, no key)</option>
              <option value="openai">openai (needs API key)</option>
            </select>
            <TerminalButton
              type="button"
              tone="exposure"
              onClick={() => void extract()}
              disabled={busy || !ready}
              style={extractButtonStyle}
            >
              {busy ? "Working…" : "Extract"}
            </TerminalButton>
          </div>
          {message && <div className="content-safe" style={{ fontSize: 11.5, color: "var(--exposure)" }}>{message}</div>}
          <p style={ingestNoteStyle}>
            A SEC URL is read via Jina Reader, then the LLM proposes typed, cited candidates — code
            verifies them and you approve below. The offline fallback matches entities already in the
            graph; the LLM can name new ones.
          </p>
        </div>
      )}
    </div>
  );
}

function ReviewQueue({
  edges,
  entityName,
  onSelect,
  onReviewed,
}: {
  edges: Edge[];
  entityName: (id: string | null) => string;
  onSelect: (id: string) => void;
  onReviewed: (edge: Edge) => Promise<void> | void;
}) {
  const [busy, setBusy] = useState<string | null>(null);
  const [reviewError, setReviewError] = useState<string | null>(null);

  const review = async (edge: Edge, kind: "approve" | "reject") => {
    setBusy(edge.id);
    setReviewError(null);
    try {
      const reviewed = await (kind === "approve" ? api.approve(edge.id) : api.reject(edge.id));
      await onReviewed(reviewed);
    } catch (error) {
      setReviewError(
        `${kind === "approve" ? "Approval" : "Rejection"} failed for ${entityName(edge.source_entity_id)} → ${entityName(edge.target_entity_id)} — ${String(error)}`,
      );
    } finally {
      setBusy(null);
    }
  };

  return (
    <div>
      <SectionTitle>Review queue</SectionTitle>
      <div style={{ padding: "0 18px 18px" }}>
        {reviewError && <PanelError>{reviewError}</PanelError>}
        {edges.length === 0 && <Empty>No candidates awaiting review.</Empty>}
        {edges.map((edge) => {
          const verification = (edge.verification ?? {}) as Record<string, unknown>;
          const pass = verification.overall === "pass";
          return (
            <div key={edge.id} style={queueRowStyle}>
              <button
                type="button"
                className="terminal-focus content-safe"
                onClick={() => onSelect(edge.id)}
                style={queueSelectStyle}
              >
                <span style={{ display: "flex", justifyContent: "space-between", gap: 8, minWidth: 0 }}>
                  <span className="content-safe" style={{ fontSize: 13, fontWeight: 600 }}>
                    {entityName(edge.source_entity_id)} → {entityName(edge.target_entity_id)}
                  </span>
                  <TerminalStatus tone={pass ? "pass" : "impact"}>
                    {pass ? "PASS" : "FLAG"}
                  </TerminalStatus>
                </span>
                <span className="content-safe" style={queueMetaStyle}>
                  {edge.relationship_type.replace(/_/g, " ")} · {formatFinancialValue(edge.value, edge.unit)}
                </span>
              </button>
              <div style={reviewActionsStyle}>
                <TerminalButton
                  type="button"
                  tone="pass"
                  disabled={busy === edge.id}
                  onClick={() => void review(edge, "approve")}
                  style={reviewButtonStyle(true)}
                >
                  Approve
                </TerminalButton>
                <TerminalButton
                  type="button"
                  tone="impact"
                  disabled={busy === edge.id}
                  onClick={() => void review(edge, "reject")}
                  style={reviewButtonStyle(false)}
                >
                  Reject
                </TerminalButton>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function DeskHeader({ label, onClose }: { label: ReactNode; onClose: () => void }) {
  return (
    <div style={deskHeaderStyle}>
      <TerminalLabel>{label}</TerminalLabel>
      <button
        type="button"
        onClick={onClose}
        className="terminal-focus"
        aria-label={`Close ${String(label).toLowerCase()}`}
        style={closeButtonStyle}
      >
        ×
      </button>
    </div>
  );
}

function DocumentLink({ title, url }: { title: string; url: string | null }) {
  const href = safeHttpUrl(url);
  return (
    <div className="content-safe" style={{ fontSize: 11, marginBottom: 4 }}>
      {href ? (
        <a href={href} target="_blank" rel="noreferrer noopener" style={{ color: "var(--candidate)" }}>
          {title} ↗
        </a>
      ) : (
        <span style={{ color: "var(--muted)" }}>{title}</span>
      )}
    </div>
  );
}

function safeHttpUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    const parsed = new URL(url);
    return parsed.protocol === "http:" || parsed.protocol === "https:" ? url : null;
  } catch {
    return null;
  }
}

function Metric({ label, value, accent }: { label: string; value: string; accent?: string }) {
  return (
    <div style={{ textAlign: "right" }}>
      <div className="num" style={{ fontSize: 18, fontWeight: 700, color: accent ?? "var(--text)", lineHeight: 1 }}>
        {value}
      </div>
      <div style={metricLabelStyle}>{label.toUpperCase()}</div>
    </div>
  );
}

function SectionTitle({ children }: { children: ReactNode }) {
  return <div style={sectionTitleStyle}>{children}</div>;
}

function Field({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div style={{ marginTop: 10 }}>
      <div style={fieldLabelStyle}>{label.toUpperCase()}</div>
      <div className={mono ? "num content-safe" : "content-safe"} style={{ fontSize: 13, marginTop: 2, lineHeight: 1.4 }}>
        {value}
      </div>
    </div>
  );
}

function Badge({ status, evidence }: { status: string; evidence: string }) {
  const candidate = status === "candidate";
  return (
    <span className="num" style={badgeStyle(candidate)}>
      {status.toUpperCase()} · {evidence.toUpperCase()}
    </span>
  );
}

function PanelError({ children }: { children: ReactNode }) {
  return (
    <div role="alert" className="content-safe" style={errorStyle}>
      {children}
    </div>
  );
}

function Empty({ children }: { children: ReactNode }) {
  return <div style={{ fontSize: 12.5, color: "var(--muted)", padding: "14px 0" }}>{children}</div>;
}

function MiniTitle({ children }: { children: ReactNode }) {
  return <div style={miniTitleStyle}>{children}</div>;
}

const panelBodyStyle: CSSProperties = { padding: "8px 18px 18px" };
const relationshipNavigatorStyle: CSSProperties = {
  marginBottom: 12,
  border: "1px solid var(--hairline)",
  borderRadius: 0,
};
const relationshipNavigatorRowStyle: CSSProperties = {
  display: "grid",
  gridTemplateColumns: "auto 1fr auto",
  alignItems: "center",
  borderBottom: "1px solid var(--hairline)",
};
const relationshipNavigatorButtonStyle: CSSProperties = {
  alignSelf: "stretch",
  padding: "7px 8px",
  border: 0,
  borderRadius: 0,
  background: "transparent",
  color: "var(--muted)",
  fontSize: 10,
  fontWeight: 700,
  textTransform: "uppercase",
  cursor: "pointer",
};
const relationshipNavigatorCountStyle: CSSProperties = {
  padding: "7px 6px",
  borderLeft: "1px solid var(--hairline)",
  borderRight: "1px solid var(--hairline)",
  color: "var(--text)",
  fontSize: 10.5,
  textAlign: "center",
};
const relationshipChipListStyle: CSSProperties = {
  display: "flex",
  flexWrap: "wrap",
  gap: 5,
  padding: 7,
};
const deskHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "16px 18px 0",
};
const closeButtonStyle: CSSProperties = {
  border: 0,
  borderRadius: 0,
  background: "transparent",
  color: "var(--muted)",
  fontSize: 18,
  lineHeight: 1,
  cursor: "pointer",
};
const passageStyle: CSSProperties = {
  margin: "12px 0 4px",
  padding: "10px 12px",
  borderLeft: "3px solid var(--exposure)",
  background: "var(--bg)",
  fontSize: 13,
  lineHeight: 1.5,
  color: "var(--text)",
};
const verificationHeaderStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  paddingBottom: 7,
};
const checkListStyle: CSSProperties = { border: "1px solid var(--hairline)" };
const checkRowStyle: CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  minHeight: 32,
  padding: "0 9px",
  borderBottom: "1px solid var(--hairline)",
  fontSize: 11.5,
};
const reviewBlockStyle: CSSProperties = {
  marginTop: 10,
  paddingTop: 10,
  borderTop: "1px solid var(--hairline)",
};
const semanticNoteStyle: CSSProperties = {
  margin: "0 0 9px",
  color: "var(--muted)",
  fontSize: 11,
  lineHeight: 1.45,
};
const reviewActionsStyle: CSSProperties = { display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7 };
const finalStateStyle: CSSProperties = {
  display: "block",
  marginTop: 12,
  padding: "8px 9px",
  border: "1px solid currentColor",
  textAlign: "center",
};
const companyTypeStyle: CSSProperties = {
  fontSize: 10.5,
  color: "var(--muted)",
  marginTop: 3,
  letterSpacing: "0.05em",
};
const relationshipRowStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  width: "100%",
  padding: "9px 0",
  border: 0,
  borderBottom: "1px solid var(--hairline)",
  borderRadius: 0,
  background: "transparent",
  color: "var(--text)",
  fontSize: 12.5,
  textAlign: "left",
  cursor: "pointer",
};
const relationshipMetaStyle: CSSProperties = {
  fontSize: 10.5,
  color: "var(--muted)",
  marginTop: 3,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};
const structuralResultsStyle: CSSProperties = {
  padding: "0 18px 14px",
  background: "color-mix(in srgb, var(--impact) 7%, transparent)",
};
const resultRowStyle: CSSProperties = { padding: "12px 0", borderBottom: "1px solid var(--hairline)" };
const resultMetaStyle: CSSProperties = {
  fontSize: 11,
  color: "var(--muted)",
  marginTop: 4,
  textTransform: "uppercase",
  letterSpacing: "0.04em",
};
const ingestToggleStyle: CSSProperties = {
  width: "100%",
  padding: "14px 18px",
  border: 0,
  borderRadius: 0,
  background: "none",
  color: "var(--muted)",
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.08em",
  textAlign: "left",
  textTransform: "uppercase",
  cursor: "pointer",
};
const ingestFormStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  gap: 8,
  padding: "0 18px 16px",
};
const inputStyle: CSSProperties = {
  width: "100%",
  padding: "7px 9px",
  border: "1px solid var(--hairline)",
  borderRadius: 0,
  background: "var(--bg)",
  color: "var(--text)",
  fontSize: 12.5,
};
const extractButtonStyle: CSSProperties = {
  padding: "8px 14px",
  border: "1px solid var(--exposure)",
  borderRadius: 0,
  background: "transparent",
  fontSize: 12,
  fontWeight: 700,
  cursor: "pointer",
};
const ingestNoteStyle: CSSProperties = {
  margin: 0,
  color: "var(--muted)",
  fontSize: 10.5,
  lineHeight: 1.45,
};
const queueRowStyle: CSSProperties = { padding: "12px 0", borderBottom: "1px solid var(--hairline)" };
const queueSelectStyle: CSSProperties = {
  display: "flex",
  flexDirection: "column",
  width: "100%",
  padding: 0,
  border: 0,
  borderRadius: 0,
  background: "transparent",
  color: "var(--text)",
  textAlign: "left",
  cursor: "pointer",
};
const queueMetaStyle: CSSProperties = {
  marginTop: 4,
  color: "var(--muted)",
  fontSize: 11,
  letterSpacing: "0.04em",
  textTransform: "uppercase",
};
const metricLabelStyle: CSSProperties = {
  marginTop: 3,
  color: "var(--muted)",
  fontSize: 10,
  letterSpacing: "0.04em",
};
const sectionTitleStyle: CSSProperties = {
  padding: "16px 18px 10px",
  color: "var(--muted)",
  fontSize: 11,
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};
const fieldLabelStyle: CSSProperties = {
  color: "var(--muted)",
  fontSize: 10,
  letterSpacing: "0.05em",
};
const errorStyle: CSSProperties = {
  marginTop: 10,
  padding: "8px 9px",
  border: "1px solid var(--impact)",
  color: "var(--impact)",
  fontSize: 11.5,
  lineHeight: 1.4,
};
const miniTitleStyle: CSSProperties = {
  margin: "16px 0 4px",
  color: "var(--muted)",
  fontSize: 10,
  fontWeight: 700,
  letterSpacing: "0.08em",
  textTransform: "uppercase",
};

function reviewButtonStyle(approve: boolean): CSSProperties {
  return {
    width: "100%",
    padding: "7px 0",
    border: `1px solid ${approve ? "var(--pass)" : "var(--impact)"}`,
    borderRadius: 0,
    background: "transparent",
    fontSize: 12,
    fontWeight: 700,
    cursor: "pointer",
  };
}

function ingestTabStyle(active: boolean): CSSProperties {
  return {
    padding: "4px 10px",
    border: "1px solid var(--hairline)",
    borderRadius: 0,
    background: active ? "var(--surface-raised)" : "transparent",
    color: active ? "var(--text)" : "var(--muted)",
    fontSize: 11,
    cursor: "pointer",
  };
}

function badgeStyle(candidate: boolean): CSSProperties {
  return {
    display: "inline-block",
    marginTop: 8,
    padding: "2px 7px",
    border: `1px solid ${candidate ? "var(--candidate)" : "var(--hairline)"}`,
    borderRadius: 0,
    color: candidate ? "var(--candidate)" : "var(--muted)",
    fontSize: 10,
  };
}

function relationshipChipStyle(selected: boolean): CSSProperties {
  return {
    padding: "3px 6px",
    border: `1px solid ${selected ? "var(--candidate)" : "var(--hairline)"}`,
    borderRadius: 0,
    background: selected ? "var(--surface-raised)" : "transparent",
    color: selected ? "var(--text)" : "var(--muted)",
    fontSize: 9.5,
    lineHeight: 1.2,
    textTransform: "uppercase",
    cursor: "pointer",
  };
}
