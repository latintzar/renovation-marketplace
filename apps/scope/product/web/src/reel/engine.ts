/**
 * Reel engine — runtime for the backend-free, auto-play portfolio reel.
 *
 * The reel drives the REAL product components against canned, production-shaped
 * data: no backend, no Supabase, no Stripe. Activation + flow selection live in
 * ./flag.ts. Per-flow scripts live in ./scripts/*. The single network chokepoint
 * is `apiFetch` in lib/api.ts, which calls `reelHandle()` here when `isReel()`.
 *
 * Nothing in this module runs unless reel mode is active, so it is a clean,
 * removable layer over the shipping product.
 */

import { create } from 'zustand';
import type {
  SendChatMessageResult,
  ProfileImportEvent,
} from '../lib/api';
import type { ReelFlowId } from './flag';
import { activeScript } from './registry';

// ---------------------------------------------------------------------------
// Script contract
// ---------------------------------------------------------------------------

/** Synthetic authed identity injected into AuthContext for a flow. */
export interface ReelIdentity {
  id: string;
  email: string;
  role: 'contractor' | 'homeowner';
  contractorId?: string;
  contractorName?: string;
  stripeConnected?: boolean;
}

/** One scripted turn of a chat-driven flow. */
export interface ReelChatBeat {
  /** One-line caption shown in the chrome for this beat. */
  caption: string;
  /** User line auto-typed for this beat. Omit for the opening Leo greeting. */
  user?: string;
  /** Canned agent response served when this beat's /v1/chat fires. */
  reply: SendChatMessageResult;
  /** Simulated agent latency before the reply (default 900ms). */
  thinkMs?: number;
  /** Dwell after the reply lands so the canvas can be read (default 3500ms). */
  holdMs?: number;
}

export interface ReelScript {
  flowId: ReelFlowId;
  /** Label for the in-app flow switcher. */
  label: string;
  /** SPA path (under basename) the reel navigates to for this flow. */
  route: string;
  /** Fake identity, or null for public/no-auth flows. */
  auth: ReelIdentity | null;
  /** Chat beats for chat-driven flows (post-job, set-milestones, import-profile intake). */
  chat?: ReelChatBeat[];
  /** Seed for the mutable data store (data-driven flows). Deep-cloned per loop. */
  initialData?: unknown;
  /** Canned REST responses for data-driven flows (canvas, quotes, milestones). */
  rest?: (pathname: string, method: string) => unknown | undefined;
  /** Frozen real SSE event stream for the profile-import flow. */
  sse?: ProfileImportEvent[];
}

// ---------------------------------------------------------------------------
// Caption store (reactive — read by the chrome caption strip / switcher)
// ---------------------------------------------------------------------------

interface ReelUiState {
  caption: string;
  setCaption: (c: string) => void;
}

export const useReelUi = create<ReelUiState>((set) => ({
  caption: '',
  setCaption: (caption) => set({ caption }),
}));

// ---------------------------------------------------------------------------
// Chat cursor — maps each POST /v1/chat to the next scripted reply.
// Module-level (read by the interception, not React state). Reset on loop.
// ---------------------------------------------------------------------------

let chatCursor = 0;

/** Beats that carry a user line (the ones that trigger a /v1/chat round-trip). */
export function chatUserBeats(): ReelChatBeat[] {
  return (activeScript()?.chat ?? []).filter((b) => b.user !== undefined);
}

export function resetChatCursor(): void {
  chatCursor = 0;
}

const delay = (ms: number) => new Promise<void>((res) => setTimeout(res, ms));

// ---------------------------------------------------------------------------
// Mutable data store — data-driven flows (Dashboard, ProjectDetail) read the
// current state through the apiFetch interception; drivers advance it (release
// a milestone, submit proof) and invalidate the query to re-render.
// ---------------------------------------------------------------------------

function clone<T>(v: T): T {
  try {
    return structuredClone(v);
  } catch {
    return JSON.parse(JSON.stringify(v)) as T;
  }
}

let mutableData: unknown = undefined;
let mutableFor: string | null = null;

/** Current mutable data for the active flow, lazily seeded from initialData. */
export function reelData<T = Record<string, unknown>>(): T {
  const script = activeScript();
  if (mutableFor !== (script?.flowId ?? null) || mutableData === undefined) {
    mutableData = clone(script?.initialData ?? {});
    mutableFor = script?.flowId ?? null;
  }
  return mutableData as T;
}

/** Mutate the current data in place. */
export function setReelData<T = Record<string, unknown>>(mutate: (d: T) => void): void {
  mutate(reelData<T>());
}

/** Reset to a fresh clone of initialData (used at the top of each loop). */
export function resetReelData(): void {
  const script = activeScript();
  mutableData = clone(script?.initialData ?? {});
  mutableFor = script?.flowId ?? null;
}

// ---------------------------------------------------------------------------
// Motion
// ---------------------------------------------------------------------------

export function prefersReducedMotion(): boolean {
  try {
    return window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  } catch {
    return false;
  }
}

// ---------------------------------------------------------------------------
// apiFetch interception — the single network chokepoint (must-fix #1)
// ---------------------------------------------------------------------------

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { 'content-type': 'application/json' },
  });
}

/**
 * Returns a canned Response when reel mode can serve this request, else null
 * (the caller then proceeds — and with VITE_API_URL=reel.invalid in the
 * vendored build, any unhandled call fails loudly instead of hitting a dead host).
 */
export function reelHandle(
  url: string,
  init?: RequestInit,
): Response | Promise<Response> | null {
  const script = activeScript();
  if (!script) return null;

  let pathname = url;
  try {
    pathname = new URL(url, window.location.origin).pathname;
  } catch {
    /* keep raw url */
  }
  const method = (init?.method ?? 'GET').toUpperCase();

  // Chat: serve the next scripted reply after a realistic "thinking" delay
  // (so the agent shimmer reads as real). The cursor stays in lockstep with
  // the driver, which sends exactly one user line per beat.
  if (method === 'POST' && pathname.endsWith('/v1/chat')) {
    const beats = chatUserBeats();
    const beat = beats[Math.min(chatCursor, beats.length - 1)];
    chatCursor += 1;
    const think = prefersReducedMotion() ? 0 : beat?.thinkMs ?? 900;
    return delay(think).then(() => jsonResponse(beat?.reply ?? { reply: '' }));
  }

  // Flow-specific canned REST data (canvas, quotes, milestone-updates, etc.).
  const rest = script.rest?.(pathname, method);
  if (rest !== undefined) return jsonResponse(rest);

  // Mutations and any other write: succeed as a no-op; the driver patches
  // local state itself.
  if (method !== 'GET') return jsonResponse({ ok: true });

  // Unknown GET (e.g. contractor lookup) — empty object keeps callers happy.
  return jsonResponse({});
}
