// Thin typed client for the FragilityGraph backend.
import type { ChatAction } from "./chat-actions";

const BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export type Entity = {
  id: string;
  name: string;
  entity_type: string | null;
  aliases: string[] | null;
};

export type Edge = {
  id: string;
  source_entity_id: string | null;
  target_entity_id: string | null;
  relationship_type: string;
  metric: string | null;
  value: number | null;
  unit: string | null;
  period: string | null;
  evidence_class: string;
  permitted_operation: string | null;
  unsupported_operation: string | null;
  passage_id: string | null;
  document_id: string | null;
  status: string;
  verification: Record<string, unknown> | null;
};

export type EdgeDetail = Edge & {
  passage_text: string | null;
  document_title: string | null;
  document_url: string | null;
};

export type Scenario = {
  id: string;
  name: string | null;
  description: string | null;
  origin_entity?: string | null;
};

export type EdgeResult = {
  edge_id: string;
  source_entity: string;
  target_entity: string;
  relationship_type: string;
  kind: "impact" | "exposure" | "unresolved";
  value: number | null;
  unit: string | null;
  label: string;
  caveat: string;
  realized_loss: number | null;
  evidence_class: string;
  visual_state: string;
};

export type ScenarioRun = {
  scenario_id: string;
  run_id: string;
  results: EdgeResult[];
  totals: { impact_total: number; exposure_total: number; unresolved_count: number };
};

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export type ChatMessage = { role: "user" | "assistant"; content: string };
export type ChatReply = { reply: string; actions: ChatAction[] };

export const api = {
  entities: () => get<Entity[]>("/entities"),
  chat: (messages: ChatMessage[]) => post<ChatReply>("/chat", { messages }),
  edges: (status?: string) => get<Edge[]>(`/edges${status ? `?status=${status}` : ""}`),
  candidates: () => get<Edge[]>("/edges/candidates"),
  edge: (id: string) => get<EdgeDetail>(`/edges/${id}`),
  createDocument: (body: { title: string; raw_text: string }) =>
    post<{ id: string; title: string }>("/documents", body),
  documentFromUrl: (body: { url: string; title?: string }) =>
    post<{ id: string; title: string }>("/documents/from_url", body),
  extractDocument: (id: string, provider: string) =>
    post<{ document_id: string; candidates_created: number; provider: string }>(
      `/documents/${id}/extract?provider=${encodeURIComponent(provider)}`,
    ),
  scenarios: () => get<Scenario[]>("/scenarios"),
  createScenario: (body: {
    name: string;
    origin_entity: string;
    magnitude: number;
    unit?: string;
    kind?: string;
  }) => post<Scenario>("/scenarios", body),
  runScenario: (id: string) => post<ScenarioRun>(`/scenarios/${id}/run`),
  approve: (id: string, reviewed_by = "reviewer") =>
    post<Edge>(`/edges/${id}/approve`, { reviewed_by }),
  reject: (id: string, reviewed_by = "reviewer") =>
    post<Edge>(`/edges/${id}/reject`, { reviewed_by }),
};
