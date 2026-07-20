import { expect, it } from "vitest";
import {
  isPropagationComplete,
  propagationDecision,
  propagationFrames,
} from "./propagation";

it("assigns one 700ms frame per ordered result", () => {
  const results = [
    { edge_id: "impact", kind: "impact" },
    { edge_id: "unresolved", kind: "unresolved" },
  ] as never[];

  expect(propagationFrames(results)).toEqual([
    { edgeId: "impact", kind: "impact", delayMs: 0 },
    { edgeId: "unresolved", kind: "unresolved", delayMs: 700 },
  ]);
});

it("reveals every result immediately and schedules no frames for reduced motion", () => {
  const frames = [
    { edgeId: "impact", kind: "impact", delayMs: 0 },
    { edgeId: "unresolved", kind: "unresolved", delayMs: 700 },
  ] as const;

  expect(propagationDecision(frames, true)).toEqual({
    immediateEdgeIds: ["impact", "unresolved"],
    scheduledFrames: [],
  });
  expect(propagationDecision(frames, false)).toEqual({
    immediateEdgeIds: [],
    scheduledFrames: frames,
  });
});

it("keeps result conclusions pending until every snapshot result is revealed", () => {
  expect(isPropagationComplete(["impact", "unresolved"], new Set(["impact"]))).toBe(false);
  expect(
    isPropagationComplete(["impact", "unresolved"], new Set(["impact", "unresolved"])),
  ).toBe(true);
  expect(isPropagationComplete([], new Set())).toBe(true);
});
