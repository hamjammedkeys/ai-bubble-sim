"use client";

import {
  BaseEdge,
  EdgeLabelRenderer,
  Handle,
  Position,
  ReactFlow,
  getBezierPath,
  type Edge as RFEdge,
  type EdgeProps,
  type Node as RFNode,
  type NodeProps,
} from "@xyflow/react";
import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  useSyncExternalStore,
  type KeyboardEvent as ReactKeyboardEvent,
} from "react";
import {
  ExposureDesk,
  MarketStrip,
  TerminalDataStatus,
  type DataStatus,
} from "./components/exposure-desk";
import {
  INITIAL_SCENARIO_LAYERS,
  ScenarioBook,
  type ScenarioLayers,
} from "./components/scenario-book";
import { RiskTape } from "./components/risk-tape";
import { EvidenceDesk } from "./components/evidence-desk";
import { ChatScenarioCard } from "./components/chat-scenario-card";
import { api, type ChatMessage, type Edge, type EdgeDetail, type EdgeResult, type Entity, type Scenario } from "./lib/api";
import { scenarioCardFromActions, type ChatAction, type ChatCompletedRun } from "./lib/chat-actions";
import {
  deskScenarioId,
  deriveDeskMetrics,
  identifiableHopCount,
  selectedScenarioAfterCreate,
  scenarioOriginEntityId,
  toDeskRunSnapshot,
  type DeskRunSnapshot,
} from "./lib/dashboard";
import { dataRequestErrorMessage, detailAfterReview, isGraphActivationKey, shouldAcceptEdgeDetail } from "./lib/evidence";
import {
  chooseDrawerFocusTarget,
  drawerStateAfterClose,
  focusTrapTargetIndex,
} from "./lib/drawer";
import { formatFinancialValue } from "./lib/format";
import {
  isPropagationComplete,
  propagationDecision,
  propagationFrames,
} from "./lib/propagation";
import {
  ENTITY_LABEL,
  STROKE,
  edgeClassName,
  edgeWidth,
  groupGraphEdges,
  graphFiltersForLayers,
  graphFocusFor,
  layout,
  reactFlowNodeDimensions,
  type GraphEdgeGroup,
  type VisualState,
} from "./lib/graph";

export function renderGroupedEdgeLabel({
  count,
  active,
  relationship,
}: {
  count: number;
  active: boolean;
  relationship?: string;
}): string | null {
  if (active) return relationship ?? null;
  return count > 1 ? `${count} relationships` : null;
}

export function groupedEdgeActivationId({
  memberIds,
  representativeId,
  selectedId,
}: {
  memberIds: string[];
  representativeId: string;
  selectedId: string | null;
}): string {
  return selectedId && memberIds.includes(selectedId) ? selectedId : representativeId;
}

export function groupedEdgeActivationForInput(
  input: string,
  activationEdgeId: string,
): string | null {
  return input === "click" || isGraphActivationKey(input) ? activationEdgeId : null;
}

export function groupedEdgeTraceKey(
  activeEdgeId: string | null,
  memberIds: string[],
): string {
  return activeEdgeId && memberIds.includes(activeEdgeId) ? activeEdgeId : "inactive";
}

export function graphFocusEdgeId({
  hoveredEdgeId,
  focusedEdgeId,
  selectedEdgeId,
  activeEntityFocus,
  followingPropagation,
}: {
  hoveredEdgeId: string | null;
  focusedEdgeId: string | null;
  selectedEdgeId: string | null;
  activeEntityFocus: string | null;
  followingPropagation: boolean;
}): string | null {
  return hoveredEdgeId
    ?? focusedEdgeId
    ?? (activeEntityFocus || followingPropagation ? null : selectedEdgeId);
}

export function focusedEdgeIdAfterGroupBlur(
  focusedEdgeId: string | null,
  memberIds: string[],
): string | null {
  return focusedEdgeId && memberIds.includes(focusedEdgeId) ? null : focusedEdgeId;
}

export function selectedEdgeGroupFor(
  groups: GraphEdgeGroup[],
  selectedId: string | null,
): Edge[] {
  if (!selectedId) return [];
  return groups.find((group) =>
    group.edges.some((edge) => edge.id === selectedId)
  )?.edges ?? [];
}

export type ChatViewMessage = ChatMessage & { actions?: ChatAction[] };

export function assistantChatMessage(content: string, actions: ChatAction[]): ChatViewMessage {
  return { role: "assistant", content, actions };
}

export async function performChatScenarioAction(
  action: "run" | "view",
  scenarioId: string,
  completedRun: ChatCompletedRun | undefined,
  handlers: {
    run: (id: string) => Promise<void>;
    view: (id: string, run?: ChatCompletedRun) => Promise<void>;
    close: () => void;
  },
): Promise<string | null> {
  try {
    await handlers[action](scenarioId, completedRun);
    handlers.close();
    return null;
  } catch (error) {
    return String(error);
  }
}

export type ScenarioRunOptions = { errorOwner?: "dashboard" | "card" };

export function dashboardErrorForScenarioRun(
  error: unknown,
  options: ScenarioRunOptions = {},
): string | null {
  return options.errorOwner === "card" ? null : String(error);
}

export function runSnapshotAfterScenarioView(
  snapshot: DeskRunSnapshot | null,
  scenarioId: string,
): DeskRunSnapshot | null {
  return snapshot?.scenarioId === scenarioId ? snapshot : null;
}

export function deskSnapshotFromChatRun(
  scenarioId: string,
  run: ChatCompletedRun,
): DeskRunSnapshot {
  return {
    scenarioId,
    results: Object.fromEntries(run.results.map((result) => [result.edge_id, result])),
    totals: run.totals,
  };
}

// Colour a node inherits from the strongest scenario result touching it.
const IGNITE_COLOR: Record<"impact" | "exposure" | "unresolved", string> = {
  impact: "var(--impact)",
  exposure: "var(--exposure)",
  unresolved: "#c99a3b",
};

// ---- custom node -----------------------------------------------------------
function EntityNode({ data }: NodeProps) {
  const d = data as {
    name: string;
    typeLabel: string;
    selected: boolean;
    dimmed: boolean;
    originPulse: boolean;
    igniteKind: "impact" | "exposure" | "unresolved" | null;
    justIgnited: boolean;
    onFocus: () => void;
    onBlur: () => void;
    onActivate: (opener: Element) => void;
  };
  const igniteColor = d.igniteKind ? IGNITE_COLOR[d.igniteKind] : null;
  return (
    <div
      role="button"
      tabIndex={0}
      aria-label={`Inspect ${d.name}`}
      onFocus={d.onFocus}
      onBlur={d.onBlur}
      onKeyDown={(event) => {
        if (!isGraphActivationKey(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        d.onActivate(event.currentTarget);
      }}
      className={[
        d.originPulse ? "scenario-origin-pulse" : "",
        d.justIgnited ? "node-ignite" : "",
      ].filter(Boolean).join(" ") || undefined}
      style={{
        width: 184,
        height: 60,
        background: d.selected ? "var(--surface-2)" : "var(--surface)",
        border: `1px solid ${igniteColor ?? (d.selected ? "var(--candidate)" : "var(--hairline)")}`,
        boxShadow: igniteColor ? `0 0 0 1px ${igniteColor}, 0 0 16px -2px ${igniteColor}` : undefined,
        transition: "box-shadow 500ms ease, border-color 500ms ease",
        borderRadius: 0,
        padding: "8px 14px",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        cursor: "pointer",
        opacity: d.dimmed ? 0.32 : 1,
      }}
    >
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <div style={{ fontSize: 14, fontWeight: 600, color: "var(--text)", lineHeight: 1.1 }}>{d.name}</div>
      <div className="num" style={{ fontSize: 10, color: "var(--muted)", marginTop: 3, letterSpacing: "0.04em" }}>
        {d.typeLabel.toUpperCase()}
      </div>
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

// ---- custom edge -----------------------------------------------------------
function EvidenceEdge(props: EdgeProps) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, id } = props;
  const d = data as {
    visualState: VisualState;
    badge: string | null;
    relationshipLabel: string | null;
    selected: boolean;
    focused: boolean;
    dimmed: boolean;
    active: boolean;
    traceKey: string;
    recentlyApproved: boolean;
    accessibleLabel: string;
    activationEdgeId: string;
    onFocus: () => void;
    onBlur: () => void;
    onActivate: (edgeId: string, opener: Element) => void;
  };
  const focusTargetRef = useRef<SVGPathElement>(null);
  useLayoutEffect(() => {
    if (d.focused && document.activeElement !== focusTargetRef.current) {
      focusTargetRef.current?.focus({ preventScroll: true });
    }
  }, [d.focused]);
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
  });
  const stroke = STROKE[d.visualState];
  return (
    <>
      <path
        ref={focusTargetRef}
        d={path}
        fill="none"
        stroke="transparent"
        strokeWidth={18}
        role="button"
        tabIndex={0}
        aria-label={d.accessibleLabel}
        onFocus={d.onFocus}
        onBlur={d.onBlur}
        onKeyDown={(event) => {
          const activationEdgeId = groupedEdgeActivationForInput(
            event.key,
            d.activationEdgeId,
          );
          if (!activationEdgeId) return;
          event.preventDefault();
          event.stopPropagation();
          d.onActivate(activationEdgeId, event.currentTarget);
        }}
      />
      <BaseEdge
        key={d.traceKey}
        id={id}
        path={path}
        className={[
          edgeClassName(d.visualState),
          d.active ? "edge-trace" : "",
          d.recentlyApproved ? "edge-approved" : "",
        ].filter(Boolean).join(" ")}
        style={{
          stroke,
          strokeWidth: d.selected ? edgeWidth(d.visualState) + 1.5 : edgeWidth(d.visualState),
          opacity: d.dimmed ? 0.18 : d.visualState === "grey" ? 0.7 : 1,
        }}
      />
      {(d.relationshipLabel || d.badge) && <EdgeLabelRenderer>
        <div
          className="num"
          style={{
            position: "absolute",
            transform: `translate(-50%,-50%) translate(${labelX}px,${labelY}px)`,
            maxWidth: 180,
            padding: "3px 6px",
            border: `1px solid ${d.selected ? stroke : "var(--hairline)"}`,
            borderRadius: 0,
            background: "var(--bg)",
            color: d.dimmed ? "var(--muted)" : "var(--text)",
            fontSize: 9.5,
            fontWeight: 600,
            lineHeight: 1.25,
            opacity: d.dimmed ? 0.25 : 1,
            pointerEvents: "none",
            textAlign: "center",
            textTransform: "uppercase",
            whiteSpace: "nowrap",
          }}
        >
          {d.relationshipLabel}
          {d.badge && <span style={{ color: stroke }}> · {d.badge}</span>}
        </div>
      </EdgeLabelRenderer>}
    </>
  );
}

const nodeTypes = { entity: EntityNode };
const edgeTypes = { evidence: EvidenceEdge };
const EMPTY_RESULTS: Record<string, EdgeResult> = {};
const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";
const NARROW_VIEWPORT_QUERY = "(max-width: 1180px)";
const DRAWER_FOCUSABLE = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  "[tabindex]:not([tabindex='-1'])",
].join(",");

function mediaMatches(query: string): boolean {
  return typeof window !== "undefined" && window.matchMedia(query).matches;
}

function useMediaQuery(query: string): boolean {
  const subscribe = useCallback((notify: () => void) => {
    const media = window.matchMedia(query);
    media.addEventListener("change", notify);
    return () => media.removeEventListener("change", notify);
  }, [query]);
  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query]);
  const getServerSnapshot = useCallback(() => false, []);

  return useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
}

type FocusableElement = (HTMLElement | SVGElement) & { focus: () => void };

function focusableElement(element: Element | null): FocusableElement | null {
  return element && typeof (element as { focus?: unknown }).focus === "function"
    ? element as FocusableElement
    : null;
}

function focusCandidate(element: FocusableElement | null) {
  if (!element) return null;
  const tagName = element.tagName.toLowerCase();
  const naturallyFocusable =
    tagName === "button" ||
    tagName === "input" ||
    tagName === "select" ||
    tagName === "textarea" ||
    (tagName === "a" && element.hasAttribute("href"));
  const disabled = element.hasAttribute("disabled");
  const style = window.getComputedStyle(element);

  return {
    target: element,
    connected: element.isConnected,
    visible:
      element.getClientRects().length > 0 &&
      style.display !== "none" &&
      style.visibility !== "hidden" &&
      style.opacity !== "0",
    focusable:
      !disabled &&
      element.getAttribute("aria-hidden") !== "true" &&
      (naturallyFocusable || element.hasAttribute("tabindex")),
  };
}

// ---- page ------------------------------------------------------------------
export default function Home() {
  const [entities, setEntities] = useState<Entity[]>([]);
  const [edges, setEdges] = useState<Edge[]>([]);
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState<string | null>(null);
  const [runSnapshot, setRunSnapshot] = useState<DeskRunSnapshot | null>(null);
  const [revealedResultIds, setRevealedResultIds] = useState<Set<string>>(() => new Set());
  const [activePropagationEdgeId, setActivePropagationEdgeId] = useState<string | null>(null);
  const [originPulseEntityId, setOriginPulseEntityId] = useState<string | null>(null);
  const [recentlyApprovedEdgeId, setRecentlyApprovedEdgeId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [selectedEntityId, setSelectedEntityId] = useState<string | null>(null);
  const [hoveredEdgeId, setHoveredEdgeId] = useState<string | null>(null);
  const [hoveredEntityId, setHoveredEntityId] = useState<string | null>(null);
  const [focusedEdgeId, setFocusedEdgeId] = useState<string | null>(null);
  const [focusedEntityId, setFocusedEntityId] = useState<string | null>(null);
  const [detail, setDetail] = useState<EdgeDetail | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [dataStatus, setDataStatus] = useState<DataStatus>("loading");
  const [layers, setLayers] = useState<ScenarioLayers>(() => ({ ...INITIAL_SCENARIO_LAYERS }));
  const [evidenceDrawerOpen, setEvidenceDrawerOpen] = useState(false);
  const [followingPropagation, setFollowingPropagation] = useState(false);
  const isNarrowViewport = useMediaQuery(NARROW_VIEWPORT_QUERY);
  const animationCancelRef = useRef<(() => void) | null>(null);
  const runSnapshotRef = useRef<DeskRunSnapshot | null>(null);
  const prefersReducedMotionRef = useRef(mediaMatches(REDUCED_MOTION_QUERY));
  const propagationFollowRef = useRef(false);
  const scenarioMutationLockedRef = useRef(false);
  const detailRequestVersionRef = useRef(0);
  const selectedEdgeRequestRef = useRef<string | null>(null);
  const evidenceDrawerOpenRef = useRef(false);
  const evidenceDrawerRef = useRef<HTMLDivElement>(null);
  const evidenceDrawerCloseRef = useRef<HTMLButtonElement>(null);
  const evidenceDrawerToggleRef = useRef<HTMLButtonElement>(null);
  const evidenceDrawerOpenerRef = useRef<FocusableElement | null>(null);
  const networkWorkspaceRef = useRef<HTMLDivElement>(null);
  const results = runSnapshot?.results ?? EMPTY_RESULTS;
  const totals = runSnapshot?.totals ?? null;
  const phase: 0 | 2 = runSnapshot ? 2 : 0;
  const drawerIsModal = isNarrowViewport && evidenceDrawerOpen;

  const invalidateEdgeDetailRequest = useCallback((edgeId: string | null) => {
    selectedEdgeRequestRef.current = edgeId;
    detailRequestVersionRef.current += 1;
    return detailRequestVersionRef.current;
  }, []);

  const openEvidenceDrawer = useCallback((opener?: Element | null) => {
    if (!isNarrowViewport) return;
    if (!evidenceDrawerOpenRef.current) {
      const activeElement = document.activeElement;
      const activeOpener = activeElement !== document.body
        ? focusableElement(activeElement)
        : null;
      evidenceDrawerOpenerRef.current =
        focusableElement(opener ?? null) ??
        activeOpener ??
        evidenceDrawerToggleRef.current;
    }
    evidenceDrawerOpenRef.current = true;
    setEvidenceDrawerOpen(true);
  }, [isNarrowViewport]);

  const closeEvidenceDrawer = useCallback(() => {
    const closedState = drawerStateAfterClose();
    propagationFollowRef.current = closedState.followPropagation;
    if (!evidenceDrawerOpenRef.current) return;
    setFollowingPropagation(closedState.followPropagation);
    evidenceDrawerOpenRef.current = closedState.open;
    setEvidenceDrawerOpen(closedState.open);
    const target = chooseDrawerFocusTarget(
      focusCandidate(evidenceDrawerOpenerRef.current),
      focusCandidate(networkWorkspaceRef.current),
    );
    evidenceDrawerOpenerRef.current = null;
    target?.focus();
  }, []);

  const trapDrawerFocus = useCallback((event: ReactKeyboardEvent<HTMLDivElement>) => {
    if (!drawerIsModal || event.key !== "Tab") return;
    const drawer = evidenceDrawerRef.current;
    if (!drawer) return;

    const focusable = Array.from(drawer.querySelectorAll<HTMLElement>(DRAWER_FOCUSABLE));
    const activeIndex = focusable.indexOf(document.activeElement as HTMLElement);
    const targetIndex = focusTrapTargetIndex(activeIndex, focusable.length, event.shiftKey);
    if (targetIndex === null) return;

    event.preventDefault();
    focusable[targetIndex]?.focus();
  }, [drawerIsModal]);

  const openEdgeDetail = useCallback((id: string) => {
    const version = invalidateEdgeDetailRequest(id);
    setSelected(id);
    setSelectedEntityId(null);
    setDetail((current) => current?.id === id ? current : null);
    setDetailError(null);
    api.edge(id)
      .then((nextDetail) => {
        if (
          shouldAcceptEdgeDetail(
            { edgeId: id, version },
            {
              selectedEdgeId: selectedEdgeRequestRef.current,
              version: detailRequestVersionRef.current,
            },
          )
        ) {
          setDetail(nextDetail);
        }
      })
      .catch((error) => {
        if (
          shouldAcceptEdgeDetail(
            { edgeId: id, version },
            {
              selectedEdgeId: selectedEdgeRequestRef.current,
              version: detailRequestVersionRef.current,
            },
          )
        ) {
          setDetailError(`Evidence detail failed — ${String(error)}`);
        }
      });
  }, [invalidateEdgeDetailRequest]);

  const selectEdge = useCallback((id: string, opener?: Element | null) => {
    propagationFollowRef.current = false;
    setFollowingPropagation(false);
    openEvidenceDrawer(opener);
    openEdgeDetail(id);
  }, [openEdgeDetail, openEvidenceDrawer]);

  const followPropagationEdge = useCallback((id: string) => {
    if (propagationFollowRef.current) openEdgeDetail(id);
  }, [openEdgeDetail]);

  const selectEntity = useCallback((id: string, opener?: Element | null) => {
    propagationFollowRef.current = false;
    setFollowingPropagation(false);
    invalidateEdgeDetailRequest(null);
    openEvidenceDrawer(opener);
    setSelectedEntityId(id);
    setSelected(null);
    setDetail(null);
    setDetailError(null);
  }, [invalidateEdgeDetailRequest, openEvidenceDrawer]);

  const clearSelection = useCallback(() => {
    propagationFollowRef.current = false;
    setFollowingPropagation(false);
    invalidateEdgeDetailRequest(null);
    setSelected(null);
    setSelectedEntityId(null);
    setDetail(null);
    setDetailError(null);
  }, [invalidateEdgeDetailRequest]);

  const load = useCallback(async () => {
    setDataStatus("loading");
    try {
      const [ents, allEdges, scns] = await Promise.all([
        api.entities(),
        api.edges(),
        api.scenarios(),
      ]);
      setEntities(ents);
      setEdges(allEdges.filter((e) => e.status === "approved" || e.status === "candidate"));
      setScenarios(scns);
      setSelectedScenarioId((prev) => prev ?? scns[0]?.id ?? null);
      setError(null);
      setDataStatus("live");
    } catch (e) {
      setError(String(e));
      setDataStatus("degraded");
    }
  }, []);

  const handleEdgeReviewed = useCallback(
    async (reviewed: Edge) => {
      propagationFollowRef.current = false;
      setFollowingPropagation(false);
      invalidateEdgeDetailRequest(reviewed.id);
      setRecentlyApprovedEdgeId(reviewed.status === "approved" ? reviewed.id : null);
      setSelected(reviewed.id);
      setSelectedEntityId(null);
      setDetail((current) => detailAfterReview(current, reviewed));
      await load();
    },
    [invalidateEdgeDetailRequest, load],
  );

  useEffect(() => {
    const timeoutId = window.setTimeout(() => {
      void load();
    }, 0);

    return () => window.clearTimeout(timeoutId);
  }, [load]);

  useEffect(() => {
    if (!isNarrowViewport) closeEvidenceDrawer();
  }, [closeEvidenceDrawer, isNarrowViewport]);

  useLayoutEffect(() => {
    if (drawerIsModal) evidenceDrawerCloseRef.current?.focus();
  }, [drawerIsModal]);

  useEffect(() => {
    const media = window.matchMedia(REDUCED_MOTION_QUERY);
    prefersReducedMotionRef.current = media.matches;
    const updateMotionPreference = (event: MediaQueryListEvent) => {
      prefersReducedMotionRef.current = event.matches;
      if (!event.matches) return;

      animationCancelRef.current?.();
      animationCancelRef.current = null;
      const snapshot = runSnapshotRef.current;
      if (!snapshot) return;

      const frames = propagationFrames(Object.values(snapshot.results));
      const decision = propagationDecision(frames, true);
      setRevealedResultIds(new Set(decision.immediateEdgeIds));
      const lastFrame = frames.at(-1);
      setActivePropagationEdgeId(lastFrame?.edgeId ?? null);
      if (lastFrame) followPropagationEdge(lastFrame.edgeId);
    };
    media.addEventListener("change", updateMotionPreference);

    return () => media.removeEventListener("change", updateMotionPreference);
  }, [followPropagationEdge]);

  useEffect(() => {
    if (!drawerIsModal) return;

    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") closeEvidenceDrawer();
    };
    document.addEventListener("keydown", closeOnEscape);

    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [closeEvidenceDrawer, drawerIsModal]);

  useEffect(() => {
    animationCancelRef.current?.();
    if (!runSnapshot) {
      animationCancelRef.current = null;
      return;
    }

    const frames = propagationFrames(Object.values(runSnapshot.results));
    const decision = propagationDecision(frames, prefersReducedMotionRef.current);
    const timeoutIds: number[] = [];

    for (const frame of decision.scheduledFrames) {
      timeoutIds.push(window.setTimeout(() => {
        setRevealedResultIds((current) => new Set(current).add(frame.edgeId));
        setActivePropagationEdgeId(frame.edgeId);
        followPropagationEdge(frame.edgeId);
      }, frame.delayMs));
    }

    const cancel = () => timeoutIds.forEach((timeoutId) => window.clearTimeout(timeoutId));
    animationCancelRef.current = cancel;

    return () => {
      cancel();
      if (animationCancelRef.current === cancel) animationCancelRef.current = null;
    };
  }, [followPropagationEdge, runSnapshot]);

  const runScenarioById = useCallback(async (
    scenarioId: string,
    options: ScenarioRunOptions = {},
  ) => {
    const scenarioAtRunStart = scenarios.find((scenario) => scenario.id === scenarioId) ?? null;
    scenarioMutationLockedRef.current = true;
    setRunning(true);
    try {
      const runData = await api.runScenario(scenarioId);
      const frames = propagationFrames(runData.results);
      const firstFrame = frames[0];
      setSelectedScenarioId(scenarioId);
      propagationFollowRef.current = true;
      setFollowingPropagation(true);
      animationCancelRef.current?.();
      invalidateEdgeDetailRequest(null);
      runSnapshotRef.current = null;
      setRevealedResultIds(new Set());
      setActivePropagationEdgeId(null);
      setOriginPulseEntityId(null);
      setRecentlyApprovedEdgeId(null);
      setSelected(null);
      setDetail(null);
      setOriginPulseEntityId(
        scenarioOriginEntityId(scenarioAtRunStart, entities, edges, firstFrame?.edgeId),
      );
      const snapshot = toDeskRunSnapshot(runData);
      const decision = propagationDecision(frames, prefersReducedMotionRef.current);
      if (prefersReducedMotionRef.current) {
        setRevealedResultIds(new Set(decision.immediateEdgeIds));
        const lastFrame = frames.at(-1);
        setActivePropagationEdgeId(lastFrame?.edgeId ?? null);
        if (lastFrame) followPropagationEdge(lastFrame.edgeId);
      }
      runSnapshotRef.current = snapshot;
      setRunSnapshot(snapshot);
    } catch (e) {
      scenarioMutationLockedRef.current = false;
      const dashboardError = dashboardErrorForScenarioRun(e, options);
      if (dashboardError) setError(dashboardError);
      throw e;
    } finally {
      setRunning(false);
    }
  }, [edges, entities, followPropagationEdge, invalidateEdgeDetailRequest, scenarios]);

  const runSelectedScenario = useCallback(() => {
    if (!selectedScenarioId) return;
    void runScenarioById(selectedScenarioId).catch(() => undefined);
  }, [runScenarioById, selectedScenarioId]);

  const viewScenarioById = useCallback(async (
    scenarioId: string,
    completedRun?: ChatCompletedRun,
  ) => {
    const nextSnapshot = completedRun
      ? deskSnapshotFromChatRun(scenarioId, completedRun)
      : runSnapshotAfterScenarioView(runSnapshotRef.current, scenarioId);
    if (nextSnapshot !== runSnapshotRef.current) {
      scenarioMutationLockedRef.current = false;
      propagationFollowRef.current = false;
      setFollowingPropagation(false);
      animationCancelRef.current?.();
      animationCancelRef.current = null;
      runSnapshotRef.current = nextSnapshot;
      setRunSnapshot(nextSnapshot);
      setRevealedResultIds(new Set(Object.keys(nextSnapshot?.results ?? {})));
      setActivePropagationEdgeId(null);
      setOriginPulseEntityId(null);
      invalidateEdgeDetailRequest(null);
      setSelected(null);
      setSelectedEntityId(null);
      setDetail(null);
      setDetailError(null);
    }
    await load();
    setSelectedScenarioId(scenarioId);
  }, [invalidateEdgeDetailRequest, load]);

  const createScenario = useCallback(
    async (name: string, origin: string, magnitude: number) => {
      const created = await api.createScenario({ name, origin_entity: origin, magnitude });
      const scns = await api.scenarios();
      setScenarios(scns);
      const mutationLocked = scenarioMutationLockedRef.current;
      setSelectedScenarioId((currentScenarioId) =>
        selectedScenarioAfterCreate(currentScenarioId, created.id, mutationLocked),
      );
    },
    [],
  );

  const reset = useCallback(() => {
    scenarioMutationLockedRef.current = false;
    propagationFollowRef.current = false;
    setFollowingPropagation(false);
    animationCancelRef.current?.();
    animationCancelRef.current = null;
    runSnapshotRef.current = null;
    setRunSnapshot(null);
    setRevealedResultIds(new Set());
    setActivePropagationEdgeId(null);
    setOriginPulseEntityId(null);
    setRecentlyApprovedEdgeId(null);
    closeEvidenceDrawer();
    invalidateEdgeDetailRequest(null);
    setSelected(null);
    setDetail(null);
  }, [closeEvidenceDrawer, invalidateEdgeDetailRequest]);

  const entityName = useCallback(
    (id: string | null) => entities.find((e) => e.id === id)?.name ?? "—",
    [entities],
  );

  const positions = useMemo(() => layout(entities, edges), [entities, edges]);

  const graphFilters = useMemo(() => graphFiltersForLayers(layers), [layers]);

  const presentedResults = useMemo(
    () => Object.fromEntries(
      Object.entries(results).filter(([edgeId]) => revealedResultIds.has(edgeId)),
    ),
    [results, revealedResultIds],
  );

  const graphFocus = useMemo(() => {
    const activeEntityFocus = hoveredEntityId ?? focusedEntityId;
    const edgeId = graphFocusEdgeId({
      hoveredEdgeId,
      focusedEdgeId,
      selectedEdgeId: selected,
      activeEntityFocus,
      followingPropagation,
    });
    const entityId = activeEntityFocus ?? selectedEntityId;
    return graphFocusFor(edges, edgeId, entityId);
  }, [edges, focusedEdgeId, focusedEntityId, followingPropagation, hoveredEdgeId, hoveredEntityId, selected, selectedEntityId]);

  // As the wave reveals each result, tint both endpoints with its strongest kind
  // (impact > exposure > unresolved) so the graph becomes a contagion map.
  const ignitedNodeKinds = useMemo(() => {
    const priority = { impact: 3, exposure: 2, unresolved: 1 } as const;
    const kinds = new Map<string, "impact" | "exposure" | "unresolved">();
    for (const edge of edges) {
      const result = presentedResults[edge.id];
      if (!result) continue;
      for (const nodeId of [edge.source_entity_id, edge.target_entity_id]) {
        if (!nodeId) continue;
        const existing = kinds.get(nodeId);
        if (!existing || priority[result.kind] > priority[existing]) {
          kinds.set(nodeId, result.kind);
        }
      }
    }
    return kinds;
  }, [edges, presentedResults]);

  const activeEndpointIds = useMemo(() => {
    const ids = new Set<string>();
    const edge = edges.find((e) => e.id === activePropagationEdgeId);
    if (edge?.source_entity_id) ids.add(edge.source_entity_id);
    if (edge?.target_entity_id) ids.add(edge.target_entity_id);
    return ids;
  }, [activePropagationEdgeId, edges]);

  const rfNodes: RFNode[] = useMemo(
    () =>
      entities.map((e) => ({
        id: e.id,
        type: "entity",
        position: positions[e.id] ?? { x: 0, y: 0 },
        ...reactFlowNodeDimensions(),
        data: {
          name: e.name,
          typeLabel: ENTITY_LABEL[e.entity_type ?? ""] ?? e.entity_type ?? "",
          selected: selectedEntityId === e.id,
          dimmed: graphFocus !== null && !graphFocus.nodeIds.has(e.id),
          originPulse: originPulseEntityId === e.id,
          igniteKind: ignitedNodeKinds.get(e.id) ?? null,
          justIgnited: activeEndpointIds.has(e.id),
          onFocus: () => setFocusedEntityId(e.id),
          onBlur: () => setFocusedEntityId((current) => current === e.id ? null : current),
          onActivate: (opener: Element) => selectEntity(e.id, opener),
        },
        draggable: true,
      })),
    [activeEndpointIds, entities, graphFocus, ignitedNodeKinds, originPulseEntityId, positions, selectEntity, selectedEntityId],
  );

  const graphEdgeGroups = useMemo(
    () => groupGraphEdges(edges, presentedResults, graphFilters),
    [edges, graphFilters, presentedResults],
  );

  const rfEdges: RFEdge[] = useMemo(() =>
    graphEdgeGroups.map((group) => {
      const memberIds = group.edges.map((edge) => edge.id);
      const activationEdgeId = groupedEdgeActivationId({
        memberIds,
        representativeId: group.representative.id,
        selectedId: selected,
      });
      const activationEdge = group.edges.find((edge) => edge.id === activationEdgeId)
        ?? group.representative;
      const result = presentedResults[activationEdge.id];
      const badge =
        result && result.kind !== "unresolved" && result.value != null
          ? formatFinancialValue(result.value, result.unit)
          : null;
      const selectedGroup = memberIds.includes(selected ?? "");
      const activeLabel = selectedGroup
        || memberIds.includes(hoveredEdgeId ?? "")
        || memberIds.includes(focusedEdgeId ?? "");
      return {
        id: group.id,
        source: group.source,
        target: group.target,
        type: "evidence",
        hidden: !group.visible,
        data: {
          visualState: group.visualState,
          badge,
          relationshipLabel: renderGroupedEdgeLabel({
            count: group.edges.length,
            active: activeLabel,
            relationship: activationEdge.relationship_type.replace(/_/g, " "),
          }),
          selected: selectedGroup,
          focused: memberIds.includes(focusedEdgeId ?? ""),
          dimmed: graphFocus !== null
            && !group.edges.some((edge) => graphFocus.edgeIds.has(edge.id)),
          active: memberIds.includes(activePropagationEdgeId ?? ""),
          traceKey: groupedEdgeTraceKey(activePropagationEdgeId, memberIds),
          recentlyApproved: memberIds.includes(recentlyApprovedEdgeId ?? ""),
          accessibleLabel: `Inspect ${group.edges.length} ${group.edges.length === 1 ? "relationship" : "relationships"} from ${entityName(group.source)} to ${entityName(group.target)}`,
          activationEdgeId,
          representativeEdgeId: group.representative.id,
          onFocus: () => setFocusedEdgeId(group.representative.id),
          onBlur: () => setFocusedEdgeId((current) =>
            focusedEdgeIdAfterGroupBlur(current, memberIds)
          ),
          onActivate: (edgeId: string, opener: Element) => selectEdge(edgeId, opener),
        },
      };
    }),
  [activePropagationEdgeId, entityName, focusedEdgeId, graphEdgeGroups, graphFocus, hoveredEdgeId, presentedResults, recentlyApprovedEdgeId, selectEdge, selected]);

  const selectedEdgeGroup = useMemo(
    () => selectedEdgeGroupFor(graphEdgeGroups, selected),
    [graphEdgeGroups, selected],
  );

  const selectedEdge =
    (detail?.id === selected ? detail : null) ??
    edges.find((edge) => edge.id === selected) ??
    null;
  const deskScenario =
    scenarios.find(
      (scenario) => scenario.id === deskScenarioId(selectedScenarioId, runSnapshot),
    ) ?? null;
  const metrics = useMemo(() => deriveDeskMetrics(entities, edges, totals), [entities, edges, totals]);

  const structural = Object.values(presentedResults).filter((r) => r.kind !== "unresolved");
  const assumptionDependent = Object.values(presentedResults).filter((r) => r.kind === "unresolved");
  const propagationInProgress =
    runSnapshot !== null &&
    !isPropagationComplete(Object.keys(results), revealedResultIds);
  const runHopCount = runSnapshot ? identifiableHopCount(Object.values(results)) : null;

  return (
    <>
      <ExposureDesk
        header={
          <>
            <div style={{ display: "flex", alignItems: "baseline", gap: 14, minWidth: 0 }}>
              <h1 style={{ fontSize: 16, fontWeight: 700, letterSpacing: "-0.01em", whiteSpace: "nowrap" }}>
                FragilityGraph
              </h1>
              <span
                className="num"
                style={{ color: "var(--muted)", fontSize: 10, letterSpacing: "0.08em", whiteSpace: "nowrap" }}
              >
                EXPOSURE DESK
              </span>
              <p
                style={{
                  overflow: "hidden",
                  color: "var(--muted)",
                  fontSize: 11.5,
                  textOverflow: "ellipsis",
                  whiteSpace: "nowrap",
                }}
              >
                Evidence-backed risk propagation
              </p>
            </div>
            <div className="num" style={{ display: "flex", alignItems: "center", gap: 18, fontSize: 10 }}>
              <span style={{ color: metrics.candidateCount > 0 ? "var(--candidate)" : "var(--muted)" }}>
                REVIEW QUEUE {metrics.candidateCount}
              </span>
              <TerminalDataStatus status={dataStatus} />
            </div>
          </>
        }
        marketStrip={
          <div className={runSnapshot ? "metric-update" : undefined} style={{ height: "100%" }}>
            <MarketStrip metrics={metrics} scenarioName={deskScenario?.name ?? null} />
          </div>
        }
        scenarioBook={
          <div className="responsive-scenario-book">
            <ScenarioBook
              scenarios={scenarios}
              selectedId={selectedScenarioId}
              entities={entities}
              phase={phase}
              running={running}
              layers={layers}
              onSelect={setSelectedScenarioId}
              onCreate={createScenario}
              onRun={runSelectedScenario}
              onReset={reset}
              onLayerChange={(layer, enabled) =>
                setLayers((current) => ({ ...current, [layer]: enabled }))
              }
            />
          </div>
        }
        network={
          <div
            ref={networkWorkspaceRef}
            className="network-workspace terminal-focus"
            tabIndex={-1}
            aria-label="Network workspace"
            style={{ position: "relative", height: "100%", minHeight: 0 }}
          >
            <button
              ref={evidenceDrawerToggleRef}
              type="button"
              className="evidence-drawer-toggle terminal-focus"
              aria-controls="evidence-drawer"
              aria-expanded={drawerIsModal}
              onClick={(event) => openEvidenceDrawer(event.currentTarget)}
            >
              Evidence desk
            </button>
            {evidenceDrawerOpen && (
              <button
                type="button"
                className="evidence-drawer-backdrop"
                aria-label="Close evidence desk"
                onClick={closeEvidenceDrawer}
              />
            )}
            {error && (
              <div role="alert" style={{ position: "absolute", zIndex: 10, top: 18, left: 16, color: "var(--impact)", fontSize: 13, maxWidth: 420 }}>
                {dataRequestErrorMessage(error)}
              </div>
            )}
            <ReactFlow
              nodes={rfNodes}
              edges={rfEdges}
              nodeTypes={nodeTypes}
              edgeTypes={edgeTypes}
              onEdgeClick={(event, edge) => {
                const activationEdgeId = groupedEdgeActivationForInput(
                  "click",
                  (edge.data as { activationEdgeId: string }).activationEdgeId,
                );
                if (activationEdgeId) selectEdge(activationEdgeId, event.currentTarget);
              }}
              onNodeClick={(event, node) => selectEntity(node.id, event.currentTarget)}
              onEdgeMouseEnter={(_, edge) =>
                setHoveredEdgeId(
                  (edge.data as { representativeEdgeId: string }).representativeEdgeId,
                )
              }
              onEdgeMouseLeave={() => setHoveredEdgeId(null)}
              onNodeMouseEnter={(_, node) => setHoveredEntityId(node.id)}
              onNodeMouseLeave={() => setHoveredEntityId(null)}
              onPaneClick={clearSelection}
              nodesFocusable={false}
              edgesFocusable={false}
              fitView
              fitViewOptions={{ padding: 0.18 }}
              proOptions={{ hideAttribution: true }}
              minZoom={0.3}
            />
            <Legend />
          </div>
        }
        evidence={
          <div
            ref={evidenceDrawerRef}
            id="evidence-drawer"
            className="evidence-drawer"
            data-open={drawerIsModal}
            role={drawerIsModal ? "dialog" : undefined}
            aria-modal={drawerIsModal ? true : undefined}
            aria-label={drawerIsModal ? "Evidence desk" : undefined}
            onKeyDown={trapDrawerFocus}
          >
            <div className="evidence-drawer-header">
              <span className="terminal-label">Evidence desk</span>
              <button
                ref={evidenceDrawerCloseRef}
                type="button"
                className="terminal-focus"
                aria-label="Close evidence desk"
                onClick={closeEvidenceDrawer}
              >
                Close
              </button>
            </div>
            <EvidenceDesk
              selectedEdge={selectedEdge}
              selectedEdgeGroup={selectedEdgeGroup}
              selectedEntity={entities.find((entity) => entity.id === selectedEntityId) ?? null}
              detail={detail}
              detailError={detailError}
              result={selectedEdge ? presentedResults[selectedEdge.id] : undefined}
              structuralResults={structural}
              assumptionResults={assumptionDependent}
              hasActiveResult={totals !== null}
              propagationInProgress={propagationInProgress}
              edges={edges}
              entityName={entityName}
              onCloseSelection={clearSelection}
              onSelectEdge={selectEdge}
              onGraphChanged={load}
              onEdgeReviewed={handleEdgeReviewed}
            />
          </div>
        }
        riskTape={
          <div className={runSnapshot ? "metric-update" : undefined} style={{ height: "100%" }}>
            <RiskTape
              metrics={metrics}
              scenarioName={deskScenario?.name ?? null}
              identifiableHopCount={runHopCount}
            />
          </div>
        }
      />

      <CopilotDock
        onGraphChanged={load}
        onRunScenario={(scenarioId) => runScenarioById(scenarioId, { errorOwner: "card" })}
        onViewScenario={viewScenarioById}
      />
    </>
  );
}

export const COPILOT_CONTENT_CLASSES = {
  panelClassName: "content-safe",
  scrollerClassName: "content-safe terminal-scrollbar",
  messageClassName: "content-safe",
  inputRowClassName: "content-safe",
} as const;

export const COPILOT_PANEL_STYLE: React.CSSProperties = {
  right: 12,
  width: "min(400px, calc(100vw - 24px))",
  maxWidth: "calc(100vw - 24px)",
};

function CopilotDock({
  onGraphChanged,
  onRunScenario,
  onViewScenario,
}: {
  onGraphChanged: () => void | Promise<void>;
  onRunScenario: (scenarioId: string) => Promise<void>;
  onViewScenario: (scenarioId: string, run?: ChatCompletedRun) => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatViewMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [cardBusy, setCardBusy] = useState<Record<string, boolean>>({});
  const [cardErrors, setCardErrors] = useState<Record<string, string | null>>({});

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    const next: ChatViewMessage[] = [...messages, { role: "user", content: text }];
    setMessages(next);
    setInput("");
    setBusy(true);
    try {
      const res = await api.chat(next.map(({ role, content }) => ({ role, content })));
      setMessages([...next, assistantChatMessage(res.reply, res.actions)]);
      if (res.actions.length > 0) await onGraphChanged();
    } catch (e) {
      setMessages([...next, { role: "assistant", content: `Something went wrong — ${String(e)}` }]);
    } finally {
      setBusy(false);
    }
  };

  const actOnScenario = async (
    action: "run" | "view",
    scenarioId: string,
    completedRun?: ChatCompletedRun,
  ) => {
    if (cardBusy[scenarioId]) return;
    setCardBusy((current) => ({ ...current, [scenarioId]: true }));
    setCardErrors((current) => ({ ...current, [scenarioId]: null }));
    const actionError = await performChatScenarioAction(action, scenarioId, completedRun, {
      run: onRunScenario,
      view: onViewScenario,
      close: () => setOpen(false),
    });
    setCardBusy((current) => ({ ...current, [scenarioId]: false }));
    if (actionError) {
      setCardErrors((current) => ({ ...current, [scenarioId]: actionError }));
    }
  };

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        style={{
          position: "fixed",
          right: 24,
          bottom: 68,
          zIndex: 20,
          background: "var(--impact)",
          color: "#fff",
          border: "none",
          borderRadius: 24,
          padding: "12px 20px",
          fontSize: 14,
          fontWeight: 600,
          cursor: "pointer",
          boxShadow: "0 6px 20px rgba(0,0,0,0.4)",
        }}
      >
        ✦ Copilot
      </button>
    );
  }

  return (
    <div
      className={COPILOT_CONTENT_CLASSES.panelClassName}
      style={{
        position: "fixed",
        ...COPILOT_PANEL_STYLE,
        bottom: 68,
        zIndex: 20,
        height: 560,
        maxHeight: "80vh",
        background: "var(--surface)",
        border: "1px solid var(--hairline)",
        borderRadius: 12,
        boxShadow: "0 10px 40px rgba(0,0,0,0.5)",
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 14px", borderBottom: "1px solid var(--hairline)" }}>
        <div style={{ fontSize: 13, fontWeight: 700 }}>✦ Copilot</div>
        <button onClick={() => setOpen(false)} style={{ color: "var(--muted)", fontSize: 18, lineHeight: 1 }}>×</button>
      </div>
      <div
        className={COPILOT_CONTENT_CLASSES.scrollerClassName}
        style={{ flex: 1, minWidth: 0, overflowX: "hidden", overflowY: "auto", padding: "12px 14px", display: "flex", flexDirection: "column", gap: 10 }}
      >
        {messages.length === 0 && (
          <div className={COPILOT_CONTENT_CLASSES.messageClassName} style={{ fontSize: 12.5, color: "var(--muted)", lineHeight: 1.5 }}>
            Ask about the graph, ingest a filing by URL, or model a shock — e.g.
            <br />
            <em>&ldquo;Ingest https://www.sec.gov/…&rdquo;</em>
            <br />
            <em>&ldquo;Model a $15B GAAP loss at OpenAI and run it.&rdquo;</em>
          </div>
        )}
        {messages.map((m, i) => {
          const scenarioCard = m.actions ? scenarioCardFromActions(m.actions) : null;
          return <div
            key={i}
            className={COPILOT_CONTENT_CLASSES.messageClassName}
            style={{
              alignSelf: m.role === "user" ? "flex-end" : "flex-start",
              maxWidth: "88%",
              background: m.role === "user" ? "var(--surface-2)" : "transparent",
              border: m.role === "user" ? "1px solid var(--hairline)" : "none",
              borderRadius: 10,
              padding: m.role === "user" ? "8px 11px" : "0",
              fontSize: 12.5,
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
              color: m.role === "user" ? "var(--text)" : "var(--text)",
            }}
          >
            {m.content}
            {scenarioCard && (
              <div style={{ marginTop: 10, minWidth: 0 }}>
                <ChatScenarioCard
                  model={scenarioCard}
                  running={cardBusy[scenarioCard.scenarioId] ?? false}
                  error={cardErrors[scenarioCard.scenarioId] ?? null}
                  onRun={(scenarioId) => void actOnScenario("run", scenarioId)}
                  onView={(scenarioId, run) => void actOnScenario("view", scenarioId, run)}
                />
              </div>
            )}
          </div>
        })}
        {busy && <div className={COPILOT_CONTENT_CLASSES.messageClassName} style={{ fontSize: 12, color: "var(--muted)" }}>Thinking… (reading a filing can take a moment)</div>}
      </div>
      <div className={COPILOT_CONTENT_CLASSES.inputRowClassName} style={{ minWidth: 0, padding: 12, borderTop: "1px solid var(--hairline)", display: "flex", gap: 8 }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          placeholder="Ask the copilot…"
          disabled={busy}
          style={{ ...inputStyle, flex: 1 }}
        />
        <button onClick={send} disabled={busy || !input.trim()} style={primaryBtn(true)}>
          Send
        </button>
      </div>
    </div>
  );
}

const inputStyle: React.CSSProperties = {
  background: "var(--bg)",
  border: "1px solid var(--hairline)",
  borderRadius: 5,
  padding: "7px 9px",
  fontSize: 12.5,
  color: "var(--text)",
  width: "100%",
};

function primaryBtn(active: boolean): React.CSSProperties {
  return {
    background: active ? "var(--impact)" : "var(--surface-2)",
    color: active ? "#fff" : "var(--text)",
    border: "1px solid var(--hairline)",
    borderRadius: 6,
    padding: "8px 14px",
    fontSize: 13,
    fontWeight: 600,
    cursor: "pointer",
  };
}

function Legend() {
  const items: [string, VisualState, string][] = [
    ["Accounting impact", "impact", "forced loss"],
    ["Exposure-at-risk", "exposure", "not a loss"],
    ["Unquantified", "amber", "assumption"],
    ["Candidate", "candidate", "unreviewed"],
    ["Inactive", "grey", ""],
  ];
  return (
    <div
      style={{
        position: "absolute",
        right: 16,
        bottom: 16,
        background: "color-mix(in srgb, var(--surface) 92%, transparent)",
        border: "1px solid var(--hairline)",
        borderRadius: 8,
        padding: "10px 12px",
        fontSize: 11.5,
      }}
    >
      {items.map(([label, vs, note]) => (
        <div key={vs} style={{ display: "flex", alignItems: "center", gap: 8, margin: "5px 0" }}>
          <span style={{ width: 20, borderTop: `3px ${vs === "amber" || vs === "candidate" ? "dashed" : "solid"} ${STROKE[vs]}` }} />
          <span style={{ color: "var(--text)" }}>{label}</span>
          {note && <span style={{ color: "var(--muted)" }}>· {note}</span>}
        </div>
      ))}
    </div>
  );
}
