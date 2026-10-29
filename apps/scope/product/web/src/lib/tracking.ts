/**
 * tracking.ts — Unified event tracking library
 *
 * Wraps PostHog with an abstraction that is compatible with Intercom and Crisp.
 * Adding either support tool later is a one-line change in each stub below.
 *
 * Rules:
 * - Only initialises after the user accepts GDPR cookie consent via initTracking()
 * - track() before consent is a complete no-op — PostHog AND backend events are
 *   both gated behind _initialized to prevent pre-consent data collection
 * - Sandbox events are tagged {is_sandbox: true} and skipped in PostHog
 *   (they still land in the backend activity_events table when consent is given)
 *
 * Usage:
 *   import { initTracking, identify, track } from '@/lib/tracking';
 *
 *   initTracking();                          // in App.tsx after consent
 *   identify('contractor-uuid', { name: 'Ana' });
 *   track('quote.created', { token, value_cents });
 */

import posthog from 'posthog-js';

import { API_BASE, apiFetch } from './api';
import { isSandbox } from './utils';
import {localMode} from './runtime';

// ---------------------------------------------------------------------------
// Internal state
// ---------------------------------------------------------------------------

let _initialized = false;
let _sandbox = false;

// ---------------------------------------------------------------------------
// Init
// ---------------------------------------------------------------------------

/**
 * Initialise PostHog. Call this once after cookie consent is granted.
 * Safe to call multiple times — only initialises on first call.
 */
export function initTracking(): void {
  if (localMode) return;
  if (_initialized) return;
  _sandbox = isSandbox();

  const key = import.meta.env.VITE_POSTHOG_KEY as string | undefined;
  if (!key) {
    if (import.meta.env.DEV) {
      // eslint-disable-next-line no-console
      console.debug('[tracking] No VITE_POSTHOG_KEY — PostHog disabled');
    }
    _initialized = true;
    return;
  }

  posthog.init(key, {
    api_host: 'https://eu.i.posthog.com', // EU for GDPR compliance
    persistence: 'localStorage',
    autocapture: false,       // explicit events only — no noise
    capture_pageview: false,  // we fire these manually for SPA accuracy
    disable_session_recording: _sandbox, // never record sandbox sessions
  });

  _initialized = true;
}

// ---------------------------------------------------------------------------
// Identity
// ---------------------------------------------------------------------------

/**
 * Associate subsequent events with a user.
 * Call after login / session restore.
 */
export function identify(userId: string, traits?: Record<string, unknown>): void {
  if (localMode) return;
  if (!userId) return;

  posthog.identify(userId, traits as Record<string, string>);

  // Intercom stub (add when ready):
  // window.Intercom?.('update', { user_id: userId, ...traits });

  // Crisp stub (add when ready):
  // window.$crisp?.push(['set', 'user:email', [traits?.email]]);
  // window.$crisp?.push(['set', 'session:data', [[['user_id', userId]]]]);
}

// ---------------------------------------------------------------------------
// Track
// ---------------------------------------------------------------------------

/**
 * Fire a named event with optional properties.
 *
 * Sandbox events are tagged is_sandbox=true and skipped in PostHog.
 * All events (including sandbox) are sent to the backend activity_events table.
 */
export function track(event: string, properties?: Record<string, unknown>): void {
  _sandbox = isSandbox(); // re-read in case it changed
  const enriched = { ...properties, is_sandbox: _sandbox };

  if (!_initialized) return; // no-op before consent

  if (!_sandbox) {
    posthog.capture(event, enriched);

    // Intercom stub:
    // window.Intercom?.('trackEvent', event, enriched);

    // Crisp stub:
    // window.$crisp?.push(['set', 'session:event', [[event, enriched]]]);
  }

  // Send to backend (consent already confirmed above)
  _sendToBackend(event, enriched);
}


// ---------------------------------------------------------------------------
// Backend persistence (fire-and-forget)
// ---------------------------------------------------------------------------

function _sendToBackend(event: string, properties: Record<string, unknown>): void {
  // We extract identity from properties if available, or from localStorage
  let userId = (properties.contractor_id as string) || (properties.user_id as string) || '';
  let quoteToken = (properties.token as string) || (properties.quote_token as string) || '';
  let phone = (properties.phone as string) || '';

  if (!userId) {
    try {
      const auth = JSON.parse(sessionStorage.getItem('leo_auth') || '{}') as Record<string, string>;
      userId = auth.contractor_id || '';
    } catch { /* ignore */ }
  }

  const payload = {
    event,
    user_id: userId,
    quote_token: quoteToken,
    phone,
    properties,
    is_sandbox: _sandbox,
  };

  apiFetch(`${API_BASE}/api/events/track`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
    keepalive: true,
  }).catch(() => {});
}
