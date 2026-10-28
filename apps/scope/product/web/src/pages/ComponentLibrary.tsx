import { useState } from 'react';
import { LeoLogo } from '../components/LeoLogo';
import { Button, Input, Textarea, Sheet, Badge, Surface, ComposerActionStrip, GlassFrame, GlassPill, VoiceNoteBubble, MapAreaCard, MilestoneList, ApplePayButton, GooglePayButton, LeoBubble, UserBubble, ChangeOrderCanvas, BriefCanvas, ProfileCanvas, QuoteCanvas, PlatformLogo, MaterialsCard, AppleWalletButton, GoogleWalletButton } from '@scope/ui';
import type { BriefUpdate, ProfileUpdate, DrawerState, QuoteUpdate, ChangeOrderUpdate, InboxResponse } from '../lib/api';
import type { PreviewState, ChatUiStatus } from '../hooks/useChat';
import type { Message } from '../types';
import PreviewPanel from '../components/chat/PreviewPanel';
import ActionBar from '../components/chat/ActionBar';
import ChatShell from '../components/chat/ChatShell';
import { Star, ChevronDown } from 'lucide-react';

const SAMPLE_BRIEF: BriefUpdate = {
  title: 'Upstairs Bathroom Replumb',
  description:
    'Upstairs bathroom needs replumbing. Hot water barely reaches the taps. House built in 1985 with original copper pipework, never replaced. Combi boiler is a Vaillant ecoTEC in the kitchen downstairs. Bathroom includes basin, shower, and toilet. Detached villa.',
  location: 'El Rosario, Marbella',
  urgency: 'Next 2–3 weeks',
  materials_mentioned: 'Copper to PEX conversion',
  measurements: '2.4 m × 3.1 m',
  budget_indication: '€2,500 – €4,000',
  status: 'solid',
};

const SAMPLE_PROFILE: ProfileUpdate = {
  business_name: 'Reformas Costa del Sol',
  trade: 'General Contractor — Renovations',
  location: 'Estepona, Málaga',
  service_area_km: '40',
  services:
    'Full bathroom & kitchen renovations\nTiling & waterproofing\nPlumbing first & second fix\nElectrical upgrades',
  bio: 'Family-run renovation company since 2012. We specialise in coastal property renovations for both Spanish and international clients. Our team of 8 covers everything from demolition to final finishes — no subcontracting on core trades.',
  years_experience: '14',
  languages: 'Spanish, English',
  certifications: 'Licencia de Actividad · Seguro de Responsabilidad Civil · NIF: B12345678',
  avatar_url: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=176&h=176&fit=crop&crop=face',
  website: 'https://reformascostadelsol.es',
  portfolio_images: [
    'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=200&h=200&fit=crop',
    'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=200&h=200&fit=crop',
    'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=200&h=200&fit=crop',
    'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=200&h=200&fit=crop',
    'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=200&h=200&fit=crop',
  ],
  verified: true,
  review_summary: 'Clients consistently praise the quality of tiling and attention to detail. Minor delays mentioned in 2 of 47 reviews, both resolved quickly. Strong English communication noted by international clients.',
  sources: [
    {
      platform: 'Houzz',
      platform_url: 'houzz.es/pro/reformas-costa-del-sol',
      rating: 4.9,
      review_count: 32,
      reviews: [
        { author: 'María García', rating: 5, date: 'Feb 2026', text: 'Excellent work on our bathroom. Clean, on time, and the tiling is flawless. Would hire again without hesitation.' },
        { author: 'John Stevens', rating: 5, date: 'Jan 2026', text: 'Complete kitchen renovation. Carlos and his team were professional throughout. Great communication in English too.' },
        { author: 'David Palmer', rating: 5, date: 'Nov 2025', text: 'Renovated our holiday apartment in Estepona. They handled everything while we were in the UK. Photos at every stage. Couldn\'t be happier.' },
        { author: 'Ana Rodríguez', rating: 4, date: 'Oct 2025', text: 'Good quality work. Slightly over the original timeline but they kept us informed. Final result is beautiful.' },
        { author: 'Carmen López', rating: 5, date: 'Sep 2025', text: 'Reformaron toda la planta baja de nuestra casa. El equipo fue muy profesional y limpio. Recomendado.' },
      ],
      projects: [
        {
          title: 'Penthouse bathroom — San Pedro',
          description: 'Full strip-out and rebuild of a 12m² master bathroom. Walk-in rain shower with frameless glass enclosure, wall-hung vanity unit with Corian worktop, underfloor heating on separate thermostat. All pipework re-run in PEX. Porcelanosa large-format tiles throughout.',
          images: [
            'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=600&h=400&fit=crop',
            'https://images.unsplash.com/photo-1584622650111-993a426fbf0a?w=600&h=400&fit=crop',
            'https://images.unsplash.com/photo-1600566753190-17f0baa2a6c3?w=600&h=400&fit=crop',
          ],
          source: 'Houzz',
          url: 'https://houzz.es/projects/penthouse-bathroom',
        },
        {
          title: 'Open-plan kitchen — Marbella',
          description: 'Knocked through load-bearing wall (RSJ steel beam), new Porcelanosa Xtone worktops, fully integrated Siemens appliances, herringbone engineered oak floor, bespoke island with waterfall edge.',
          images: [
            'https://images.unsplash.com/photo-1600607687939-ce8a6c25118c?w=600&h=400&fit=crop',
            'https://images.unsplash.com/photo-1600585154340-be6161a56a0c?w=600&h=400&fit=crop',
          ],
          source: 'Houzz',
          url: 'https://houzz.es/projects/open-plan-kitchen',
        },
      ],
    },
    {
      platform: 'Habitissimo',
      platform_url: 'habitissimo.es/pro/reformas-costa-del-sol',
      rating: 4.6,
      review_count: 15,
      reviews: [
        { author: 'Pedro Martín', rating: 5, date: 'Mar 2026', text: 'Reforma integral del baño. Muy contentos con el resultado. Precio justo y cumplieron con los plazos.' },
        { author: 'Laura Sánchez', rating: 4, date: 'Jan 2026', text: 'Buen trabajo en la cocina. Tardaron un poco más de lo previsto pero el acabado es impecable.' },
        { author: 'Miguel Fernández', rating: 5, date: 'Dec 2025', text: 'Hicieron la terraza y el baño de invitados. Muy profesionales y limpios. Repetiría sin duda.' },
      ],
      projects: [
        {
          title: 'Reforma integral baño — Estepona',
          description: 'Reforma completa de baño de 8m². Plato de ducha extraplano, mampara fija, mueble suspendido doble. Azulejos rectificados 60×120.',
          images: [
            'https://images.unsplash.com/photo-1552321554-5fefe8c9ef14?w=600&h=400&fit=crop',
          ],
          source: 'Habitissimo',
        },
      ],
    },
  ],
  leo_jobs_completed: 3,
  leo_rating: 4.9,
};

const SAMPLE_SCOPE: QuoteUpdate = {
  title: 'Hot Water Cylinder Replacement',
  description:
    'Remove existing hot water cylinder and replace with Megaflo Eco 170i unvented cylinder. Includes disconnection, drain-down, removal and disposal of old unit, installation with all required safety valves, connection to existing feeds, commissioning and testing.',
  contractor_name: 'James Mitchell Plumbing',
  client_name: 'Carlos Ruiz',
  location: 'El Rosario, Marbella',
  line_items: [
    { description: 'Megaflo Eco 170i cylinder', amount: 620 },
    { description: 'Installation labour (1 day)', amount: 280 },
    { description: 'Safety valves + fittings', amount: 85 },
  ],
  service_fee_percent: 5,
  payment_schedule: { upfront_percent: 40, completion_percent: 60 },
  terms: [
    'Work to commence within 7 days',
    'Materials warranty: 2 years',
    'Labour guarantee: 12 months',
  ],
  status: 'sent',
  created_at: '2026-03-21',
};

const SAMPLE_CHANGE_ORDER: ChangeOrderUpdate = {
  title: 'Additional Copper Pipework',
  reason: 'James found corroded pipe behind the wall during installation — needs replacing for safety before continuing.',
  line_items: [
    { description: 'Copper pipe (1.5m)', amount: 52.50 },
    { description: 'Labour (45 min)', amount: 45.00 },
  ],
  photo_urls: ['/app/sample-attachment.png', '/app/sample-attachment.png'],
  market_range_low: 80,
  market_range_high: 130,
  status: 'pending',
  scope_ref: 'HWC-2026',
  contractor_name: 'James Mitchell',
};

const PREVIEW_STATES: PreviewState[] = ['empty', 'building', 'editing', 'ready'];
const UI_STATUSES: ChatUiStatus[] = ['needs-info', 'workable', 'solid'];

const MOCK_MESSAGES: Message[] = [
  {
    id: 'm1',
    role: 'user',
    variant: 'text',
    content: 'I need someone to replumb my upstairs bathroom. The hot water barely reaches the taps.',
    timestamp: Date.now() - 120000,
  },
  {
    id: 'm2',
    role: 'leo',
    variant: 'text',
    content: 'Got it! Could you tell me what kind of pipework is in the house currently? And roughly when was it last updated?',
    timestamp: Date.now() - 90000,
  },
  {
    id: 'm3',
    role: 'user',
    variant: 'text',
    content: 'Original copper from 1985. Never touched.',
    timestamp: Date.now() - 60000,
  },
  {
    id: 'm4',
    role: 'leo',
    variant: 'text',
    content: 'That helps a lot. What size is the bathroom roughly, and do you have a budget range in mind?',
    timestamp: Date.now() - 30000,
  },
];

const DRAWER_HIGHLIGHT: DrawerState = {
  content_type: 'brief',
  accent: 'highlight',
  status_text: 'Your brief is ready to post',
  action_label: 'Post job now',
  action_id: 'confirm_brief',
};

const MOCK_RESPONSES: InboxResponse[] = [
  {
    id: '1',
    contractor_name: 'Carlos Fontanería',
    contractor_phone: '34612345678',
    source: 'houzz',
    reaction: 'Need to check the combi pressure and the pipe runs before quoting the full reroute.',
    availability: 'This week',
    profile: SAMPLE_PROFILE,
    ai_rank: 1,
    ai_commentary: 'Experienced plumber with strong reviews for similar replumbing jobs in the Marbella area.',
    onboarding_complete: true,
    created_at: '2026-03-27',
  },
  {
    id: '2',
    contractor_name: 'Instalaciones Ruiz',
    contractor_phone: '34698765432',
    source: 'direct',
    reaction: 'I can come look at it tomorrow. Vaillant certified.',
    profile: {} as ProfileUpdate,
    ai_rank: 2,
    onboarding_complete: false,
    created_at: '2026-03-27',
  },
];

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="mb-12">
      <h2 className="font-display text-lg font-semibold text-ink mb-1">{title}</h2>
      <div className="h-px bg-border mb-4" />
      {children}
    </div>
  );
}

function Card({ label, children, width }: { label: string; children: React.ReactNode; width?: string }) {
  return (
    <div className="inline-flex flex-col" style={{ width: width || '340px' }}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5">{label}</span>
      <div className="rounded-sm overflow-hidden border border-border bg-cream">
        {children}
      </div>
    </div>
  );
}

function PhoneFrame({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="inline-flex flex-col" style={{ width: '375px' }}>
      <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5">{label}</span>
      <div className="rounded-sm overflow-hidden border-2 border-ink" style={{ height: '640px' }}>
        {children}
      </div>
    </div>
  );
}

function MiniResponseCard({ r, rank }: { r: InboxResponse; rank: number }) {
  const isTop = r.ai_rank === 1;
  return (
    <div className={`rounded-sm overflow-hidden bg-cream border ${isTop ? 'border-teal/30' : 'border-border'}`}>
      <div className="px-3 pt-3 pb-2 flex items-start justify-between">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${isTop ? 'bg-teal/15 text-teal' : 'bg-cream-dark text-stone'}`}>
            {r.ai_rank ?? rank}
          </div>
          <div className="min-w-0">
            <h3 className="font-display text-xs font-semibold text-ink truncate">{r.contractor_name}</h3>
            <span className="text-[9px] text-muted">via {r.source}</span>
          </div>
        </div>
        {isTop ? <Star className="w-3.5 h-3.5 shrink-0 text-amber fill-amber" /> : null}
      </div>
      {r.reaction ? (
        <div className="px-3 pb-2">
          <p className="text-[10px] text-stone line-clamp-1">"{r.reaction}"</p>
        </div>
      ) : null}
      <div className="px-3 pb-2.5 flex gap-1.5">
        <div className="flex-1 py-1.5 rounded-md text-[10px] font-semibold text-center bg-cream-dark text-stone">
          View profile
        </div>
        <div className="flex-1 py-1.5 rounded-md text-[10px] font-semibold text-center text-white bg-wa-green">
          WhatsApp
        </div>
      </div>
    </div>
  );
}

const BUTTON_VARIANTS = ['primary', 'secondary', 'terracotta', 'ghost', 'danger'] as const;
const BUTTON_SIZES = ['sm', 'md', 'lg', 'icon'] as const;
const BADGE_COLORS = ['terracotta', 'teal', 'ink', 'amber', 'green', 'red', 'muted'] as const;

export default function ComponentLibrary() {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [inboxBriefOpen, setInboxBriefOpen] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <div className="min-h-dvh bg-cream px-4 py-6 sm:px-8" style={{ maxWidth: '1400px', margin: '0 auto' }}>
      <header className="mb-8">
        <h1 className="font-display text-2xl font-bold text-ink mb-1">Leo Component Library</h1>
        <p className="text-sm text-muted">
          The visual reference for every shared React component. Open this before building anything new.
        </p>
      </header>

      {/* ══════════════════════════════════════════════════════════════════
          PRIMITIVES — mandatory building blocks, never bypass with raw HTML
          ══════════════════════════════════════════════════════════════════ */}

      {/* ── Button ──────────────────────────────────────── */}
      <Section title="Primitives — Button">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">Button</code> from <code className="text-[11px]">@scope/ui</code>.
          Every clickable action in the app composes from this. Never use raw <code className="text-[11px]">&lt;button&gt;</code>.
        </p>
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-2 items-end">
            {BUTTON_VARIANTS.map((v) => (
              <Button key={v} variant={v}>{v}</Button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2 items-end">
            {BUTTON_SIZES.map((s) => (
              <Button key={s} size={s} variant="primary">{s === 'icon' ? '✕' : s}</Button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2 items-end">
            <Button fullWidth>Full width primary</Button>
          </div>
          <div className="flex flex-wrap gap-2 items-end">
            <Button loading>Loading</Button>
            <Button disabled>Disabled</Button>
            <Button variant="terracotta" loading>Loading terra</Button>
            <Button variant="secondary" disabled>Disabled secondary</Button>
          </div>
        </div>
      </Section>

      {/* ── Input + Textarea ────────────────────────────── */}
      <Section title="Primitives — Input + Textarea">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">Input</code> and <code className="text-[11px]">Textarea</code> from <code className="text-[11px]">@scope/ui</code>.
          Every form field composes from these. Never use raw <code className="text-[11px]">&lt;input&gt;</code> or <code className="text-[11px]">&lt;textarea&gt;</code>.
        </p>
        <div className="flex flex-wrap gap-4" style={{ maxWidth: 600 }}>
          <div className="flex-1 min-w-[250px] flex flex-col gap-3">
            <Input label="Email" placeholder="you@example.com" type="email" />
            <Input label="With error" placeholder="Enter amount" error="Amount must be positive" />
            <Input placeholder="No label, just placeholder" />
          </div>
          <div className="flex-1 min-w-[250px] flex flex-col gap-3">
            <Textarea label="Description" placeholder="Describe the work needed..." />
            <Textarea label="With error" placeholder="Notes" error="Required field" />
          </div>
        </div>
      </Section>

      {/* ── Badge ───────────────────────────────────────── */}
      <Section title="Primitives — Badge">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">Badge</code> from <code className="text-[11px]">@scope/ui</code>.
          Status indicators, pills, and tags.
        </p>
        <div className="flex flex-col gap-3">
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5 block">pill (default)</span>
            <div className="flex flex-wrap gap-1.5">
              {BADGE_COLORS.map((c) => <Badge key={c} color={c}>{c}</Badge>)}
            </div>
          </div>
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5 block">status (with dot)</span>
            <div className="flex flex-wrap gap-1.5">
              {BADGE_COLORS.map((c) => <Badge key={c} variant="status" color={c}>{c}</Badge>)}
            </div>
          </div>
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5 block">outline</span>
            <div className="flex flex-wrap gap-1.5">
              {BADGE_COLORS.map((c) => <Badge key={c} variant="outline" color={c}>{c}</Badge>)}
            </div>
          </div>
        </div>
      </Section>

      {/* ── Surface ─────────────────────────────────────── */}
      <Section title="Primitives — Surface">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">Surface</code> from <code className="text-[11px]">@scope/ui</code>.
          Card/container wrapper. Replaces inline <code className="text-[11px]">bg-white border border-border rounded-sm</code> patterns.
        </p>
        <div className="flex flex-wrap gap-4">
          <div className="w-[200px]">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5 block">flat</span>
            <Surface variant="flat"><p className="text-sm text-stone">Flat surface</p></Surface>
          </div>
          <div className="w-[200px]">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5 block">lifted</span>
            <Surface variant="lifted"><p className="text-sm text-stone">Lifted surface</p></Surface>
          </div>
          <div className="w-[200px]">
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1.5 block">raised</span>
            <Surface variant="raised"><p className="text-sm text-stone">Raised surface</p></Surface>
          </div>
        </div>
      </Section>

      {/* ── Sheet ───────────────────────────────────────── */}
      <Section title="Primitives — Sheet">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">Sheet</code> from <code className="text-[11px]">@scope/ui</code>.
          Bottom sheet (Vaul Drawer). Replaces all inline <code className="text-[11px]">Drawer.Root</code> patterns.
        </p>
        <Button variant="secondary" onClick={() => setSheetOpen(true)}>Open Sheet demo</Button>
        <Sheet open={sheetOpen} onClose={() => setSheetOpen(false)} title="Example Sheet" footer={<Button fullWidth onClick={() => setSheetOpen(false)}>Close</Button>}>
          <div className="p-5 space-y-3">
            <Input label="Name" placeholder="Your name" />
            <Textarea label="Notes" placeholder="Any additional notes..." />
          </div>
        </Sheet>
      </Section>

      {/* ── Composition example ─────────────────────────── */}
      <Section title="Primitives — Composition Example">
        <p className="text-xs text-muted mb-3">
          Combining Surface + Badge + Button to show how primitives compose into real UI without any raw HTML elements.
        </p>
        <Surface variant="lifted" className="max-w-sm">
          <div className="flex items-start justify-between mb-3">
            <div>
              <h3 className="text-sm font-semibold text-ink">Hot Water Cylinder</h3>
              <p className="text-xs text-muted">El Rosario, Marbella</p>
            </div>
            <Badge variant="status" color="green">Ready</Badge>
          </div>
          <p className="text-xs text-stone mb-4">Remove and replace existing cylinder with Megaflo Eco 170i.</p>
          <div className="flex gap-2">
            <Button variant="secondary" size="sm" className="flex-1">View details</Button>
            <Button variant="primary" size="sm" className="flex-1">Send scope</Button>
          </div>
        </Surface>
      </Section>

      {/* ── Canvas Templates (populated) ─────────────── */}
      <Section title="Canvas Templates">
        <div className="flex flex-wrap gap-4">
          <Card label="BriefCanvas">
            <BriefCanvas b={SAMPLE_BRIEF} />
          </Card>
          <Card label="ProfileCanvas">
            <ProfileCanvas p={SAMPLE_PROFILE} />
          </Card>
          <Card label="QuoteCanvas">
            <QuoteCanvas scope={SAMPLE_SCOPE} />
          </Card>
        </div>
      </Section>

      {/* ── Canvas Templates — Empty State (vellum + placeholder) */}
      <Section title="Canvas Templates — Empty State (vellum + placeholder behind)">
        <p className="text-xs text-muted mb-3">
          Each shows sample data ghosted behind the vellum overlay — matching how PreviewPanel renders the empty state in the actual chat.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Brief — empty">
            <div style={{ height: '320px' }}>
              <PreviewPanel
                previewState="empty"
                inline
                placeholderContent={<BriefCanvas b={SAMPLE_BRIEF} />}
                emptyLabel="Your brief will appear here"
              >
                <BriefCanvas b={null} />
              </PreviewPanel>
            </div>
          </Card>
          <Card label="Profile — empty">
            <div style={{ height: '320px' }}>
              <PreviewPanel
                previewState="empty"
                inline
                placeholderContent={<ProfileCanvas p={SAMPLE_PROFILE} />}
                emptyLabel="Your profile will appear here"
              >
                <ProfileCanvas p={null} />
              </PreviewPanel>
            </div>
          </Card>
          <Card label="Scope — empty">
            <div style={{ height: '320px' }}>
              <PreviewPanel
                previewState="empty"
                inline
                placeholderContent={<QuoteCanvas scope={SAMPLE_SCOPE} />}
                emptyLabel="Your scope will appear here"
              >
                <QuoteCanvas scope={null} />
              </PreviewPanel>
            </div>
          </Card>
        </div>
      </Section>

      {/* ── PreviewPanel States ───────────────────────── */}
      <Section title="PreviewPanel States">
        <p className="text-xs text-muted mb-3">
          All four vellum states shown inline. Empty has placeholder behind, building has shimmer text, editing has pulse, ready shows clean content.
        </p>
        <div className="flex flex-wrap gap-4">
          {PREVIEW_STATES.map((state) => (
            <Card key={state} label={`PreviewPanel — ${state}`}>
              <div style={{ height: '360px' }}>
                <PreviewPanel
                  previewState={state}
                  inline
                  placeholderContent={<BriefCanvas b={SAMPLE_BRIEF} />}
                  emptyLabel="Check back here as your brief builds up"
                >
                  <BriefCanvas b={SAMPLE_BRIEF} />
                </PreviewPanel>
              </div>
            </Card>
          ))}
        </div>
      </Section>

      {/* ── ComposerActionStrip (shared chrome, ActionBar + Leo Sales) ── */}
      <Section title="ComposerActionStrip">
        <p className="text-xs text-muted mb-3 max-w-xl">
          Presentational rail <strong>above the composer</strong>. Scope{' '}
          <code className="text-[11px]">ActionBar</code> wraps this; Leo Sales (Electron) mirrors the same pixels in{' '}
          <code className="text-[11px]">apps/leo-internal-sales/product/app/renderer/composer-action-strip.css</code>.
        </p>
        <div className="flex flex-col gap-3 bg-cream p-4 rounded-sm border border-border" style={{ maxWidth: 440 }}>
          <ComposerActionStrip elevated>
            <span className="flex-1 text-sm text-stone min-w-0 truncate">Default strip (elevated shadow)</span>
            <button
              type="button"
              className="shrink-0 px-2 py-1.5 text-xs font-semibold rounded-sm bg-border/60 text-ink"
            >
              Button
            </button>
          </ComposerActionStrip>
          <ComposerActionStrip highlight>
            <span className="flex-1 text-sm font-semibold text-terracotta min-w-0 truncate">
              Highlight state (drawer emphasis)
            </span>
            <button
              type="button"
              className="shrink-0 px-2 py-1.5 text-xs font-semibold rounded-sm bg-terracotta text-white"
            >
              Act
            </button>
          </ComposerActionStrip>
        </div>
      </Section>

      {/* ── ActionBar States ──────────────────────────── */}
      <Section title="ActionBar States">
        <div className="flex flex-col gap-3" style={{ maxWidth: '400px' }}>
          {UI_STATUSES.map((status) => (
            <div key={status}>
              <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1 block">
                {status}
              </span>
              <ActionBar
                status={status}
                previewOpen={previewOpen}
                onTogglePreview={() => setPreviewOpen((o) => !o)}
                previewLabelOpen="Close preview"
                previewLabelClosed="Preview brief"
                confirmLabel="Post job"
                onConfirm={() => {}}
                confirmDisabled={status === 'needs-info'}
              />
            </div>
          ))}
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1 block">
              with drawer highlight
            </span>
            <ActionBar
              status="solid"
              previewOpen={false}
              onTogglePreview={() => {}}
              previewLabelOpen="Close preview"
              previewLabelClosed="Preview brief"
              confirmLabel="Post job"
              onConfirm={() => {}}
              confirmDisabled={false}
              drawerState={DRAWER_HIGHLIGHT}
              onDrawerAction={() => {}}
            />
          </div>
          <div>
            <span className="text-[10px] font-semibold uppercase tracking-wide text-muted mb-1 block">
              confirmed
            </span>
            <ActionBar
              status="solid"
              previewOpen={false}
              onTogglePreview={() => {}}
              previewLabelOpen="Close preview"
              previewLabelClosed="Preview brief"
              confirmLabel="Post job"
              onConfirm={() => {}}
              confirmDisabled={false}
              confirmed
            />
          </div>
        </div>
      </Section>

      {/* ── Rendering Contexts ────────────────────────── */}
      <Section title="Rendering Contexts — same canvas, different shell">
        <p className="text-xs text-muted mb-4">
          Each uses the <strong>real</strong> ChatShell / PreviewPanel / ChatInput / ActionBar components in contained mode. Same canvas, different surrounding page.
        </p>
        <div className="flex flex-wrap gap-6">

          {/* Context 1: ChatShell — building state (preview open, mid-conversation) */}
          <PhoneFrame label="ChatShell — building state">
            <ChatShell
              contained
              title="Post a job"
              messages={MOCK_MESSAGES.slice(0, 3)}
              isThinking={false}
              status="workable"
              previewState="building"
              previewContent={<BriefCanvas b={SAMPLE_BRIEF} />}
              placeholderContent={<BriefCanvas b={SAMPLE_BRIEF} />}
              emptyPreviewLabel="Check back here as your brief builds up"
              onSendText={() => {}}
              onSendVoice={() => {}}
              onConfirm={() => {}}
              confirmLabel="Post job"
              previewLabelClosed="Preview brief"
              previewLabelOpen="Close preview"
            />
          </PhoneFrame>

          {/* Context 2: ChatShell — ready state (brief complete) */}
          <PhoneFrame label="ChatShell — ready state">
            <ChatShell
              contained
              title="Post a job"
              messages={MOCK_MESSAGES}
              isThinking={false}
              status="solid"
              previewState="ready"
              previewContent={<BriefCanvas b={SAMPLE_BRIEF} />}
              placeholderContent={<BriefCanvas b={SAMPLE_BRIEF} />}
              onSendText={() => {}}
              onSendVoice={() => {}}
              onConfirm={() => {}}
              confirmLabel="Post job"
              previewLabelClosed="Preview brief"
              previewLabelOpen="Close preview"
            />
          </PhoneFrame>

          {/* Context 3: ChatShell — profile onboarding (tradesperson) */}
          <PhoneFrame label="ChatShell — profile onboarding">
            <ChatShell
              contained
              title="Create profile"
              messages={[
                { id: 'p1', role: 'leo', variant: 'text', content: 'Welcome! Let\'s set up your business profile. What\'s your company name?', timestamp: Date.now() - 60000 },
                { id: 'p2', role: 'user', variant: 'text', content: 'Reformas Costa del Sol', timestamp: Date.now() - 30000 },
                { id: 'p3', role: 'leo', variant: 'text', content: 'Great name. What type of work do you specialise in?', timestamp: Date.now() },
              ]}
              isThinking={false}
              status="workable"
              previewState="editing"
              previewContent={<ProfileCanvas p={SAMPLE_PROFILE} />}
              placeholderContent={<ProfileCanvas p={SAMPLE_PROFILE} />}
              onSendText={() => {}}
              onSendVoice={() => {}}
              onConfirm={() => {}}
              confirmLabel="Save profile"
              previewLabelClosed="Preview profile"
              previewLabelOpen="Close preview"
            />
          </PhoneFrame>

          {/* Context 3b: ChatShell — scope creation (tradesperson) */}
          <PhoneFrame label="ChatShell — scope creation">
            <ChatShell
              contained
              title="Create scope"
              messages={[
                { id: 's1', role: 'leo', variant: 'text', content: 'I have the brief for the hot water cylinder replacement in El Rosario. Ready to build the scope — what\'s the first item?', timestamp: Date.now() - 90000 },
                { id: 's2', role: 'user', variant: 'text', content: 'Megaflo Eco 170i cylinder, €620. Installation labour one day, €280. Safety valves and fittings, about €85.', timestamp: Date.now() - 60000 },
                { id: 's3', role: 'leo', variant: 'text', content: 'Added all three. Total so far: €985 + 5% Leo fee = €1,034. Anything else?', timestamp: Date.now() - 30000 },
              ]}
              isThinking={false}
              status="solid"
              previewState="ready"
              previewContent={<QuoteCanvas scope={SAMPLE_SCOPE} />}
              placeholderContent={<QuoteCanvas scope={SAMPLE_SCOPE} />}
              onSendText={() => {}}
              onSendVoice={() => {}}
              onConfirm={() => {}}
              confirmLabel="Send scope"
              previewLabelClosed="Preview scope"
              previewLabelOpen="Close scope"
            />
          </PhoneFrame>

          {/* Context 4: Job Inbox with brief overlay */}
          <PhoneFrame label="Job Inbox — brief overlay">
            <div className="flex flex-col h-full bg-cream relative overflow-hidden">
              <header className="shrink-0 flex items-center justify-between px-4 h-12 z-10 bg-ink">
                <h1 className="font-display text-[14px] font-semibold text-white">Job inbox</h1>
                <button
                  onClick={() => setInboxBriefOpen((o) => !o)}
                  className="text-[10px] font-medium px-2.5 py-1 rounded-md bg-white/10 text-cream"
                >
                  {inboxBriefOpen ? 'Close brief' : 'View brief'}
                </button>
              </header>
              <div className="shrink-0 px-3 py-2 flex items-center justify-between bg-cream border-b border-border">
                <div>
                  <h2 className="font-display text-xs font-semibold text-ink">{SAMPLE_BRIEF.title}</h2>
                  <p className="text-[10px] text-muted">2 responses · 5 contacted</p>
                </div>
                <span className="text-[9px] font-semibold uppercase px-1.5 py-0.5 rounded bg-teal/[.12] text-teal">Ready</span>
              </div>
              <div className="flex-1 overflow-y-auto px-2.5 py-2.5 space-y-2">
                {MOCK_RESPONSES.map((r, i) => (
                  <MiniResponseCard key={r.id} r={r} rank={i + 1} />
                ))}
              </div>
              <div
                className="absolute inset-x-0 bottom-0 z-20 bg-cream transition-transform duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] rounded-t-xl shadow-[0_-4px_20px_rgba(0,0,0,0.12)]"
                style={{
                  top: '48px',
                  transform: inboxBriefOpen ? 'translateY(0)' : 'translateY(100%)',
                  pointerEvents: inboxBriefOpen ? 'auto' : 'none',
                }}
              >
                <div className="flex flex-col h-full">
                  <div className="flex-1 overflow-y-auto">
                    <BriefCanvas b={SAMPLE_BRIEF} />
                  </div>
                  <button
                    onClick={() => setInboxBriefOpen(false)}
                    className="shrink-0 flex items-center justify-center gap-1.5 py-2.5 text-xs font-medium text-stone border-t border-border"
                  >
                    <ChevronDown className="w-3.5 h-3.5" />
                    Close brief
                  </button>
                </div>
              </div>
            </div>
          </PhoneFrame>

          {/* Context 5: Standalone URL */}
          <PhoneFrame label="Standalone URL — /canvas/:token">
            <div className="flex flex-col h-full bg-cream">
              <header className="shrink-0 flex items-center px-4 h-10 bg-ink">
                <LeoLogo variant="cream" height={14} />
              </header>
              <div className="flex-1 overflow-y-auto">
                <div className="mx-2.5 mt-2.5 mb-4 rounded-sm overflow-hidden border border-border">
                  <BriefCanvas b={SAMPLE_BRIEF} />
                </div>
              </div>
            </div>
          </PhoneFrame>
        </div>
      </Section>

      {/* ── Brand Effects ─────────────────────────── */}
      <Section title="Brand Effects — Glass Pill + Shimmer">
        <p className="text-xs text-muted mb-3">
          CSS from <code className="text-[11px]">brand-effects.css</code> (loaded globally). React wrapper: <code className="text-[11px]">GlassPill</code> from <code className="text-[11px]">@scope/ui</code>.
        </p>
        <div className="flex flex-wrap gap-4 items-start">
          <Card label="GlassPill — with dot (thinking state)" width="280px">
            <div className="p-4 flex justify-center bg-terracotta/[.08]">
              <GlassPill>Updating brief…</GlassPill>
            </div>
          </Card>
          <Card label="GlassPill — no dot (status)" width="280px">
            <div className="p-4 flex justify-center bg-terracotta/[.08]">
              <GlassPill dot={false}>Brief ready</GlassPill>
            </div>
          </Card>
          <Card label="Shimmer label" width="280px">
            <div className="p-4 flex justify-center items-center" style={{ minHeight: '56px' }}>
              <span className="leo-shimmer-label text-sm font-semibold">Leo is thinking…</span>
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Glass Frame (shared component) ──────────── */}
      <Section title="Glass Frame">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">GlassFrame</code> from <code className="text-[11px]">@scope/ui</code>.
          Style from <code className="text-[11px]">leo-glass-frame.css</code> (loaded globally).
          Dots are always terra / amber / teal — baked into the CSS.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Light variant" width="380px">
            <div className="p-3">
              <GlassFrame url="leo.casa/brief/bath-replumb">
                <div className="p-4 text-[13px] text-stone">Content goes here</div>
              </GlassFrame>
            </div>
          </Card>
          <Card label="Dark variant" width="380px">
            <div className="p-3 bg-ink rounded-md">
              <GlassFrame dark url="leo.casa/scope/hwc-2026">
                <div className="p-4 text-[13px] text-muted">Content goes here</div>
              </GlassFrame>
            </div>
          </Card>
          <Card label="Dark — wrapping BriefCanvas" width="380px">
            <div className="p-3 bg-ink rounded-md">
              <GlassFrame dark url="leo.casa/brief/LCS-4821">
                <BriefCanvas b={SAMPLE_BRIEF} />
              </GlassFrame>
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Pay Buttons ───────────────────────────────── */}
      <Section title="Pay Buttons — Apple Pay + Google Pay">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">ApplePayButton</code> and <code className="text-[11px]">GooglePayButton</code> from <code className="text-[11px]">@scope/ui</code>.
          Branding rules: logo + "Pay" only — no "Apple" or "Google" text.
          Apple "Pay" uses SF Pro (-apple-system). Google "Pay" uses Google Sans.
          Static HTML: <code className="text-[11px]">.leo-pay-pill</code> / <code className="text-[11px]">.leo-pay-btn</code> from <code className="text-[11px]">brand-effects.css</code>.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Pill variant (inline lists)" width="280px">
            <div className="p-4 flex items-center gap-2 bg-ink rounded-md">
              <ApplePayButton variant="pill" />
              <GooglePayButton variant="pill" />
            </div>
          </Card>
          <Card label="Button variant (payment flows)" width="320px">
            <div className="p-4 flex flex-col gap-2 bg-ink rounded-md">
              <div className="grid grid-cols-2 gap-2.5">
                <ApplePayButton variant="button" />
                <GooglePayButton variant="button" />
              </div>
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Apple Wallet & Google Wallet Buttons ─────────────────────────── */}
      <Section title="Apple Wallet & Google Wallet Buttons">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">AppleWalletButton</code> and <code className="text-[11px]">GoogleWalletButton</code> from <code className="text-[11px]">@scope/ui</code>.
          Official brand-compliant wallet buttons following Apple and Google design guidelines.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Apple Wallet Button" width="140px">
            <div className="p-4">
              <AppleWalletButton />
            </div>
          </Card>
          
          <Card label="Google Wallet Button" width="140px">
            <div className="p-4">
              <GoogleWalletButton />
            </div>
          </Card>

          <Card label="Wallet Buttons Side by Side" width="320px">
            <div className="p-4">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                <AppleWalletButton />
                <GoogleWalletButton />
              </div>
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Materials Card ─────────────────────────── */}
      <Section title="Materials Card — Leo Debit Card">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">MaterialsCard</code> from <code className="text-[11px]">@scope/ui</code>.
          Credit card visual with Leo branding, contactless symbol, chip, and masked card number.
          Used for materials purchases that only work at construction suppliers.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Full card with Apple/Google Pay + split" width="420px">
            <div className="p-4">
              <MaterialsCard />
            </div>
          </Card>
          
          <Card label="Card only (no pay buttons, no split)" width="420px">
            <div className="p-4">
              <MaterialsCard showSplit={false} showPayButtons={false} />
            </div>
          </Card>

          <Card label="Custom card holder" width="420px">
            <div className="p-4">
              <MaterialsCard cardHolder="C. DÍAZ" cardNumber="•••• •••• •••• 1234" />
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Platform Logos ──────────────────────────────── */}
      <Section title="Platform Logos">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">PlatformLogo</code> from <code className="text-[11px]">@scope/ui</code>. Supports all major platforms with consistent sizing and variants.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Inline Variants">
            <div className="flex items-center gap-4">
              <PlatformLogo platform="habitissimo" size="sm" />
              <PlatformLogo platform="houzz" size="md" />
              <PlatformLogo platform="cronoshare" size="lg" />
              <PlatformLogo platform="hogami" size="md" />
            </div>
          </Card>
          <Card label="Card Variants (Reviews)">
            <div className="flex flex-col gap-3">
              <div className="flex items-center gap-3">
                <PlatformLogo platform="cronoshare" size="md" variant="card" />
                <div>
                  <div className="text-xs font-semibold text-ink">CronoShare</div>
                  <div className="text-[10px] text-stone">9.5★ · 16 reviews</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <PlatformLogo platform="habitissimo" size="md" variant="card" />
                <div>
                  <div className="text-xs font-semibold text-ink">Habitissimo</div>
                  <div className="text-[10px] text-stone">4.8★ · 23 reviews</div>
                </div>
              </div>
              <div className="flex items-center gap-3">
                <PlatformLogo platform="houzz" size="md" variant="card" />
                <div>
                  <div className="text-xs font-semibold text-ink">Houzz</div>
                  <div className="text-[10px] text-stone">4.9★ · 32 reviews</div>
                </div>
              </div>
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Chat Bubbles ──────────────────────────────── */}
      <Section title="Chat Bubbles — User + Leo">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">UserBubble</code> and <code className="text-[11px]">LeoBubble</code> from <code className="text-[11px]">@scope/ui</code>.
          CSS from <code className="text-[11px]">brand-effects.css</code>: <code className="text-[11px]">.leo-chat-user</code> / <code className="text-[11px]">.leo-chat-leo</code>.
          <code className="text-[11px]">variant="dark"</code> for landing pages on dark backgrounds.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="App variant (light bg)" width="400px">
            <div className="p-4 flex flex-col gap-3 bg-cream rounded-md">
              <UserBubble text="I need someone to replumb my upstairs bathroom. The hot water barely reaches the taps." />
              <LeoBubble text="Got it — **old 1985 copper pipework** and a Vaillant combi downstairs. That's a solid brief. A few questions: is this a full replumb or just the bathroom feed?" />
              <UserBubble text="Just the bathroom feed for now." />
              <LeoBubble text="Perfect. **Brief is ready** — I've noted the Vaillant model and the 1985 build. A local plumber should price this at **€800–€1,200** depending on access." />
            </div>
          </Card>
          <Card label="Landing page variant (dark bg)" width="400px">
            <div className="p-4 flex flex-col gap-3 bg-ink rounded-md">
              <UserBubble variant="dark" text="Hot water barely reaches the upstairs bathroom." />
              <LeoBubble variant="dark" text="That sounds like a pressure or pipework issue. **When was the house built?** Original copper often degrades after 30+ years." />
              <UserBubble variant="dark" text="1985, copper pipework, never been replaced." />
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Change Order Canvas ───────────────────────── */}
      <Section title="Change Order Canvas — Fourth Leo Document">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">ChangeOrderCanvas</code> from <code className="text-[11px]">@scope/ui</code>.
          <code className="text-[11px]">mode="full"</code> for chat preview / standalone page.
          <code className="text-[11px]">mode="compact"</code> for embedding inside a job progress list.
          Static HTML reference: H5 "Know about changes before you're billed" in homeowners.html.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Full card — pending approval" width="420px">
            <div className="p-4">
              <ChangeOrderCanvas co={SAMPLE_CHANGE_ORDER} mode="full" />
            </div>
          </Card>
          <Card label="Full card — approved" width="420px">
            <div className="p-4">
              <ChangeOrderCanvas co={{ ...SAMPLE_CHANGE_ORDER, status: 'approved' }} mode="full" />
            </div>
          </Card>
          <Card label="Compact row (for MilestoneList / progress)" width="380px">
            <div className="p-4 flex flex-col gap-2">
              <ChangeOrderCanvas co={SAMPLE_CHANGE_ORDER} mode="compact" />
              <ChangeOrderCanvas co={{ ...SAMPLE_CHANGE_ORDER, title: 'Extra Tile Adhesive', status: 'approved' }} mode="compact" />
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Voice Note Bubble ────────────────────────── */}
      <Section title="Voice Note Bubble">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">VoiceNoteBubble</code> from <code className="text-[11px]">@scope/ui</code>.
          Terra terracotta bubble — canonical across app and static landing pages.
          Static HTML counterpart: <code className="text-[11px]">.lead-modal-user-vn</code> in homeowners.html.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="With waveform + transcript" width="320px">
            <div className="p-4 flex justify-center">
              <VoiceNoteBubble
                durationSec={37}
                waveform={[0.3,0.6,0.8,0.5,0.9,0.4,0.7,0.6,0.85,0.5,0.4,0.7,0.9,0.6,0.3,0.8,0.5,0.7,0.6,0.4]}
                transcript="Upstairs bathroom needs replumbing. Hot water barely reaches the taps. House built in 1985 with original copper pipework, never replaced."
              />
            </div>
          </Card>
          <Card label="Transcribing state (no transcript)" width="320px">
            <div className="p-4 flex justify-center">
              <VoiceNoteBubble durationSec={12} />
            </div>
          </Card>
          <Card label="Short transcript (no expand)" width="320px">
            <div className="p-4 flex justify-center">
              <VoiceNoteBubble durationSec={8} transcript="Paint the living room." />
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Recording State (ChatInput bar while recording) ── */}
      <Section title="Recording State — ChatInput bar">
        <p className="text-xs text-muted mb-3">
          Standard recording UI used in <code className="text-[11px]">ChatInput</code> (React app) and
          replicated in <code className="text-[11px]">heroInlineWave</code> (homeowners landing page).
          Features: pulsing red dot · rAF-driven timer (immune to animation-loop throttling) ·
          waveform bars that fill to the right edge of available space.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Recording — 0:04, mid-speech" width="380px">
            <div className="bg-ink rounded-sm p-3 mx-4 my-3">
              <div className="flex items-center gap-[8px] px-3 h-[44px]">
                <span className="w-[7px] h-[7px] rounded-full bg-red-500 shrink-0 animate-[recDot_1.1s_ease-in-out_infinite]" aria-hidden="true" />
                <span className="text-xs text-white/65 tabular-nums shrink-0">0:04</span>
                <div
                  className="flex-1 flex items-center justify-end gap-[2px] h-[30px] overflow-hidden"
                  style={{
                    maskImage: 'linear-gradient(90deg, rgba(0,0,0,0.15) 0, rgba(0,0,0,0.6) 8px, rgba(0,0,0,1) 20px)',
                    WebkitMaskImage: 'linear-gradient(90deg, rgba(0,0,0,0.15) 0, rgba(0,0,0,0.6) 8px, rgba(0,0,0,1) 20px)',
                  }}
                >
                  {[2,3,6,14,22,18,8,4,2,3,10,20,28,18,6,3,2,4,12,24,26,14,5,2,3,8,16,22,18,10,4,2,6,18,26,20,8,3,2,5].map((h, i) => (
                    <span key={i} className="w-[2.5px] rounded-[1.5px] bg-white/85 shrink-0" style={{ height: `${h}px` }} />
                  ))}
                </div>
              </div>
            </div>
          </Card>
          <Card label="Recording — 0:09, silence (flat)" width="380px">
            <div className="bg-ink rounded-sm p-3 mx-4 my-3">
              <div className="flex items-center gap-[8px] px-3 h-[44px]">
                <span className="w-[7px] h-[7px] rounded-full bg-red-500 shrink-0 animate-[recDot_1.1s_ease-in-out_infinite]" aria-hidden="true" />
                <span className="text-xs text-white/65 tabular-nums shrink-0">0:09</span>
                <div
                  className="flex-1 flex items-center justify-end gap-[2px] h-[30px] overflow-hidden"
                  style={{
                    maskImage: 'linear-gradient(90deg, rgba(0,0,0,0.15) 0, rgba(0,0,0,0.6) 8px, rgba(0,0,0,1) 20px)',
                    WebkitMaskImage: 'linear-gradient(90deg, rgba(0,0,0,0.15) 0, rgba(0,0,0,0.6) 8px, rgba(0,0,0,1) 20px)',
                  }}
                >
                  {Array(40).fill(2).map((h, i) => (
                    <span key={i} className="w-[2.5px] rounded-[1.5px] bg-white/20 shrink-0" style={{ height: `${h}px` }} />
                  ))}
                </div>
              </div>
            </div>
          </Card>
          <Card label="In ChatInput context (light bg)" width="400px">
            <div className="bg-surface border border-border rounded-sm p-2 mx-4 my-3">
              <div className="flex items-center gap-2">
                <div className="flex-1 border border-terracotta/40 rounded-md">
                  <div className="flex items-center gap-[8px] px-3 h-[44px]">
                    <span className="w-[7px] h-[7px] rounded-full bg-red-500 shrink-0 animate-[recDot_1.1s_ease-in-out_infinite]" aria-hidden="true" />
                    <span className="text-xs text-muted tabular-nums shrink-0">0:06</span>
                    <div
                      className="flex-1 flex items-center justify-end gap-[2px] h-[30px] overflow-hidden"
                      style={{
                        maskImage: 'linear-gradient(90deg, rgba(0,0,0,0.2) 0, rgba(0,0,0,0.5) 16px, rgba(0,0,0,1) 40px)',
                        WebkitMaskImage: 'linear-gradient(90deg, rgba(0,0,0,0.2) 0, rgba(0,0,0,0.5) 16px, rgba(0,0,0,1) 40px)',
                      }}
                    >
                      {[2,4,10,18,24,20,10,4,2,5,14,22,26,16,6,2,3,8,18,24,22,12,4,2,5,12,20,24,18,8,3,2,7,16,24,20,10,4,2,6].map((h, i) => (
                        <span key={i} className="w-[2.5px] rounded-[1.5px] bg-terracotta shrink-0" style={{ height: `${h}px` }} />
                      ))}
                    </div>
                  </div>
                </div>
                <button className="w-[44px] h-[44px] rounded-sm bg-black/[0.06] flex items-center justify-center text-stone shrink-0" aria-label="Discard">
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/><path d="M10 11v6M14 11v6"/><path d="M9 6V4h6v2"/></svg>
                </button>
                <button className="w-[44px] h-[44px] rounded-sm bg-terracotta flex items-center justify-center shrink-0" aria-label="Send">
                  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>
                </button>
              </div>
            </div>
          </Card>
        </div>
        <p className="text-xs text-muted mt-3">
          <strong>Static HTML:</strong> <code className="text-[11px]">.hero-inline-wave</code> + <code className="text-[11px]">.hero-rec-dot</code> + <code className="text-[11px]">@keyframes recDotPulse</code> in homeowners.html.
          Timer uses <code className="text-[11px]">requestAnimationFrame</code> (not setInterval) to avoid freezes caused by the fluid gradient animation loop.
          Bar count calculated from container width: <code className="text-[11px]">Math.floor((width + gap) / (barW + gap))</code>.
        </p>
      </Section>

      {/* ── Voice Note Bubble ─────────────────────────── */}
      <Section title="Voice Note Bubble">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">VoiceNoteBubble</code> from <code className="text-[11px]">@scope/ui</code>.
          Terra terracotta bubble — canonical across app and static landing pages.
          Static HTML counterpart: <code className="text-[11px]">.lead-modal-user-vn</code> in homeowners.html.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="With waveform + transcript" width="320px">
            <div className="p-4 flex justify-center">
              <VoiceNoteBubble
                durationSec={37}
                waveform={[0.3,0.6,0.8,0.5,0.9,0.4,0.7,0.6,0.85,0.5,0.4,0.7,0.9,0.6,0.3,0.8,0.5,0.7,0.6,0.4]}
                transcript="Upstairs bathroom needs replumbing. Hot water barely reaches the taps. House built in 1985 with original copper pipework, never replaced."
              />
            </div>
          </Card>
          <Card label="Transcribing state (no transcript)" width="320px">
            <div className="p-4 flex justify-center">
              <VoiceNoteBubble durationSec={12} />
            </div>
          </Card>
          <Card label="Short transcript (no expand)" width="320px">
            <div className="p-4 flex justify-center">
              <VoiceNoteBubble durationSec={8} transcript="Paint the living room." />
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Map Area Card ─────────────────────────────── */}
      <Section title="Map Area Card">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">MapAreaCard</code> from <code className="text-[11px]">@scope/ui</code>.
          Approximate location only — terra ring overlay, area footer, privacy note.
          Static HTML: <code className="text-[11px]">.map-approx-animate</code> + <code className="text-[11px]">.map-directions-animate</code> in homeowners.html.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="Approx ring (homeowner brief)" width="320px">
            <div className="p-4">
              <MapAreaCard
                mapImageSrc="/app/sample-attachment.png"
                areaName="El Rosario, Marbella"
                radiusLabel="~2 km radius · rough area"
                showApproxRing={true}
              />
            </div>
          </Card>
          <Card label="No ring (pro invite — precise)" width="320px">
            <div className="p-4">
              <MapAreaCard
                mapImageSrc="/app/sample-attachment.png"
                areaName="Calle Girasol 14, Marbella"
                radiusLabel="Exact address — invited tradesperson only"
                showApproxRing={false}
                privacyNote=""
              />
            </div>
          </Card>
        </div>
      </Section>

      {/* ── Milestone List (Escrow) ───────────────────── */}
      <Section title="Milestone List — Escrow">
        <p className="text-xs text-muted mb-3">
          <code className="text-[11px]">MilestoneList</code> from <code className="text-[11px]">@scope/ui</code>.
          Same component, two shells: <code className="text-[11px]">gradientBg=true</code> for landing pages, plain white for app.
          Static HTML: H4 "Your money doesn't move" section in homeowners.html + professionals.html.
        </p>
        <div className="flex flex-wrap gap-4">
          <Card label="App variant (plain white)" width="320px">
            <div className="p-4">
              <MilestoneList
                milestones={[
                  { id: '1', label: 'Deposit — work commences', amount: '€295', status: 'done' },
                  { id: '2', label: 'Mid-job milestone', amount: '€395', status: 'done', note: 'Released after install · 18 Mar' },
                  { id: '3', label: 'Final sign-off', amount: '€295', status: 'active', note: '€295 held until you approve' },
                ]}
              />
            </div>
          </Card>
          <Card label="Landing page variant (gradient shell)" width="340px">
            <div className="p-4 bg-ink rounded-md">
              <MilestoneList
                gradientBg
                gradientSrc="/app/sample-attachment.png"
                milestones={[
                  { id: '1', label: 'Deposit — work commences', amount: '€295', status: 'done' },
                  { id: '2', label: 'Mid-job milestone', amount: '€395', status: 'done' },
                  { id: '3', label: 'Final sign-off', amount: '€295', status: 'pending' },
                ]}
              />
            </div>
          </Card>
        </div>
      </Section>

      <footer className="pt-4 pb-8 text-center text-xs text-muted">
        Leo Component Library · Dev only · Not shipped
      </footer>
    </div>
  );
}
