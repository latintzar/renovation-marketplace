/**
 * Flow 2 — "Set milestones": a contractor describes a job and Leo turns it into
 * a phased, priced scope (milestones) in real time.
 *
 * Drives the real FirstQuote page (/quote/first, useChat mode 'quote' /
 * audience 'professional', renders QuoteCanvas). Contractor-gated route — needs
 * a synthetic contractor identity.
 */

import type { ReelScript } from '../engine';
import type { QuoteUpdate } from '../../lib/api';

const base = {
  title: 'Bathroom Renovation — Marbella',
  contractor_name: 'James Mitchell',
  client_name: 'Homeowner',
  location: 'Marbella, Málaga',
  service_fee_percent: 5,
  created_at: '2026-06-24T09:00:00.000Z',
};

const scopeStep1: QuoteUpdate = {
  ...base,
  description: 'Full bathroom strip-out and refit: walk-in shower conversion, retile, new vanity and WC.',
  line_items: [
    { description: 'Strip-out & first fix (demolition, waste relocation)', amount: 1400, duration_label: '3 días' },
  ],
  terms: [],
  status: 'draft',
};

const scopeStep2: QuoteUpdate = {
  ...base,
  description: 'Full bathroom strip-out and refit: walk-in shower conversion, retile, new vanity and WC. Phased into three milestones.',
  line_items: [
    { description: 'Strip-out & first fix (demolition, waste relocation)', amount: 1400, duration_label: '3 días' },
    { description: 'Waterproofing & full-height tiling', amount: 2100, duration_label: '4 días' },
    { description: 'Fit-out & finish (shower, vanity, WC, snagging)', amount: 1900, duration_label: '3 días' },
  ],
  terms: ['Work guaranteed for 12 months', 'Client supplies sanitaryware unless agreed otherwise'],
  status: 'draft',
};

const scopeReady: QuoteUpdate = {
  ...base,
  description: 'Full bathroom strip-out and refit: walk-in shower conversion, retile, new vanity and WC. Three milestones, paid on completion of each via escrow.',
  line_items: [
    { description: 'Strip-out & first fix (demolition, waste relocation)', amount: 1400, duration_label: '3 días' },
    { description: 'Waterproofing & full-height tiling', amount: 2100, duration_label: '4 días' },
    { description: 'Fit-out & finish (shower, vanity, WC, snagging)', amount: 1900, duration_label: '3 días' },
  ],
  materials_upfront: 1800,
  iva_rate: 10,
  terms: ['Work guaranteed for 12 months', 'Client supplies sanitaryware unless agreed otherwise'],
  status: 'ready',
};

export const setMilestonesScript: ReelScript = {
  flowId: 'set-milestones',
  label: 'Build a scope',
  route: '/quote/first',
  auth: {
    id: 'reel-contractor',
    email: 'james@reel.invalid',
    role: 'contractor',
    contractorId: 'reel-web-contractor',
    contractorName: 'James Mitchell',
    stripeConnected: true,
  },
  chat: [
    {
      caption: 'A contractor starts a quote — by talking, not filling a form.',
      reply: {
        reply:
          "Tell me about the job — what it is, where, and the phases with rough price and duration. You can say it all at once, even as a voice note. Tap 👁 to watch the quote build.",
      },
      holdMs: 2400,
    },
    {
      caption: 'They describe the job in plain language.',
      user: "Bathroom reno in Marbella — strip it out, convert to a walk-in shower, retile, new vanity and WC. About two weeks of work.",
      thinkMs: 1300,
      reply: {
        reply:
          "Great. I've started the scope. Want me to phase it so the homeowner pays per stage through escrow? Tell me the phases and I'll price them.",
        quote_update: scopeStep1,
        tool_activity: [{ tool: 'draft_scope', label: 'Drafting the scope' }],
      },
      holdMs: 3400,
    },
    {
      caption: 'Leo phases it into milestones, priced and timed — live.',
      user: "Yes: phase one strip-out and first fix, phase two waterproofing and tiling, phase three fit-out and finish.",
      thinkMs: 1500,
      reply: {
        reply:
          "Done — three milestones, each with price and duration. The homeowner releases each payment only when that phase is signed off. Anything on materials or IVA?",
        quote_update: scopeStep2,
        tool_activity: [{ tool: 'price_milestones', label: 'Pricing the milestones' }],
      },
      holdMs: 4200,
    },
    {
      caption: 'Scope is ready — escrow-backed, milestone by milestone.',
      user: "Materials are about 1,800 upfront, and 10% IVA.",
      thinkMs: 1400,
      reply: {
        reply:
          "Locked in: €1,800 materials upfront, 10% IVA, three milestones released on completion. Your scope is ready to send — the homeowner gets a clear, escrow-backed agreement.",
        quote_update: scopeReady,
        tool_activity: [{ tool: 'finalize_scope', label: 'Finalizing the scope' }],
      },
      holdMs: 5200,
    },
  ],
};
