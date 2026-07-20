import { expect, it } from "vitest";
import {
  chooseDrawerFocusTarget,
  drawerStateAfterClose,
  focusTrapTargetIndex,
} from "./drawer";

it("wraps focus only at drawer boundaries", () => {
  expect(focusTrapTargetIndex(2, 3, false)).toBe(0);
  expect(focusTrapTargetIndex(0, 3, true)).toBe(2);
  expect(focusTrapTargetIndex(1, 3, false)).toBeNull();
  expect(focusTrapTargetIndex(1, 3, true)).toBeNull();
});

it("recovers focus into the drawer when the active target is outside", () => {
  expect(focusTrapTargetIndex(-1, 3, false)).toBe(0);
  expect(focusTrapTargetIndex(-1, 3, true)).toBe(2);
  expect(focusTrapTargetIndex(-1, 0, false)).toBeNull();
});

it("restores only to a usable opener and otherwise chooses the workspace fallback", () => {
  const svgTarget = { kind: "svg", focus: () => undefined };
  const fallback = { kind: "workspace", focus: () => undefined };

  expect(
    chooseDrawerFocusTarget(
      { target: svgTarget, connected: true, visible: true, focusable: true },
      { target: fallback, connected: true, visible: true, focusable: true },
    ),
  ).toBe(svgTarget);

  for (const unusableOpener of [
    { target: svgTarget, connected: true, visible: false, focusable: true },
    { target: svgTarget, connected: false, visible: true, focusable: true },
    { target: svgTarget, connected: true, visible: true, focusable: false },
  ]) {
    expect(
      chooseDrawerFocusTarget(unusableOpener, {
        target: fallback,
        connected: true,
        visible: true,
        focusable: true,
      }),
    ).toBe(fallback);
  }

  expect(
    chooseDrawerFocusTarget(
      { target: svgTarget, connected: false, visible: false, focusable: false },
      { target: fallback, connected: true, visible: false, focusable: true },
    ),
  ).toBeNull();
});

it("closing the drawer also relinquishes propagation-follow ownership", () => {
  expect(drawerStateAfterClose()).toEqual({
    open: false,
    followPropagation: false,
  });
});
