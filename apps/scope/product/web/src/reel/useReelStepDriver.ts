/**
 * Drives a data-driven reel flow (Dashboard, ProjectDetail) as a timeline of
 * steps. Each step sets a caption, runs an action (open a sheet, advance a
 * milestone via setReelData + invalidate query), and dwells. Loops forever.
 *
 * The mutable store is reset at the top of every loop, so the page's first step
 * should re-fetch (invalidate its query) to pick up the fresh state.
 *
 * No-op unless reel mode is active for `flowId`.
 */

import { useEffect } from 'react';
import { reelFlowId, type ReelFlowId } from './flag';
import { activeScript } from './registry';
import { useReelUi, prefersReducedMotion, resetReelData } from './engine';

export interface ReelStep {
  caption?: string;
  action?: () => void | Promise<void>;
  holdMs?: number;
}

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function useReelStepDriver(
  flowId: ReelFlowId,
  buildSteps: () => ReelStep[],
  deps: unknown[],
): void {
  useEffect(() => {
    if (reelFlowId() !== flowId) return;
    if (!activeScript()) return;

    let cancelled = false;
    const reduced = prefersReducedMotion();
    const setCaption = useReelUi.getState().setCaption;

    async function once() {
      const steps = buildSteps();
      for (const s of steps) {
        if (cancelled) return;
        if (s.caption) setCaption(s.caption);
        if (s.action) await s.action();
        await wait(reduced ? 0 : s.holdMs ?? 2500);
      }
    }

    async function loop() {
      do {
        resetReelData();
        await once();
        if (cancelled) return;
        await wait(2200);
      } while (!reduced && !cancelled);
    }

    void loop();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
}
