/**
 * Flow 4 — "Approve & release": a homeowner reviews a finished phase and
 * releases the escrow payment milestone-by-milestone.
 *
 * Drives the real ProjectDetail page (/project/:token). Public route, but the
 * release controls require the homeowner identity (email must match the
 * canvas homeowner_email), provided via reel-mode auth.
 */

import type { ReelScript } from '../engine';
import { reelData } from '../engine';

/** Resolve a reel public asset in both dev (/app/) and the vendored build (/scope/app/). */
const asset = (f: string) => `${import.meta.env.BASE_URL}reel/${f}`;

interface ProjectData {
  canvas: Record<string, unknown>;
  milestoneUpdates: Record<string, unknown>[];
}

const initialData: ProjectData = {
  canvas: {
    title: 'Bathroom Renovation — Marbella',
    location: 'Marbella, Málaga',
    client_name: 'María',
    contractor_id: 'reel-pro-1',
    contractor_name: 'James Mitchell',
    contractor_trade: 'Bathroom specialist',
    homeowner_email: 'maria@reel.invalid',
    amount_total_cents: 720000,
    status: 'in_progress',
    payment_status: 'paid',
    milestones: [
      {
        title: 'Strip-out & first fix',
        description: 'Demolition, debris removal, waste relocation for the new shower.',
        amount: 1400,
        amount_cents: 140000,
        status: 'released',
      },
      {
        title: 'Waterproofing & full-height tiling',
        description: 'Tanking to wet areas, large-format porcelain tiling, grouted and sealed.',
        amount: 2100,
        amount_cents: 210000,
        status: 'proof_submitted',
      },
      {
        title: 'Fit-out & finish',
        description: 'Walk-in shower, wall-hung vanity, WC, snagging and handover.',
        amount: 1900,
        amount_cents: 190000,
        status: 'pending',
      },
    ],
  },
  milestoneUpdates: [
    {
      id: 'reel-mu-1',
      milestone_index: 1,
      photos: [asset('sample-attachment.png')],
      note: 'Waterproofing done, full-height tiling complete and grouted. Ready for your review.',
      status: 'proof_submitted',
      created_at: '2026-06-23T16:00:00.000Z',
    },
  ],
};

export const approveReleaseScript: ReelScript = {
  flowId: 'approve-release',
  label: 'Release a payment',
  route: '/project/reel',
  auth: {
    id: 'reel-homeowner',
    email: 'maria@reel.invalid',
    role: 'homeowner',
  },
  initialData,
  rest: (pathname) => {
    if (pathname.includes('/v1/canvas/')) return reelData<ProjectData>().canvas;
    if (pathname.includes('/v1/milestone-updates/')) return reelData<ProjectData>().milestoneUpdates;
    if (pathname.includes('/v1/variation-orders/')) return [];
    return undefined;
  },
};
