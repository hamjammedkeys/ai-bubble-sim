export function focusTrapTargetIndex(
  activeIndex: number,
  focusableCount: number,
  backwards: boolean,
): number | null {
  if (focusableCount === 0) return null;
  if (activeIndex < 0) return backwards ? focusableCount - 1 : 0;
  if (backwards && activeIndex === 0) return focusableCount - 1;
  if (!backwards && activeIndex === focusableCount - 1) return 0;
  return null;
}

export type DrawerFocusCandidate<T> = {
  target: T;
  connected: boolean;
  visible: boolean;
  focusable: boolean;
};

export function chooseDrawerFocusTarget<T>(
  opener: DrawerFocusCandidate<T> | null,
  fallback: DrawerFocusCandidate<T> | null,
): T | null {
  const usable = (candidate: DrawerFocusCandidate<T> | null) =>
    candidate?.connected && candidate.visible && candidate.focusable;

  if (usable(opener)) return opener!.target;
  if (usable(fallback)) return fallback!.target;
  return null;
}

export function drawerStateAfterClose() {
  return { open: false, followPropagation: false } as const;
}
