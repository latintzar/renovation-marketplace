/**
 * Typed HTTP client for Scope web ↔ FastAPI backend.
 * Base URL: VITE_API_URL or production api.leo.casa
 *
 * Canvas types (BriefUpdate, ProfileUpdate, QuoteUpdate, etc.) now live in
 * @scope/ui and are re-exported here for backwards compatibility.
 */

// Import canvas types from @scope/ui to use in interfaces
import type {
  BriefUpdate,
  ProfileUpdate,
  QuoteUpdate,
} from '@scope/ui';
import { isSandbox } from './utils';
import {localMode, appBase} from './runtime';
import { isReel } from '../reel/flag';
import { reelHandle } from '../reel/engine';
import { activeScript } from '../reel/registry';

// Re-export canvas types from @scope/ui — the canonical source
export type {
  BriefUpdate,
  ProfileUpdate,
  ProfileSource,
  ProfileProject,
  ProfileReview,
  QuoteUpdate,
  QuoteLineItem,
  QuoteContingencyDraft,
  ChangeOrderUpdate,
  ChangeOrderLineItem,
} from '@scope/ui';

const log = (msg: string, data?: Record<string, unknown>) => {
  if (import.meta.env.DEV) {
    // eslint-disable-next-line no-console
    console.debug(`[api] ${msg}`, data ?? '');
  }
};

const logError = (msg: string, err: unknown) => {
  // eslint-disable-next-line no-console
  console.error(`[api] ${msg}`, err);
};

export const API_BASE = localMode ? appBase : import.meta.env.VITE_API_URL?.replace(/\/$/, '') || 'http://127.0.0.1:18261';

// ---------------------------------------------------------------------------
// Auth token injection — wired up by AuthProvider on mount
// ---------------------------------------------------------------------------

/**
 * Getter function registered by AuthProvider.
 * Allows apiFetch to inject Authorization headers without creating a circular
 * dependency on AuthContext (which lives above api.ts in the import chain).
 */
let _getAccessToken: (() => Promise<string | null>) | null = null;

/** Called once by AuthProvider when it mounts. */
export function setAuthTokenGetter(fn: () => Promise<string | null>) {
  _getAccessToken = fn;
}

// ---------------------------------------------------------------------------
// Sandbox-aware, auth-aware fetch wrapper
// ---------------------------------------------------------------------------

/**
 * Returns X-Sandbox header when sandbox mode is active.
 * Uses the shared isSandbox() helper from utils to avoid key drift.
 */
function _sandboxHeaders(): Record<string, string> {
  return isSandbox() ? { 'X-Sandbox': 'true' } : {};
}

/**
 * fetch() wrapper that automatically merges:
 *   - X-Sandbox: true when sandbox mode is active
 *   - Authorization: Bearer <token> when the user is authenticated
 *
 * Use this for ALL backend calls — never use raw fetch() directly.
 */
// ---------------------------------------------------------------------------
// Internal JSON request helper
// ---------------------------------------------------------------------------

/**
 * Performs an apiFetch and parses JSON, returning a typed result.
 * On HTTP error, returns { ok: false, error: message }.
 * On network error, throws — callers should catch if needed.
 *
 * Used internally only. Not exported.
 */
async function jsonRequest<T extends object>(
  url: string,
  init?: RequestInit,
): Promise<(T & { ok: true }) | { ok: false; error: string }> {
  const res = await apiFetch(url, init);
  const body = await res.json().catch(() => ({})) as Record<string, unknown>;
  if (!res.ok) {
    return { ok: false, error: (body.detail as string) || (body.error as string) || `HTTP ${res.status}` };
  }
  return { ok: true, ...(body as T) };
}

export async function apiFetch(url: string, init?: RequestInit): Promise<Response> {
  // Reel mode: serve canned, production-shaped data with no network. The single
  // chokepoint for every backend call in the SPA.
  if (isReel()) {
    const canned = reelHandle(url, init);
    if (canned) return canned;
  }

  const sandboxH = _sandboxHeaders();
  const headers = new Headers(init?.headers);
  for (const [k, v] of Object.entries(sandboxH)) headers.set(k, v);

  // Inject JWT if available and not already set by caller
  if (_getAccessToken && !headers.has('Authorization')) {
    const token = await _getAccessToken();
    if (token) headers.set('Authorization', `Bearer ${token}`);
  }

  return fetch(url, { ...init, headers });
}

export type ChatMode = 'quote_intake' | 'quote' | 'early_access' | 'general';
export type ChatAudience = 'homeowner' | 'professional' | 'agent';

export interface ChatApiMessage {
  role: 'user' | 'assistant';
  text: string;
  images?: { media_type: string; data: string }[];
}

export interface ToolActivityItem {
  tool: string;
  label: string;
}

export interface SendChatMessageParams {
  messages: ChatApiMessage[];
  mode: ChatMode;
  audience: ChatAudience;
  leadContext?: string;
  profileContext?: string;
  pageLocale?: string;
  userLanguageHint?: string;
  /** Session/lead ID for mem0 memory continuity */
  userId?: string;
  /** True when the user has tapped confirm — unlocks phone collection phase */
  confirmed?: boolean;
  /** Contractor dossier ID (web-{uuid} or hc-{uuid}) for dossier lookups */
  contractorId?: string;
  /** Abort in-flight request (language toggle, navigation) */
  signal?: AbortSignal;
}

export interface DrawerState {
  content_type: 'brief' | 'profile' | 'custom' | 'reset';
  display?: 'inline' | 'banner' | 'fullscreen';
  status_text?: string;
  action_label?: string;
  action_id?: string;
  custom_title?: string;
  custom_body?: string;
  accent?: 'default' | 'highlight';
  auto_open?: boolean;
}

export interface SendChatMessageResult {
  reply: string;
  brief_update?: BriefUpdate;
  profile_update?: ProfileUpdate;
  quote_update?: QuoteUpdate;
  tool_activity?: ToolActivityItem[];
  show_drawer?: boolean;
  drawer_state?: DrawerState;
  cost_usd?: number;
  tokens?: number;
  model_used?: string;
  error?: string;
  copy_blocks?: string[];
  /** True when fetch was aborted — caller should ignore reply */
  aborted?: boolean;
}

export async function sendChatMessage(params: SendChatMessageParams): Promise<SendChatMessageResult> {
  const url = `${API_BASE}/v1/chat`;
  log('POST chat', { mode: params.mode, audience: params.audience, n: params.messages.length });
  try {
    const res = await apiFetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: params.signal,
      body: JSON.stringify({
        messages: params.messages,
        mode: params.mode,
        audience: params.audience,
        lead_context: params.leadContext ?? '',
        profile_context: params.profileContext ?? '',
        page_locale: params.pageLocale ?? '',
        user_language_hint: params.userLanguageHint ?? '',
        user_id: params.userId ?? '',
        confirmed: params.confirmed ?? false,
        contractor_id: params.contractorId ?? '',
      }),
    });
    const data = (await res.json()) as SendChatMessageResult & { error?: string };
    if (!res.ok) {
      logError('chat HTTP error', { status: res.status, body: data });
      return { reply: '', error: data.error || `HTTP ${res.status}` };
    }
    return data;
  } catch (e) {
    if (params.signal?.aborted || (e instanceof DOMException && e.name === 'AbortError')) {
      log('chat fetch aborted', {});
      return { reply: '', aborted: true };
    }
    logError('chat fetch failed', e);
    return { reply: '', error: e instanceof Error ? e.message : 'network error' };
  }
}

export interface TranscribeResult {
  text: string;
  lang?: string;
  error?: string;
}

export async function transcribeAudio(blob: Blob, opts?: { polish?: boolean }): Promise<TranscribeResult> {
  const polish = opts?.polish ?? false;
  const url = `${API_BASE}/api/transcribe?polish=${polish ? 'true' : 'false'}&provider=auto`;
  const mime = blob.type || 'audio/webm';
  const fd = new FormData();
  fd.append('audio', blob, `recording.${mime.includes('webm') ? 'webm' : 'ogg'}`);
  log('POST transcribe', { bytes: blob.size, mime });
  try {
    const res = await apiFetch(url, { method: 'POST', body: fd });
    const data = (await res.json()) as { text?: string; lang?: string; error?: string };
    if (!res.ok) {
      logError('transcribe HTTP error', { status: res.status, data });
      return { text: '', error: data.error || `HTTP ${res.status}` };
    }
    return { text: (data.text || '').trim(), lang: data.lang };
  } catch (e) {
    logError('transcribe fetch failed', e);
    return { text: '', error: e instanceof Error ? e.message : 'network error' };
  }
}

export interface UploadPhotosResult {
  urls: string[];
  ok: boolean;
  error?: string;
}

export async function uploadPhotos(leadId: string, photos: File[]): Promise<UploadPhotosResult> {
  if (!leadId || !photos.length) {
    return { urls: [], ok: false, error: 'missing lead or files' };
  }
  const url = `${API_BASE}/api/leads/photos`;
  const fd = new FormData();
  fd.append('lead_id', leadId);
  for (const f of photos.slice(0, 10)) {
    fd.append('photos', f);
  }
  log('POST leads/photos', { leadId, count: photos.length });
  try {
    const res = await apiFetch(url, { method: 'POST', body: fd });
    const data = (await res.json()) as { ok?: boolean; urls?: string[]; error?: string };
    if (!res.ok) {
      logError('uploadPhotos HTTP error', { status: res.status, data });
      return { urls: [], ok: false, error: data.error || `HTTP ${res.status}` };
    }
    return { urls: data.urls ?? [], ok: data.ok !== false };
  } catch (e) {
    logError('uploadPhotos failed', e);
    return { urls: [], ok: false, error: e instanceof Error ? e.message : 'network error' };
  }
}


export type ProfileImportEvent =
  | { type: 'progress'; step: string; percent?: number }
  | { type: 'result'; profile: Record<string, unknown> }
  | { type: 'error'; message: string }
  | { type: string; [k: string]: unknown };

/**
 * SSE stream from POST /api/profile-import — yields parsed event objects.
 */
export async function* importProfile(url: string, contractorId?: string): AsyncGenerator<ProfileImportEvent> {
  // Reel mode: replay a frozen real import stream (progress beats + final
  // profile) with no network. See reel/scripts/import-profile.
  if (isReel()) {
    const sse = activeScript()?.sse ?? [];
    for (const evt of sse) {
      await new Promise((r) => setTimeout(r, 700));
      yield evt;
    }
    return;
  }

  const endpoint = `${API_BASE}/api/profile-import`;
  log('POST profile-import SSE', { url, contractorId });
  let res: Response;
  try {
    res = await apiFetch(endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', Accept: 'text/event-stream' },
      body: JSON.stringify({ url, contractor_id: contractorId ?? '' }),
    });
  } catch (e) {
    logError('profile-import fetch failed', e);
    yield { type: 'error', message: e instanceof Error ? e.message : 'network error' };
    return;
  }
  if (!res.ok || !res.body) {
    const t = await res.text();
    logError('profile-import bad response', { status: res.status, t: t.slice(0, 200) });
    yield { type: 'error', message: `HTTP ${res.status}` };
    return;
  }

  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = '';

  try {
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      const parts = buf.split('\n\n');
      buf = parts.pop() ?? '';
      for (const block of parts) {
        const line = block
          .split('\n')
          .find((l) => l.startsWith('data: '));
        if (!line) continue;
        const json = line.slice(6).trim();
        if (!json) continue;
        try {
          yield JSON.parse(json) as ProfileImportEvent;
        } catch (e) {
          logError('profile-import SSE parse', e);
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

export interface ExtractDocResult {
  markdown: string;
  chars: number;
  filename: string;
  error?: string;
}

/**
 * Fire-and-forget signal: user is composing (typing/recording) or stopped.
 * Lightweight — no response needed. Backend uses this to hold off premature replies.
 */
export function signalComposing(userId: string, composing: boolean, inputType: 'text' | 'voice' | null): void {
  if (!userId) return;
  const url = `${API_BASE}/api/composing`;
  log('POST composing', { userId: userId.slice(0, 8), composing, inputType });
  apiFetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_id: userId, composing, input_type: inputType }),
    keepalive: true,
  }).catch(() => {});
}

export async function extractDocument(file: File): Promise<ExtractDocResult> {
  const url = `${API_BASE}/api/extract-doc`;
  const fd = new FormData();
  fd.append('file', file);
  log('POST extract-doc', { name: file.name, bytes: file.size });
  try {
    const res = await apiFetch(url, { method: 'POST', body: fd });
    const data = (await res.json()) as ExtractDocResult;
    if (!res.ok) {
      logError('extract-doc HTTP error', { status: res.status, data });
      return { markdown: '', chars: 0, filename: file.name, error: data.error || `HTTP ${res.status}` };
    }
    return data;
  } catch (e) {
    logError('extract-doc failed', e);
    return { markdown: '', chars: 0, filename: file.name, error: e instanceof Error ? e.message : 'network error' };
  }
}


// ── Job Inbox API ─────────────────────────────────────────────────────

export interface InboxJob {
  id: string;
  brief: BriefUpdate;
  brief_photos: string[];
  status: string;
  outreach_count: number;
  outreach_approval_status?: 'pending_approval' | 'approved' | 'rejected' | null;
  houzz_candidates_count?: number;
  fb_candidates_count?: number;
  created_at: string;
}

export interface InboxResponse {
  id: string;
  contractor_name: string;
  contractor_phone: string;
  source: string;
  houzz_profile_url?: string;
  voice_transcript?: string;
  reaction?: string;
  site_visit_needs?: string;
  availability?: string;
  profile: ProfileUpdate | Record<string, never>;
  ai_rank?: number;
  ai_commentary?: string;
  onboarding_complete: boolean;
  created_at: string;
}

export interface InboxData {
  job: InboxJob;
  responses: InboxResponse[];
  total_responses: number;
  error?: string;
}

export async function fetchInbox(token: string): Promise<InboxData> {
  const url = `${API_BASE}/v1/inbox/${encodeURIComponent(token)}`;
  log('GET inbox', { token: token.slice(0, 8) });
  try {
    const res = await apiFetch(url);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      logError('inbox HTTP error', { status: res.status, data });
      return {
        job: { id: '', brief: {} as BriefUpdate, brief_photos: [], status: '', outreach_count: 0, created_at: '' },
        responses: [],
        total_responses: 0,
        error: (data as { detail?: string }).detail || `HTTP ${res.status}`,
      };
    }
    return (await res.json()) as InboxData;
  } catch (e) {
    logError('inbox fetch failed', e);
    return {
      job: { id: '', brief: {} as BriefUpdate, brief_photos: [], status: '', outreach_count: 0, created_at: '' },
      responses: [],
      total_responses: 0,
      error: e instanceof Error ? e.message : 'network error',
    };
  }
}


export async function approveOutreach(
  token: string,
): Promise<{ ok: boolean; status?: string; candidates_count?: number; message?: string; error?: string }> {
  const url = `${API_BASE}/v1/inbox/${encodeURIComponent(token)}/approve-outreach`;
  log('POST approve-outreach', { token: token.slice(0, 8) });
  try {
    return await jsonRequest<{ status?: string; candidates_count?: number; message?: string }>(url, { method: 'POST' });
  } catch (e) {
    logError('approve-outreach failed', e);
    return { ok: false, error: e instanceof Error ? e.message : 'network error' };
  }
}



// ── Canvas API (shareable URLs) ──────────────────────────────────────

export interface CanvasData {
  canvas_type: 'brief' | 'profile' | 'quote' | 'scope';
  brief?: BriefUpdate;
  profile?: ProfileUpdate;
  scope?: QuoteUpdate;
  /** Alias for scope — returned by /v1/canvas when canvas_type is 'quote' */
  quote?: QuoteUpdate;
  /** Alternate key for backward compat */
  quote_data?: QuoteUpdate;
  photos?: string[];
  /** Contractor ID — returned for profile and scope canvases */
  contractor_id?: string;
  /** For scope canvases: the scope's own token */
  quote_token?: string;
  /** For scope canvases: finalized | draft */
  status?: string;
  /** Whether the profile has been claimed via Google OAuth */
  claimed?: boolean;
  /** Whether Stripe Connect onboarding is complete */
  stripe_onboarding_complete?: boolean;
  /** For scope canvases: unpaid | paid */
  payment_status?: string;
  /** For scope canvases: amount paid in cents */
  amount_total_cents?: number;
  /** True if this scope was created in sandbox mode — homeowner browser auto-enables sandbox */
  is_sandbox?: boolean;
  error?: string;
}

export async function fetchCanvas(token: string): Promise<CanvasData> {
  const url = `${API_BASE}/v1/canvas/${encodeURIComponent(token)}`;
  log('GET canvas', { token: token.slice(0, 8) });
  try {
    const res = await apiFetch(url);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      logError('canvas HTTP error', { status: res.status, data });
      return { canvas_type: 'brief', error: (data as { detail?: string }).detail || `HTTP ${res.status}` };
    }
    return (await res.json()) as CanvasData;
  } catch (e) {
    logError('canvas fetch failed', e);
    return { canvas_type: 'brief', error: e instanceof Error ? e.message : 'network error' };
  }
}


// ── Scope Finalize API ────────────────────────────────────────────────

export interface ScopeFinalizeResult {
  ok: boolean;
  token?: string;
  canvas_url?: string;
  error?: string;
}

export async function finalizeScope(
  contractorId: string,
  scopeData: QuoteUpdate,
  authUserId?: string,
): Promise<ScopeFinalizeResult> {
  const url = `${API_BASE}/v1/quote/finalize`;
  log('POST scope/finalize', { contractor: contractorId.slice(0, 8) });
  try {
    return await jsonRequest<ScopeFinalizeResult>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contractor_id: contractorId, scope_data: scopeData, auth_user_id: authUserId ?? null }),
    });
  } catch (e) {
    logError('scope finalize fetch failed', e);
    return { ok: false, error: e instanceof Error ? e.message : 'network error' };
  }
}

// ── Claim Profile API ─────────────────────────────────────────────────

export interface ClaimProfileResult {
  ok: boolean;
  contractor_id?: string;
  auth_user_id?: string;
  claimed?: boolean;
  error?: string;
}

export async function claimProfile(
  canvasToken: string,
  accessToken: string,
): Promise<ClaimProfileResult> {
  const url = `${API_BASE}/v1/claim-profile`;
  log('POST claim-profile', { token: canvasToken.slice(0, 8) });
  try {
    return await jsonRequest<ClaimProfileResult>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ canvas_token: canvasToken, access_token: accessToken }),
    });
  } catch (e) {
    logError('claim profile fetch failed', e);
    return { ok: false, error: e instanceof Error ? e.message : 'network error' };
  }
}

// ── Stripe Connect API ────────────────────────────────────────────────

export interface StripeAccountStatus {
  ok: boolean;
  has_account: boolean;
  stripe_account_id?: string;
  charges_enabled: boolean;
  payouts_enabled: boolean;
  details_submitted: boolean;
  onboarding_complete: boolean;
  requirements?: {
    currently_due: string[];
    eventually_due: string[];
    pending_verification: string[];
  };
  error?: string;
}

export async function createStripeAccount(
  contractorId: string,
  opts?: { email?: string; firstName?: string; lastName?: string },
): Promise<{ ok: boolean; stripe_account_id?: string; existing?: boolean; error?: string }> {
  const url = `${API_BASE}/v1/stripe/create-account`;
  log('POST stripe/create-account', { contractor: contractorId.slice(0, 8) });
  try {
    return await jsonRequest<{ stripe_account_id?: string; existing?: boolean }>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contractor_id: contractorId, email: opts?.email ?? null, first_name: opts?.firstName ?? null, last_name: opts?.lastName ?? null }),
    });
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : 'network error' };
  }
}

export async function getStripeAccountLink(
  contractorId: string,
): Promise<{ ok: boolean; url?: string; error?: string }> {
  const apiUrl = `${API_BASE}/v1/stripe/account-link`;
  const returnUrl = `${window.location.origin}${import.meta.env.BASE_URL}stripe/complete?contractor=${encodeURIComponent(contractorId)}`;
  const refreshUrl = `${window.location.origin}${import.meta.env.BASE_URL}stripe/refresh?contractor=${encodeURIComponent(contractorId)}`;
  log('POST stripe/account-link', { contractor: contractorId.slice(0, 8) });
  try {
    return await jsonRequest<{ url?: string }>(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ contractor_id: contractorId, return_url: returnUrl, refresh_url: refreshUrl }),
    });
  } catch (e) {
    return { ok: false, error: e instanceof Error ? e.message : 'network error' };
  }
}

const STRIPE_STATUS_EMPTY: StripeAccountStatus = { ok: false, has_account: false, charges_enabled: false, payouts_enabled: false, details_submitted: false, onboarding_complete: false };

export async function getStripeAccountStatus(contractorId: string): Promise<StripeAccountStatus> {
  const url = `${API_BASE}/v1/stripe/account-status?contractor_id=${encodeURIComponent(contractorId)}`;
  log('GET stripe/account-status', { contractor: contractorId.slice(0, 8) });
  try {
    return await jsonRequest<StripeAccountStatus>(url) as StripeAccountStatus;
  } catch (e) {
    return { ...STRIPE_STATUS_EMPTY, error: e instanceof Error ? e.message : 'network error' };
  }
}


export interface ScopeSummary {
  token: string;
  title: string;
  /** Total homeowner pays in cents (milestones + materials + Leo fee + IVA). Use this, not total. */
  amount_total_cents?: number;
  /** @deprecated Use amount_total_cents. Kept for backward compat — milestones sum only. */
  total?: number;
  materials_upfront_cents?: number;
  status: string;
  payment_status: string;
  /** Total number of milestone phases */
  milestones_total?: number;
  /** Number of phases released (paid) to contractor */
  milestones_released?: number;
  created_at: string;
  started_at?: string | null;
  completed_at?: string | null;
}

export interface ContractorScopesResult {
  scopes: ScopeSummary[];
  error?: string;
}

export async function fetchContractorScopes(contractorId: string): Promise<ContractorScopesResult> {
  const url = `${API_BASE}/v1/quotes?contractor_id=${encodeURIComponent(contractorId)}`;
  log('GET scopes', { contractor: contractorId.slice(0, 8) });
  try {
    const res = await apiFetch(url);
    if (!res.ok) {
      const data = (await res.json().catch(() => ({}))) as { detail?: string };
      return { scopes: [], error: data.detail || `HTTP ${res.status}` };
    }
    return (await res.json()) as ContractorScopesResult;
  } catch (e) {
    logError('fetch contractor scopes failed', e);
    return { scopes: [], error: e instanceof Error ? e.message : 'network error' };
  }
}

export interface UpdateScopeResult {
  ok: boolean;
  token?: string;
  canvas_url?: string;
  error?: string;
}

export async function updateScope(
  token: string,
  scopeData: QuoteUpdate,
  contractorId: string,
): Promise<UpdateScopeResult> {
  const url = `${API_BASE}/v1/quote/update`;
  log('POST scope/update', { token: token.slice(0, 8) });
  try {
    return await jsonRequest<UpdateScopeResult>(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token, scope_data: scopeData, contractor_id: contractorId }),
    });
  } catch (e) {
    logError('scope update fetch failed', e);
    return { ok: false, error: e instanceof Error ? e.message : 'network error' };
  }
}

// ── Ops Monitor API ───────────────────────────────────────────────────

export interface OpsContractor {
  id: string;
  name: string;
  phone: string;
  source: string;
  has_voice: boolean;
  reaction: string;
  availability: string;
  onboarded: boolean;
  ai_rank?: number;
  ai_commentary: string;
  houzz_url: string;
  outreach_stage: string;
  followup_count: number;
  created_at: string;
}

export interface OpsJob {
  id: string;
  title: string;
  location: string;
  status: string;
  homeowner_phone: string;
  inbox_token: string;
  inbox_url: string;
  outreach_count: number;
  total_responses: number;
  responded: number;
  onboarded: number;
  pipeline: Record<string, number>;
  created_at: string;
  contractors: OpsContractor[];
}

export interface OpsData {
  ops_token: string;
  total_jobs: number;
  total_outreach: number;
  total_responses: number;
  pipeline: Record<string, number>;
  jobs: OpsJob[];
  error?: string;
}

export async function fetchOps(token: string): Promise<OpsData> {
  const url = `${API_BASE}/v1/ops/${encodeURIComponent(token)}`;
  log('GET ops', { token: token.slice(0, 8) });
  try {
    const res = await apiFetch(url);
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      return { ops_token: '', total_jobs: 0, total_outreach: 0, total_responses: 0, pipeline: {}, jobs: [], error: (data as { detail?: string }).detail || `HTTP ${res.status}` };
    }
    return (await res.json()) as OpsData;
  } catch (e) {
    logError('ops fetch failed', e);
    return { ops_token: '', total_jobs: 0, total_outreach: 0, total_responses: 0, pipeline: {}, jobs: [], error: e instanceof Error ? e.message : 'network error' };
  }
}
