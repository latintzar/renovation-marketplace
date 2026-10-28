/**
 * Landing page → React app handoff via sessionStorage.
 *
 * The landing page writes a JSON blob to `leo_handoff` before navigating
 * to /app/onboard/*. This module reads it once and deletes it so the
 * handoff data doesn't re-fire on refresh.
 */

const HANDOFF_KEY = 'leo_handoff';

export interface HandoffData {
  text?: string;
  lang?: string;
  location?: string;
  phone?: string;
  import?: string;
  jobId?: string;
  /** Set to true when the contractor wants to edit their profile (skips import, opens chat with preview) */
  edit?: boolean;
  /** Contractor ID for the edit flow — links back to the already-imported profile */
  contractorId?: string;
  /** Set when the imported phone differs from the known phone for a contractor */
  phone_discrepancy?: { habitissimo_phone: string; known_phone: string };
}

/**
 * Read and delete the handoff payload. Returns an empty object if
 * there's nothing (direct navigation, refresh, or already consumed).
 */
export function consumeHandoff(): HandoffData {
  try {
    const raw = sessionStorage.getItem(HANDOFF_KEY);
    const data: HandoffData = raw ? JSON.parse(raw) : {};
    if (raw) sessionStorage.removeItem(HANDOFF_KEY);

    const params = new URLSearchParams(window.location.search);
    if (params.get('jobId')) data.jobId = params.get('jobId')!;
    if (params.get('phone')) data.phone = params.get('phone')!;
    if (params.get('import') || params.get('importUrl')) {
      data.import = params.get('import') || params.get('importUrl') || undefined;
    }
    if (params.get('edit') === '1' || params.get('edit') === 'true') data.edit = true;
    if (params.get('contractorId')) data.contractorId = params.get('contractorId')!;

    return data;
  } catch {
    return {};
  }
}
