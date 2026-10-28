/**
 * Flow 3 — "Submit proof": a contractor marks a finished phase done by sending
 * photo proof to the homeowner for approval.
 *
 * Drives the real Dashboard page (/dashboard) — contractor identity, a canned
 * paid job. The SubmitProofSheet self-fills + submits in reel mode; the driver
 * (in Dashboard) just opens it at the right beat.
 */

import type { ReelScript } from '../engine';
import { reelData } from '../engine';
import type { ScopeSummary } from '../../lib/api';

interface DashboardData {
  scopes: (ScopeSummary & { milestones: { title: string; status: string }[] })[];
}

const initialData: DashboardData = {
  scopes: [
    {
      token: 'reel-job-1',
      title: 'Bathroom Renovation — Marbella',
      amount_total_cents: 720000,
      status: 'in_progress',
      payment_status: 'paid',
      milestones_total: 3,
      milestones_released: 1,
      created_at: '2026-06-20T09:00:00.000Z',
      milestones: [
        { title: 'Strip-out & first fix', status: 'released' },
        { title: 'Waterproofing & full-height tiling', status: 'in_progress' },
        { title: 'Fit-out & finish', status: 'pending' },
      ],
    },
  ],
};

export const submitProofScript: ReelScript = {
  flowId: 'submit-proof',
  label: 'Submit proof',
  route: '/dashboard',
  auth: {
    id: 'reel-contractor',
    email: 'james@reel.invalid',
    role: 'contractor',
    contractorId: 'reel-web-contractor',
    contractorName: 'James Mitchell',
    stripeConnected: true,
  },
  initialData,
  rest: (pathname) => {
    if (pathname.includes('/v1/quotes')) return { scopes: reelData<DashboardData>().scopes };
    return undefined;
  },
};
