/**
 * Drives a chat-based reel flow against the real useChat hook: injects the
 * opening greeting, auto-types each scripted user line on a timeline, and loops.
 * The canned agent replies are served by the apiFetch interception (engine.ts),
 * which keeps a cursor in lockstep with the one-user-line-per-beat cadence here.
 *
 * No-op unless reel mode is active for `flowId`, so chat pages can call this
 * unconditionally.
 */

import { useEffect } from 'react';
import { reelFlowId, type ReelFlowId } from './flag';
import { activeScript } from './registry';
import {
  useReelUi,
  resetChatCursor,
  prefersReducedMotion,
  type ReelChatBeat,
} from './engine';

/** Minimal slice of useChat the driver needs. */
export interface ReelChatHandle {
  injectLeoMessage: (text: string) => void;
  sendTextMessage: (text: string) => Promise<void> | void;
  reset?: () => void;
}

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

export function useReelChatDriver(chat: ReelChatHandle, flowId: ReelFlowId): void {
  useEffect(() => {
    if (reelFlowId() !== flowId) return;
    const script = activeScript();
    if (!script?.chat) return;

    // No ref guard: under StrictMode the first mount's loop is cancelled by its
    // cleanup, and the second (real) mount runs. A ref guard would block it.
    let cancelled = false;
    const beats = script.chat as ReelChatBeat[];
    const reduced = prefersReducedMotion();
    const setCaption = useReelUi.getState().setCaption;

    async function runOnce() {
      resetChatCursor();
      chat.reset?.();
      await wait(reduced ? 0 : 500);
      for (const b of beats) {
        if (cancelled) return;
        setCaption(b.caption);
        if (b.user === undefined) {
          // Opening greeting — no round-trip.
          chat.injectLeoMessage(b.reply.reply);
          await wait(reduced ? 0 : b.holdMs ?? 2200);
        } else {
          // Pause as if typing, then the user line lands.
          await wait(reduced ? 0 : Math.min(2600, 350 + b.user.length * 26));
          if (cancelled) return;
          await chat.sendTextMessage(b.user);
          // Reply latency (interception adds thinkMs) + dwell to read the canvas.
          await wait(reduced ? 0 : (b.thinkMs ?? 900) + (b.holdMs ?? 3500));
        }
      }
    }

    async function loop() {
      do {
        await runOnce();
        if (cancelled) return;
        await wait(2000);
      } while (!reduced && !cancelled);
    }

    void loop();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [flowId]);
}
