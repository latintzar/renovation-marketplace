/**
 * Flow 1 — "Post a job": a homeowner describes a renovation in plain language
 * and Leo turns it into a structured, priced-context brief.
 *
 * Drives the real OnboardHomeowner page (/onboard/homeowner,
 * useChat mode 'quote_intake' / audience 'homeowner', renders BriefCanvas).
 * Public route — no fake auth needed.
 */

import type { ReelScript } from '../engine';
import type { BriefUpdate } from '../../lib/api';

// Brief built up progressively across the conversation.
const briefStep1: BriefUpdate = {
  title: 'Bathroom Renovation',
  description: 'Dated family bathroom. Shower has been leaking; homeowner wants a full refit.',
  location: '',
  urgency: '',
  materials_mentioned: '',
  measurements: '',
  budget_indication: '',
  status: 'needs_more_info',
};

const briefStep2: BriefUpdate = {
  title: 'Bathroom Renovation',
  description:
    'Strip existing tiles & fittings. Replace cracked tiling and convert to a walk-in shower. Supply and fit new vanity, WC and thermostatic shower valve.',
  location: 'Marbella, Málaga',
  urgency: '',
  materials_mentioned: '',
  measurements: '≈ 7 m²',
  budget_indication: '',
  status: 'workable',
};

const briefSolid: BriefUpdate = {
  title: 'Bathroom Renovation',
  description:
    'Strip existing tiles & fittings. Convert to a walk-in shower. Supply and fit wall-hung vanity, rimless WC and thermostatic shower valve. Full-height tiling in wet areas, half-height elsewhere.',
  location: 'Marbella, Málaga',
  urgency: 'Within the next month',
  materials_mentioned: 'Walk-in shower, wall-hung vanity, large-format tiles',
  measurements: '≈ 7 m² (2.4 m × 3.1 m)',
  budget_indication: '€8,000 (approx.)',
  status: 'solid',
};

export const postJobScript: ReelScript = {
  flowId: 'post-job',
  label: 'Post a job',
  route: '/onboard/homeowner',
  auth: null,
  chat: [
    {
      caption: 'A homeowner opens the chat — no forms, just a conversation.',
      // Opening greeting — injected directly, no round-trip.
      reply: {
        reply:
          "Hi — I'm Leo. Tell me what you need doing at home, in your own words. A photo helps too.",
      },
      holdMs: 2200,
    },
    {
      caption: 'They describe the job in plain language.',
      user: "I want to redo my bathroom — it's really dated and the shower's been leaking for months.",
      thinkMs: 1100,
      reply: {
        reply:
          "Sorry to hear about the leak — let's get it sorted. Roughly how big is the room, and where are you based? A rough budget helps me brief the right pros.",
        brief_update: briefStep1,
      },
      holdMs: 3200,
    },
    {
      caption: 'Leo structures it into a real brief as they talk.',
      user: "It's about 7 square meters, in Marbella. The tiles are cracked and I'd love a proper walk-in shower.",
      thinkMs: 1300,
      reply: {
        reply:
          "Got it — a walk-in shower conversion in a ~7 m² bathroom in Marbella. What's your budget, and how soon would you want it done?",
        brief_update: briefStep2,
        tool_activity: [{ tool: 'draft_brief', label: 'Structuring the brief' }],
      },
      holdMs: 3600,
    },
    {
      caption: 'The brief is solid — ready to send to vetted pros.',
      user: "Budget's around 8,000 euros, and ideally done within the month.",
      thinkMs: 1300,
      reply: {
        reply:
          "Perfect. Your brief is ready: a ~7 m² walk-in shower conversion in Marbella, ~€8,000, within the month. I'll match it to vetted local pros — tap Post job and you'll start getting structured quotes.",
        brief_update: briefSolid,
        tool_activity: [{ tool: 'match_pros', label: 'Matching vetted pros nearby' }],
      },
      holdMs: 5000,
    },
  ],
};
