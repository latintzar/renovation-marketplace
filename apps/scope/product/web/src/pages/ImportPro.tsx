/**
 * ImportPro — Profile import progress page.
 *
 * Shown when a tradesperson enters their profile URL on the landing page.
 * Runs the import SSE stream, shows animated progress steps + a live
 * ProfileCanvas preview building up below. When complete, redirects to
 * /canvas/:contractorId so they can review their profile without going
 * through the chat first.
 *
 * If no import URL is found in the handoff, redirects to /onboard/pro
 * so the regular chat flow handles it.
 */

import { useEffect, useRef, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, Loader2, Phone } from 'lucide-react';
import { consumeHandoff } from '../lib/handoff';
import { LeoLogo } from '../components/LeoLogo';
import { LanguageToggle } from '../components/LanguageToggle';
import { FullScreenStep } from '../components/FullScreenStep';
import { importProfile, type ProfileUpdate, apiFetch, API_BASE } from '../lib/api';
import { Button, Input, ProfileCanvas } from '@scope/ui';

interface ProgressStep {
  id: string;
  label: string;
  status: 'waiting' | 'active' | 'done';
}

const INITIAL_STEPS: ProgressStep[] = [
  { id: 'detecting', label: 'Detecting your platform…', status: 'active' },
  { id: 'fetching', label: 'Fetching your profile', status: 'waiting' },
  { id: 'gallery', label: 'Collecting portfolio images', status: 'waiting' },
  { id: 'reviews', label: 'Reading your reviews', status: 'waiting' },
  { id: 'credentials', label: 'Checking credentials & licences', status: 'waiting' },
  { id: 'building', label: 'Building your Leo profile', status: 'waiting' },
];

const STEP_MAP: Record<string, string> = {
  connecting: 'detecting',
  fetching_profile: 'fetching',
  crawling_linked_website: 'gallery',
  crawling_website: 'gallery',
  discovering_profiles: 'gallery',
  checking_credentials: 'credentials',
  verifying_trust: 'credentials',
  structuring_with_ai: 'reviews',
  summarizing_reviews: 'reviews',
  processing: 'building',
  saving_dossier: 'building',
  complete: 'building',
};

/**
 * Adapt raw ProfileResult (from SSE preview) into the ProfileUpdate shape
 * that ProfileCanvas expects. The backend sends `result.model_dump()` for
 * preview events — flat fields like `name`, `reviews[]`, `projects[]` at
 * the top level. ProfileCanvas needs `business_name`, nested `sources[]`
 * with per-platform reviews/projects, etc.
 */
function adaptRawToCanvas(raw: Record<string, unknown>): ProfileUpdate {
  // If it already has `sources` array, it's the canvas format from save_and_recompute
  if (Array.isArray(raw.sources) && raw.sources.length > 0 && raw.sources[0]?.platform) {
    return raw as unknown as ProfileUpdate;
  }

  const services = Array.isArray(raw.services)
    ? (raw.services as string[]).join('\n')
    : String(raw.services ?? '');

  const reviews = Array.isArray(raw.reviews) ? (raw.reviews as Record<string, unknown>[]) : [];
  const projects = Array.isArray(raw.projects) ? (raw.projects as Record<string, unknown>[]) : [];

  const source = {
    platform: String(raw.source ?? 'Unknown'),
    platform_url: String(raw.source_url ?? ''),
    rating: typeof raw.rating === 'number' ? raw.rating : undefined,
    review_count: typeof raw.review_count === 'number' ? raw.review_count : reviews.length,
    reviews: reviews.map((r) => ({
      author: String(r.reviewer_name ?? r.author ?? ''),
      rating: typeof r.rating === 'number' ? r.rating : undefined,
      date: String(r.date ?? ''),
      text: String(r.text ?? ''),
    })),
    projects: projects.map((p) => ({
      title: String(p.title ?? ''),
      description: String(p.description ?? ''),
      images: Array.isArray(p.images) ? p.images as string[] : [],
      url: String(p.url ?? ''),
      source: String(raw.source ?? ''),
    })),
  };

  return {
    business_name: String(raw.name ?? ''),
    trade: String(raw.trade ?? ''),
    location: String(raw.location ?? ''),
    service_area_km: '',
    services,
    bio: String(raw.description ?? raw.raw_about ?? ''),
    years_experience: raw.years_experience != null ? String(raw.years_experience) : '',
    languages: '',
    certifications: Array.isArray(raw.credentials)
      ? (raw.credentials as Record<string, unknown>[]).map((c) => String(c.value ?? '')).filter(Boolean).join('\n')
      : '',
    avatar_url: String(raw.avatar_url ?? ''),
    website: String(raw.website ?? ''),
    portfolio_images: Array.isArray(raw.portfolio_images) ? raw.portfolio_images as string[] : [],
    sources: [source],
    review_summary: String(raw.review_summary ?? ''),
  } as ProfileUpdate;
}

function advanceSteps(steps: ProgressStep[], activeId: string): ProgressStep[] {
  const activeIdx = steps.findIndex((s) => s.id === activeId);
  if (activeIdx === -1) return steps;
  return steps.map((s, i) => {
    if (i < activeIdx) return { ...s, status: 'done' };
    if (i === activeIdx) return { ...s, status: 'active' };
    return { ...s, status: 'waiting' };
  });
}

export default function ImportPro() {
  const navigate = useNavigate();
  const handoff = useMemo(() => consumeHandoff(), []);
  const importUrl = handoff.import || '';
  const [contractorId] = useState(() => `web-${globalThis.crypto?.randomUUID?.() ?? Array.from(crypto.getRandomValues(new Uint8Array(16)), b => b.toString(16).padStart(2, '0')).join('')}`);

  const [steps, setSteps] = useState<ProgressStep[]>(INITIAL_STEPS);
  const [profile, setProfile] = useState<ProfileUpdate | null>(null);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const [phoneDiscrepancy, setPhoneDiscrepancy] = useState<{ habitissimo_phone: string; known_phone: string } | null>(null);
  const [needsPhone, setNeedsPhone] = useState(false);
  const [phoneInput, setPhoneInput] = useState('');
  const [phoneSubmitting, setPhoneSubmitting] = useState(false);
  const ranRef = useRef(false);

  // If no import URL, fall back to regular chat onboarding
  useEffect(() => {
    if (!importUrl) {
      navigate('/onboard/pro', { replace: true });
    }
  }, [importUrl, navigate]);

  useEffect(() => {
    if (!importUrl || ranRef.current) return;
    ranRef.current = true;

    void (async () => {
      try {
        for await (const evt of importProfile(importUrl, contractorId)) {
          if (evt.type === 'progress') {
            const step = (evt as { step?: string }).step;
            if (step) {
              const mappedId = STEP_MAP[step] || null;
              if (mappedId) {
                setSteps((prev) => advanceSteps(prev, mappedId));
              }
            }
          }
          if (evt.type === 'preview') {
            const p = (evt as { profile?: Record<string, unknown> }).profile;
            if (p) setProfile(adaptRawToCanvas(p));
          }
          if (evt.type === 'result') {
            const evtTyped = evt as {
              profile?: Record<string, unknown>;
              canvas?: boolean;
              phone_discrepancy?: { habitissimo_phone: string; known_phone: string };
              needs_phone?: boolean;
            };
            if (evtTyped.profile) {
              setProfile(evtTyped.canvas
                ? (evtTyped.profile as unknown as ProfileUpdate)
                : adaptRawToCanvas(evtTyped.profile));
            }
            if (evtTyped.phone_discrepancy) setPhoneDiscrepancy(evtTyped.phone_discrepancy);
            if (evtTyped.needs_phone) setNeedsPhone(true);
          }
          if (evt.type === 'error') {
            const msg = (evt as { message?: string }).message || 'Import failed';
            setError(msg);
          }
        }
        // Mark all steps done
        setSteps((prev) => prev.map((s) => ({ ...s, status: 'done' })));
        setDone(true);
        // If phone is needed, don't navigate — let the modal handle it.
        // needsPhone state is set from the result event above.
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Import failed');
      }
    })();
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Navigate to canvas — store phone discrepancy context first if present
  function handleNavigateToCanvas() {
    if (phoneDiscrepancy) {
      localStorage.setItem(`phone_discrepancy_${contractorId}`, JSON.stringify(phoneDiscrepancy));
    }
    navigate(`/canvas/${contractorId}`, { replace: true });
  }

  // Auto-navigate when done and no phone collection needed
  useEffect(() => {
    if (done && !needsPhone) {
      const t = setTimeout(handleNavigateToCanvas, 900);
      return () => clearTimeout(t);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [done, needsPhone]);

  async function handlePhoneSubmit(e: React.FormEvent) {
    e.preventDefault();
    const cleaned = phoneInput.trim().replace(/\s/g, '');
    if (!cleaned || cleaned.length < 7) return;
    setPhoneSubmitting(true);
    try {
      await apiFetch(`${API_BASE}/v1/contractor/set-phone`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ contractor_id: contractorId, phone: cleaned }),
      });
    } catch {
      // Non-fatal — social proof just won't run
    }
    setNeedsPhone(false);
    handleNavigateToCanvas();
  }

  if (!importUrl) return null;

  return (
    <div className="flex flex-col min-h-dvh bg-cream">
      {/* Minimal Leo header */}
      <header className="shrink-0 flex items-center justify-between px-4 h-12 bg-ink">
        <LeoLogo variant="cream" height={15} />
        <LanguageToggle variant="dark" />
      </header>

      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto max-w-lg px-4 pt-8 pb-10">

          {/* Heading */}
          <div className="text-center mb-8">
            <h1 className="font-display text-2xl font-semibold text-ink mb-2">
              {done ? (needsPhone ? 'One last thing' : 'Your profile is ready') : 'Building your profile'}
            </h1>
            <p className="text-sm text-stone">
              {done && !needsPhone
                ? 'Taking you to review it now…'
                : !done
                ? 'We\'re scanning your listing and building your Leo profile.'
                : ''}
            </p>
          </div>

          {/* Progress steps */}
          <div className="rounded-sm border border-border bg-card mb-6 overflow-hidden">
            {steps.map((step, i) => (
              <div
                key={step.id}
                className={[
                  'flex items-center gap-3 px-4 py-3',
                  i < steps.length - 1 ? 'border-b border-border' : '',
                  step.status === 'waiting' ? 'opacity-35' : '',
                ].join(' ')}
              >
                <div className="shrink-0 w-5 h-5 flex items-center justify-center">
                  {step.status === 'done' && (
                    <span className="w-5 h-5 rounded-full bg-green/15 flex items-center justify-center">
                      <Check size={11} className="text-green" strokeWidth={2.5} />
                    </span>
                  )}
                  {step.status === 'active' && (
                    <Loader2 size={16} className="text-terracotta animate-spin" />
                  )}
                  {step.status === 'waiting' && (
                    <span className="w-3 h-3 rounded-full border border-border" />
                  )}
                </div>
                <span
                  className={[
                    'text-sm',
                    step.status === 'active' ? 'leo-shimmer-label font-medium' : '',
                    step.status === 'done' ? 'text-stone' : '',
                    step.status === 'waiting' ? 'text-muted' : '',
                  ].join(' ')}
                >
                  {step.label}
                </span>
              </div>
            ))}
          </div>

          {/* Error state */}
          {error && (
            <div className="rounded-sm border border-red/20 bg-red/5 px-4 py-3 mb-6 text-sm text-red">
              {error} — your profile may still be usable.
            </div>
          )}

          {/* Phone discrepancy notice */}
          {phoneDiscrepancy && (
            <div className="rounded-sm border border-amber/30 bg-amber/5 px-4 py-3 mb-6 text-sm text-ink">
              <p className="font-medium mb-1">Two phone numbers found</p>
              <p className="text-stone">
                Habitissimo shows <span className="font-mono text-xs bg-border/60 px-1.5 py-0.5 rounded">{phoneDiscrepancy.habitissimo_phone}</span>.
                Your account uses <span className="font-mono text-xs bg-border/60 px-1.5 py-0.5 rounded">{phoneDiscrepancy.known_phone}</span>.
                We'll ask you which to use in the next step.
              </p>
            </div>
          )}

          {/* Live profile preview */}
          {profile && (
            <div>
              <p className="text-xs font-semibold uppercase tracking-wide text-muted mb-2 px-1">
                Preview
              </p>
              <div className="rounded-sm border border-border overflow-hidden">
                <ProfileCanvas p={profile} />
              </div>
            </div>
          )}

          {/* Placeholder while no profile yet */}
          {!profile && !error && (
            <div className="rounded-sm border border-dashed border-border flex items-center justify-center py-16">
              <p className="text-sm text-muted">Your profile will appear here as it builds…</p>
            </div>
          )}

        </div>
      </div>

      {/* Phone collection — full-screen step (shared FullScreenStep container) */}
      {needsPhone && (
        <FullScreenStep
          icon={<Phone size={20} className="text-terracotta" />}
          title="What's your phone number?"
          subtitle="We use it to verify your identity online — checking that it's really you on Facebook groups and review sites, not another company with the same name."
          footer={
            <form onSubmit={handlePhoneSubmit} className="flex flex-col gap-3">
              <Button variant="terracotta" fullWidth className="py-3.5 text-card disabled:opacity-40 active:scale-[0.98]" type="submit"
                disabled={phoneSubmitting || phoneInput.trim().length < 7}>{phoneSubmitting ? 'Continuing…' : 'Continue →'}</Button>
              <Button
                type="button"
                onClick={() => { setNeedsPhone(false); handleNavigateToCanvas(); }}
                className="text-center text-xs text-muted py-1"
              >
                Skip for now
              </Button>
            </form>
          }
        >
          <div className="flex items-center gap-2 rounded-sm border border-border bg-card px-4 py-3.5 focus-within:border-terracotta transition-colors">
            <span className="text-sm text-stone shrink-0">+</span>
            <Input
              type="tel"
              inputMode="tel"
              autoFocus
              placeholder="34 612 345 678"
              value={phoneInput}
              onChange={(e) => setPhoneInput(e.target.value)}
              className="flex-1 bg-transparent text-sm text-ink placeholder:text-muted outline-none"
              autoComplete="tel"
            />
          </div>
        </FullScreenStep>
      )}
    </div>
  );
}
