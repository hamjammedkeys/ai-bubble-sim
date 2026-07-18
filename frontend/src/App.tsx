import { useCallback, useEffect, useRef, useState } from "react";
import {
  listReviewCandidates,
  runCompoundCreditEvent,
  submitReviewDecision
} from "./api";
import { CompanyPanel } from "./components/CompanyPanel";
import { NetworkMap } from "./components/NetworkMap";
import { ResultsPanel } from "./components/ResultsPanel";
import type {
  CompoundCreditEventRequest,
  EvidenceNode,
  EvidencePayload,
  ReviewAction
} from "./types";

export const SCENARIO_LANGUAGE =
  "calculated Impact plus activated Exposure; downstream loss not identifiable";

const HERO_EVENT: CompoundCreditEventRequest = {
  incrementalGaapLoss: 10_000_000_000,
  creditStatus: "severe_distress",
  defaultStatus: "not_defaulted"
};

const initialEvidence: EvidencePayload = {
  scenario: {
    incrementalGaapLoss: null,
    creditStatus: null,
    defaultStatus: null,
    language: SCENARIO_LANGUAGE
  },
  nodes: [],
  edges: [],
  reviewCandidates: [],
  auditLog: [],
  ranking: []
};

export default function App() {
  const [evidence, setEvidence] = useState<EvidencePayload>(initialEvidence);
  const [selectedNode, setSelectedNode] = useState<EvidenceNode | null>(null);
  const [replayToken, setReplayToken] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [reviewNotice, setReviewNotice] = useState<string | null>(null);
  const [reviewBusy, setReviewBusy] = useState(false);
  const requestSequence = useRef(0);

  const runScenario = useCallback(async () => {
    const requestId = ++requestSequence.current;
    setError(null);
    try {
      const [scenarioPayload, reviewPayload] = await Promise.all([
        runCompoundCreditEvent(HERO_EVENT),
        listReviewCandidates()
      ]);
      if (requestId !== requestSequence.current) return;
      const refreshed: EvidencePayload = {
        ...scenarioPayload,
        reviewCandidates: reviewPayload.reviewCandidates,
        auditLog: reviewPayload.auditLog
      };
      setEvidence(refreshed);
      setSelectedNode((selected) =>
        selected
          ? refreshed.nodes.find((node) => node.companyId === selected.companyId) ?? null
          : null
      );
      setReplayToken((value) => value + 1);
    } catch {
      if (requestId !== requestSequence.current) return;
      setEvidence(initialEvidence);
      setSelectedNode(null);
      setError("Unable to load compound-credit-event evidence.");
    }
  }, []);

  const submitDecision = useCallback(async (candidateId: string, action: ReviewAction) => {
    setReviewBusy(true);
    setError(null);
    try {
      const payload = await submitReviewDecision(candidateId, action, {
        reviewerId: "dashboard-reviewer",
        reason: action === "approve" ? "Approved from dashboard" : "Rejected from dashboard"
      });
      const latestAudit = payload.auditLog[payload.auditLog.length - 1];
      setReviewNotice(latestAudit?.reason ?? null);
      await runScenario();
    } catch {
      setError("Unable to submit review decision.");
    } finally {
      setReviewBusy(false);
    }
  }, [runScenario]);

  useEffect(() => {
    void runScenario();
  }, [runScenario]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <h1>AI Fragility Map</h1>
        <span>{evidence.scenario.language}</span>
      </header>
      <section className="workspace">
        <aside className="left-rail">
          <section className="panel controls">
            <h2>Compound credit event</h2>
            <p className="observed-shock">Observed shock: $10.0B incremental GAAP loss</p>
            <p className="assumption">Credit status: severe distress · Default status: not defaulted</p>
            <button type="button" onClick={runScenario}>Run compound credit event</button>
          </section>
          {error && <p className="api-error" role="alert">{error}</p>}
          {reviewNotice && <p className="review-notice" role="status">{reviewNotice}</p>}
          <ResultsPanel
            evidence={evidence}
            onReviewDecision={submitDecision}
            reviewBusy={reviewBusy}
          />
        </aside>
        <NetworkMap evidence={evidence} replayToken={replayToken} onSelectNode={setSelectedNode} />
        <aside className="right-rail">
          <CompanyPanel
            nodes={evidence.nodes}
            node={selectedNode}
            onSelectNode={setSelectedNode}
          />
        </aside>
      </section>
    </main>
  );
}
