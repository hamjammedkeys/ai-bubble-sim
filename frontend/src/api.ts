import type { GraphPayload } from "./types";

export async function runCloudSlowdown(params: {
  shock_percentage: number;
  pass_through_rate: number;
  propagation_factor: number;
  max_rounds: number;
}): Promise<GraphPayload> {
  const response = await fetch("/api/scenario/cloud-slowdown", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(params)
  });
  if (!response.ok) {
    throw new Error(`Scenario request failed: ${response.status}`);
  }
  return response.json();
}
