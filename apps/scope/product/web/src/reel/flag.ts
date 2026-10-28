/**
 * Reel mode — the backend-free, auto-play "portfolio reel" of the Scope product.
 *
 * Activated by `?reel=<flowId>` in the URL (persisted to localStorage so it
 * survives the SPA's internal navigation between flow routes). When active,
 * the app runs a scripted, self-driving demo of one flow against canned data:
 * no backend, no Supabase, no Stripe. See apps/scope/company/decisions/
 * scope-portfolio-spec-2026-06-23.md.
 *
 * Mirrors the `isSandbox()` helper in lib/utils.ts: a tiny pure reader, no
 * React, so it can be called from lib/api.ts (apiFetch) and context/AuthContext
 * alike without an import cycle.
 */

/** The five portfolio-reel flows, in product-story order. */
export const REEL_FLOWS = [
  'post-job', // 1. homeowner chat -> priced, milestoned brief
  'set-milestones', // 2. contractor sets milestones in chat
  'submit-proof', // 3. contractor submits proof of a milestone (Dashboard)
  'approve-release', // 4. homeowner approves + releases a milestone (ProjectDetail)
  'import-profile', // 5. contractor imports a real profile from a link
] as const;

export type ReelFlowId = (typeof REEL_FLOWS)[number];

const STORAGE_KEY = 'leo_reel_flow';

function isReelFlowId(v: string | null): v is ReelFlowId {
  return !!v && (REEL_FLOWS as readonly string[]).includes(v);
}

/**
 * Resolve the active reel flow, or null when reel mode is off.
 * Order: `?reel=<id>` query param (sticks it to localStorage) -> localStorage.
 * `?reel=off` / `?reel=0` clears it. Invalid ids are ignored (treated as off).
 */
export function reelFlowId(): ReelFlowId | null {
  try {
    const qp = new URLSearchParams(window.location.search).get('reel');
    if (qp !== null) {
      if (qp === 'off' || qp === '0' || qp === 'false') {
        localStorage.removeItem(STORAGE_KEY);
        return null;
      }
      if (isReelFlowId(qp)) {
        localStorage.setItem(STORAGE_KEY, qp);
        return qp;
      }
      // Unknown value: turn reel on with no specific flow is meaningless — ignore.
      return null;
    }
    const stored = localStorage.getItem(STORAGE_KEY);
    return isReelFlowId(stored) ? stored : null;
  } catch {
    return null;
  }
}

/** True when the app is running as a portfolio reel (any flow). */
export function isReel(): boolean {
  return reelFlowId() !== null;
}
