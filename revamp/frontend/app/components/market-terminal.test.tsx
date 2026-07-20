import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { ExposureDesk, MarketStrip, TerminalDataStatus } from "./exposure-desk";
import { ScenarioBook, type ScenarioLayers } from "./scenario-book";
import { RiskTape } from "./risk-tape";
import { EvidenceDesk, relationshipNavigationFocusTarget } from "./evidence-desk";
import {
  COPILOT_CONTENT_CLASSES,
  COPILOT_PANEL_STYLE,
  assistantChatMessage,
  dashboardErrorForScenarioRun,
  deskSnapshotFromChatRun,
  performChatScenarioAction,
  focusedEdgeIdAfterGroupBlur,
  groupedEdgeActivationForInput,
  groupedEdgeActivationId,
  groupedEdgeTraceKey,
  renderGroupedEdgeLabel,
  runSnapshotAfterScenarioView,
  selectedEdgeGroupFor,
} from "../page";
import type { ChatAction } from "../lib/chat-actions";

const layers: ScenarioLayers = {
  impact: true,
  exposure: true,
  unresolved: true,
  candidate: true,
  inactive: true,
};

const idleMetrics = {
  entityCount: 2,
  approvedEdgeCount: 1,
  candidateCount: 1,
  impactTotal: null,
  exposureTotal: null,
  unresolvedCount: null,
  evidenceCoverage: 50,
};

describe("market terminal component contracts", () => {
  it("keeps tool actions attached only to their assistant response", () => {
    const actions: ChatAction[] = [{
      tool: "create_scenario",
      args: { name: "OpenAI shock" },
      result: { scenario_id: "scenario-1" },
    }];

    expect(assistantChatMessage("Created.", actions)).toEqual({
      role: "assistant",
      content: "Created.",
      actions,
    });
  });

  it("runs a READY chat card with its exact scenario id", async () => {
    const calls: string[] = [];

    const error = await performChatScenarioAction("run", "scenario-from-chat", undefined, {
      run: async (id) => { calls.push(`run:${id}`); },
      view: async (id) => { calls.push(`view:${id}`); },
      close: () => { calls.push("close"); },
    });

    expect(error).toBeNull();
    expect(calls).toEqual(["run:scenario-from-chat", "close"]);
  });

  it("views a COMPLETE chat card without running the scenario again", async () => {
    const calls: string[] = [];

    const error = await performChatScenarioAction("view", "completed-scenario", undefined, {
      run: async (id) => { calls.push(`run:${id}`); },
      view: async (id) => { calls.push(`view:${id}`); },
      close: () => { calls.push("close"); },
    });

    expect(error).toBeNull();
    expect(calls).toEqual(["view:completed-scenario", "close"]);
  });

  it("keeps chat card failures local and leaves the dock open", async () => {
    const calls: string[] = [];

    const error = await performChatScenarioAction("run", "scenario-failure", undefined, {
      run: async () => { throw new Error("run rejected"); },
      view: async () => undefined,
      close: () => { calls.push("close"); },
    });

    expect(error).toContain("run rejected");
    expect(calls).toEqual([]);
  });

  it("suppresses dashboard errors only when the chat card owns the run error", () => {
    const error = new Error("run rejected");

    expect(dashboardErrorForScenarioRun(error, { errorOwner: "card" })).toBeNull();
    expect(dashboardErrorForScenarioRun(error, { errorOwner: "dashboard" }))
      .toContain("run rejected");
  });

  it("clears a prior scenario snapshot when viewing a different completed scenario", () => {
    const snapshot = { scenarioId: "scenario-a" } as never;

    expect(runSnapshotAfterScenarioView(snapshot, "scenario-b")).toBeNull();
    expect(runSnapshotAfterScenarioView(snapshot, "scenario-a")).toBe(snapshot);
  });

  it("restores a completed chat run as the viewed desk snapshot", () => {
    const run = {
      results: [{ edge_id: "edge-b" }],
      totals: { impact_total: 4, exposure_total: 9, unresolved_count: 1 },
    } as never;

    expect(deskSnapshotFromChatRun("scenario-b", run)).toMatchObject({
      scenarioId: "scenario-b",
      totals: run.totals,
      results: { "edge-b": run.results[0] },
    });
  });

  it("keeps the Copilot inside a narrow viewport", () => {
    expect(COPILOT_PANEL_STYLE).toMatchObject({
      right: 12,
      width: "min(400px, calc(100vw - 24px))",
      maxWidth: "calc(100vw - 24px)",
    });
  });

  it("keeps grouped edge labels calm until the connection is active", () => {
    expect(renderGroupedEdgeLabel({ count: 3, active: false })).toBe("3 relationships");
    expect(renderGroupedEdgeLabel({ count: 1, active: false })).toBeNull();
    expect(
      renderGroupedEdgeLabel({
        count: 1,
        active: true,
        relationship: "take or pay",
      }),
    ).toBe("take or pay");
  });

  it("activates an underlying group member instead of the synthetic edge id", () => {
    const activationId = groupedEdgeActivationId({
      memberIds: ["edge-investment", "edge-take-or-pay"],
      representativeId: "edge-take-or-pay",
      selectedId: null,
    });

    expect(activationId).toBe("edge-take-or-pay");
    expect(activationId).not.toBe("microsoft->coreweave");
    expect(
      groupedEdgeActivationId({
        memberIds: ["edge-investment", "edge-take-or-pay"],
        representativeId: "edge-take-or-pay",
        selectedId: "edge-investment",
      }),
    ).toBe("edge-investment");
  });

  it("uses the same underlying activation id for click, Enter, and Space", () => {
    const activationId = "edge-take-or-pay";

    expect(groupedEdgeActivationForInput("click", activationId)).toBe(activationId);
    expect(groupedEdgeActivationForInput("Enter", activationId)).toBe(activationId);
    expect(groupedEdgeActivationForInput(" ", activationId)).toBe(activationId);
    expect(groupedEdgeActivationForInput("Escape", activationId)).toBeNull();
  });

  it("changes the grouped path key for every underlying propagation hop", () => {
    const memberIds = ["edge-a", "edge-b"];

    expect(groupedEdgeTraceKey("edge-a", memberIds)).toBe("edge-a");
    expect(groupedEdgeTraceKey("edge-b", memberIds)).toBe("edge-b");
    expect(groupedEdgeTraceKey("other-edge", memberIds)).toBe("inactive");
    expect(groupedEdgeTraceKey(null, memberIds)).toBe("inactive");
  });

  it("derives the selected underlying relationship group", () => {
    const edgeA = { id: "edge-a" } as never;
    const edgeB = { id: "edge-b" } as never;
    const groups = [{ edges: [edgeA, edgeB] }] as never;

    expect(selectedEdgeGroupFor(groups, "edge-b")).toEqual([edgeA, edgeB]);
    expect(selectedEdgeGroupFor(groups, "edge-missing")).toEqual([]);
    expect(selectedEdgeGroupFor(groups, null)).toEqual([]);
  });

  it("clears group focus when the representative changes before blur", () => {
    const memberIds = ["impact-representative", "exposure-representative"];

    expect(focusedEdgeIdAfterGroupBlur("impact-representative", memberIds)).toBeNull();
    expect(focusedEdgeIdAfterGroupBlur("unrelated-edge", memberIds)).toBe("unrelated-edge");
  });

  it("renders the semantic four-zone exposure desk", () => {
    const html = renderToStaticMarkup(
      <ExposureDesk
        header="header"
        marketStrip="market"
        scenarioBook="scenarios"
        network="network"
        evidence="evidence"
        riskTape="risk"
      />,
    );

    expect(html).toContain('<main class="exposure-desk"');
    expect(html).toContain('<header class="terminal-header"');
    expect(html).toContain('class="market-strip" aria-label="Market summary"');
    expect(html).toContain('class="desk-workspace"');
    expect(html).toContain('class="scenario-column"');
    expect(html).toContain('class="network-column"');
    expect(html).toContain('class="evidence-column"');
    expect(html).toContain('<footer class="risk-tape"');
    expect(html).toMatch(/class="risk-tape"[^>]*overflow-x:auto/);
    expect(html).not.toMatch(/class="risk-tape"[^>]*overflow-x:hidden/);
  });

  it("contains Evidence Desk and Copilot external content without blocking the Risk Tape", () => {
    const edge = evidenceEdge("edge-investment", "investment");
    const evidenceHtml = renderToStaticMarkup(
      <EvidenceDesk
        selectedEdge={edge}
        selectedEdgeGroup={[edge]}
        selectedEntity={null}
        detail={{
          passage_text: "https://www.sec.gov/Archives/edgar/data/unbroken-passage",
          document_title: "UnbrokenExternalDocumentTitle",
          document_url: "https://www.sec.gov/Archives/edgar/data/unbroken-document-url",
        } as never}
        detailError="UnbrokenExternalEvidenceError"
        structuralResults={[]}
        assumptionResults={[]}
        hasActiveResult={false}
        propagationInProgress={false}
        edges={[edge]}
        entityName={(id) => id ?? "—"}
        onCloseSelection={() => undefined}
        onSelectEdge={() => undefined}
        onGraphChanged={() => undefined}
        onEdgeReviewed={() => undefined}
      />,
    );

    expect(evidenceHtml).toContain("content-safe");
    expect(evidenceHtml).toContain("terminal-scrollbar");
    expect(COPILOT_CONTENT_CLASSES).toMatchObject({
      scrollerClassName: expect.stringContaining("terminal-scrollbar"),
      messageClassName: expect.stringContaining("content-safe"),
      inputRowClassName: expect.stringContaining("content-safe"),
    });
  });

  it("contains API-derived result text at each wrapping boundary", () => {
    const source = "UnbrokenResultSourceEntityName";
    const target = "UnbrokenResultTargetEntityName";
    const relationship = "UnbrokenResultRelationship";
    const caveat = "UnbrokenResultCaveatText";
    const html = renderToStaticMarkup(
      <EvidenceDesk
        selectedEdge={null}
        selectedEdgeGroup={[]}
        selectedEntity={null}
        structuralResults={[{
          edge_id: "edge-result",
          source_entity: source,
          target_entity: target,
          relationship_type: relationship,
          kind: "impact",
          value: 1,
          unit: "usd_billions",
          caveat,
        } as never]}
        assumptionResults={[]}
        hasActiveResult
        propagationInProgress={false}
        edges={[]}
        entityName={(id) => id ?? "—"}
        onCloseSelection={() => undefined}
        onSelectEdge={() => undefined}
        onGraphChanged={() => undefined}
        onEdgeReviewed={() => undefined}
      />,
    );

    expect(html).toMatch(new RegExp(`class="content-safe"[^>]*>${source} → ${target}</span>`));
    expect(html).toMatch(new RegExp(`class="content-safe"[^>]*>${relationship} · impact</div>`));
    expect(html).toMatch(new RegExp(`class="content-safe"[^>]*>${caveat}</div>`));
  });

  it("contains API-derived Review Queue entity and relationship text", () => {
    const source = "UnbrokenReviewSourceEntityName";
    const target = "UnbrokenReviewTargetEntityName";
    const relationship = "UnbrokenReviewRelationship";
    const edge = {
      ...evidenceEdge("edge-review", relationship),
      status: "candidate",
    } as never;
    const html = renderToStaticMarkup(
      <EvidenceDesk
        selectedEdge={null}
        selectedEdgeGroup={[]}
        selectedEntity={null}
        structuralResults={[]}
        assumptionResults={[]}
        hasActiveResult={false}
        propagationInProgress={false}
        edges={[edge]}
        entityName={(id) => id === "microsoft" ? source : id === "coreweave" ? target : id ?? "—"}
        onCloseSelection={() => undefined}
        onSelectEdge={() => undefined}
        onGraphChanged={() => undefined}
        onEdgeReviewed={() => undefined}
      />,
    );

    expect(html).toMatch(new RegExp(`class="content-safe"[^>]*>${source} → ${target}</span>`));
    expect(html).toMatch(new RegExp(`class="content-safe"[^>]*>${relationship} ·`));
  });

  it("shows idle run metrics as em dashes and idle risk guidance", () => {
    const html = renderToStaticMarkup(
      <>
        <MarketStrip metrics={idleMetrics} scenarioName="Baseline" />
        <RiskTape metrics={idleMetrics} scenarioName="Baseline" identifiableHopCount={null} />
      </>,
    );

    expect(html).toContain("Select and run a scenario");
    expect(html.match(/—/g)?.length).toBeGreaterThanOrEqual(3);
  });

  it("marks the selected square scenario row and renders five controlled layers", () => {
    const html = renderScenarioBook();

    expect(html).toContain('aria-current="true"');
    expect(html.match(/type="checkbox"/g)).toHaveLength(5);
    expect(html.match(/checked=""/g)).toHaveLength(5);
  });

  it("disables scenario selection and hides create controls while running", () => {
    const html = renderScenarioBook({ running: true });

    expect(html).toMatch(/aria-current="true"[^>]*disabled=""/);
    expect(html).not.toContain("+ New scenario");
  });

  it("renders scenario creation failures in the Scenario Book alert region", () => {
    const html = renderScenarioBook({ createError: "Scenario creation failed — request rejected" });

    expect(html).toContain('role="alert"');
    expect(html).toContain("Scenario creation failed — request rejected");
  });

  it("renders edge-detail failures inside the Evidence Desk alert region", () => {
    const edge = {
      id: "edge-a",
      source_entity_id: "amazon",
      target_entity_id: "anthropic",
      relationship_type: "investment",
      evidence_class: "reported",
      status: "approved",
      verification: null,
    } as never;
    const html = renderToStaticMarkup(
      <EvidenceDesk
        selectedEdge={edge}
        selectedEdgeGroup={[edge]}
        selectedEntity={null}
        detail={null}
        detailError="Evidence detail failed — request rejected"
        structuralResults={[]}
        assumptionResults={[]}
        hasActiveResult={false}
        propagationInProgress={false}
        edges={[edge]}
        entityName={(id) => id ?? "—"}
        onCloseSelection={() => undefined}
        onSelectEdge={() => undefined}
        onGraphChanged={() => undefined}
        onEdgeReviewed={() => undefined}
      />,
    );

    expect(html).toContain('role="alert"');
    expect(html).toContain("Evidence detail failed — request rejected");
  });

  it("navigates every relationship in the selected company pair", () => {
    const edgeGroup = [
      evidenceEdge("edge-investment", "investment"),
      evidenceEdge("edge-take-or-pay", "take_or_pay"),
      evidenceEdge("edge-purchase", "purchase_obligation"),
    ];
    const html = renderEvidenceDesk(edgeGroup[1], edgeGroup);

    expect(html).toContain("Relationship 2 of 3");
    expect(html).toContain("take or pay");
    expect(html).toContain("purchase obligation");
    expect(html).toContain('role="group"');
    expect(html).toContain('aria-label="take or pay, relationship 2 of 3"');
    expect(html).toMatch(/>Previous<\/button>/);
    expect(html).toMatch(/>Next<\/button>/);
    expect(html).not.toMatch(/disabled=""[^>]*>Previous<\/button>/);
    expect(html).not.toMatch(/disabled=""[^>]*>Next<\/button>/);
  });

  it("disables grouped relationship navigation only at its boundaries", () => {
    const edgeGroup = [
      evidenceEdge("edge-investment", "investment"),
      evidenceEdge("edge-take-or-pay", "take_or_pay"),
      evidenceEdge("edge-purchase", "purchase_obligation"),
    ];
    const first = renderEvidenceDesk(edgeGroup[0], edgeGroup);
    const last = renderEvidenceDesk(edgeGroup[2], edgeGroup);

    expect(first).toMatch(/disabled=""[^>]*>Previous<\/button>/);
    expect(first).not.toMatch(/disabled=""[^>]*>Next<\/button>/);
    expect(last).not.toMatch(/disabled=""[^>]*>Previous<\/button>/);
    expect(last).toMatch(/disabled=""[^>]*>Next<\/button>/);
  });

  it("omits grouped relationship navigation for a single edge", () => {
    const edge = evidenceEdge("edge-investment", "investment");
    const html = renderEvidenceDesk(edge, [edge]);

    expect(html).not.toContain("Relationships in this company pair");
    expect(html).not.toContain("Relationship 1 of 1");
    expect(html).not.toMatch(/>Previous<\/button>|>Next<\/button>/);
  });

  it("keeps navigator focus on an enabled control and falls back to the selected chip", () => {
    const enabledControl = { disabled: false };
    const disabledControl = { disabled: true };
    const selectedChip = { disabled: false };

    expect(relationshipNavigationFocusTarget(enabledControl, selectedChip)).toBe(enabledControl);
    expect(relationshipNavigationFocusTarget(disabledControl, selectedChip)).toBe(selectedChip);
    expect(relationshipNavigationFocusTarget(null, selectedChip)).toBe(selectedChip);
  });

  it("reports only quantified structural results as identifiable hops", () => {
    const html = renderToStaticMarkup(
      <RiskTape
        metrics={{
          ...idleMetrics,
          impactTotal: 2.7,
          exposureTotal: 8,
          unresolvedCount: 9,
        }}
        scenarioName="Scenario A"
        identifiableHopCount={2}
      />,
    );

    expect(html).toContain("2 identifiable hops");
    expect(html).not.toContain("9 unresolved hops");
  });

  it("uses pass tone for evidence coverage only at 100 percent", () => {
    const partial = renderToStaticMarkup(<MarketStrip metrics={idleMetrics} scenarioName={null} />);
    const complete = renderToStaticMarkup(
      <MarketStrip metrics={{ ...idleMetrics, evidenceCoverage: 100 }} scenarioName={null} />,
    );

    expect(partial).not.toMatch(/terminal-tone-pass[^>]*>.*50%/);
    expect(complete).toMatch(/terminal-tone-pass[^>]*>.*100%/);
  });

  it("distinguishes loading from confirmed live data", () => {
    const loading = renderToStaticMarkup(<TerminalDataStatus status="loading" />);
    const live = renderToStaticMarkup(<TerminalDataStatus status="live" />);

    expect(loading).toContain("LOADING");
    expect(loading).not.toContain("DATA LIVE");
    expect(live).toContain("DATA LIVE");
  });
});

function renderScenarioBook({
  running = false,
  createError = null,
}: { running?: boolean; createError?: string | null } = {}) {
  return renderToStaticMarkup(
    <ScenarioBook
      scenarios={[{ id: "baseline", name: "Baseline", description: null }]}
      selectedId="baseline"
      entities={[]}
      phase={0}
      running={running}
      layers={layers}
      onLayerChange={() => undefined}
      onSelect={() => undefined}
      onCreate={async () => undefined}
      onRun={() => undefined}
      onReset={() => undefined}
      createError={createError}
    />,
  );
}

function evidenceEdge(id: string, relationshipType: string) {
  return {
    id,
    source_entity_id: "microsoft",
    target_entity_id: "coreweave",
    relationship_type: relationshipType,
    evidence_class: "reported",
    status: "approved",
    verification: null,
  } as never;
}

function renderEvidenceDesk(selectedEdge: never, selectedEdgeGroup: never[]) {
  return renderToStaticMarkup(
    <EvidenceDesk
      selectedEdge={selectedEdge}
      selectedEdgeGroup={selectedEdgeGroup}
      selectedEntity={null}
      detail={null}
      structuralResults={[]}
      assumptionResults={[]}
      hasActiveResult={false}
      propagationInProgress={false}
      edges={selectedEdgeGroup}
      entityName={(id) => id ?? "—"}
      onCloseSelection={() => undefined}
      onSelectEdge={() => undefined}
      onGraphChanged={() => undefined}
      onEdgeReviewed={() => undefined}
    />,
  );
}
