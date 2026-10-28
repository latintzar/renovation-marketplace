/**
 * Dashboard — Contractor's action queue + revenue snapshot.
 *
 * Jobber-inspired: home screen is not just a job list — it's an action queue
 * with revenue metrics. Jobs needing action surface at the top.
 *
 * Uses useAuth() for contractor identity. apiFetch() handles auth headers.
 */

import { useEffect, useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import {
  Plus, Briefcase, MapPin, Settings, User, Landmark,
  Bell, AlertCircle, ChevronRight,
} from 'lucide-react';
import { fetchContractorScopes, type ScopeSummary } from '../lib/api';
import { eur } from '../lib/utils';
import type { Milestone as FullMilestone } from '../components/project/types';
import { useAuth } from '../context/AuthContext';
import { LanguageToggle } from '../components/LanguageToggle';
import { LeoLogo } from '../components/LeoLogo';
import { SubmitProofSheet } from '../components/dashboard/SubmitProofSheet';
import { VariationCreateSheet } from '../components/dashboard/VariationCreateSheet';
import { JobCard } from '../components/dashboard/JobCard';
import { useReelStepDriver } from '../reel/useReelStepDriver';
import { reelData } from '../reel/engine';
import { Button } from '@scope/ui';

type Milestone = Pick<FullMilestone, 'title' | 'status'>;

// ---------------------------------------------------------------------------
// Main page
// ---------------------------------------------------------------------------

type NavTab = 'jobs' | 'nearby' | 'settings';

export default function Dashboard() {
  const navigate = useNavigate();
  const { contractorId, contractorName, stripeConnected, loading: authLoading } = useAuth();
  const [scopes, setScopes] = useState<ScopeSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [activeTab] = useState<NavTab>('jobs');

  const [proofSheet, setProofSheet] = useState<{ open: boolean; token: string; milestones: Milestone[] }>({
    open: false, token: '', milestones: [],
  });
  const [variationSheet, setVariationSheet] = useState<{ open: boolean; token: string }>({
    open: false, token: '',
  });

  useEffect(() => {
    if (authLoading) return;

    if (!contractorId) {
      navigate('/', { replace: true });
      return;
    }

    fetchContractorScopes(contractorId).then((result) => {
      if (result.error) setError(result.error);
      else setScopes(result.scopes);
      setLoading(false);
    });
  }, [authLoading, contractorId, navigate]);

  // Reel mode: auto-play the "submit proof of a finished phase" walkthrough.
  useReelStepDriver(
    'submit-proof',
    () => {
      const job = reelData<{ scopes: { token: string; milestones: { title: string; status: string }[] }[] }>().scopes?.[0];
      if (!job) return [];
      return [
        { caption: "A contractor's jobs — each paid into escrow, phase by phase.", holdMs: 2800 },
        {
          caption: 'Finished a phase? They send photo proof in seconds.',
          action: () => setProofSheet({ open: true, token: job.token, milestones: job.milestones }),
          holdMs: 6800,
        },
        {
          caption: 'Sent — the homeowner is notified to review and release.',
          action: () => setProofSheet({ open: false, token: '', milestones: [] }),
          holdMs: 3400,
        },
      ];
    },
    [contractorId],
  );

  const handleNewQuote = () => {
    if (contractorId) {
      navigate(`/quote/first?contractorId=${encodeURIComponent(contractorId)}${scopes.length === 0 ? '&first=true' : ''}`);
    }
  };

  const displayName = contractorName || '';

  // Revenue strip calculations
  const paidScopes = scopes.filter((s) => s.payment_status === 'paid');
  const totalEscrowCents = paidScopes.reduce((sum, s) => sum + (s.amount_total_cents ?? 0), 0);
  const releasedCents = 0;
  const inEscrowCents = totalEscrowCents - releasedCents;

  // Needs-action items
  const needsAction = scopes.filter((s) => {
    if (s.payment_status === 'unpaid' || (!s.payment_status && s.status !== 'paid')) return true;
    return false;
  });

  const initials = displayName
    ? displayName.split(' ').map((w) => w[0]).slice(0, 2).join('').toUpperCase()
    : '?';

  return (
    <div className="min-h-dvh bg-cream flex flex-col">
      {/* Header */}
      <header className="shrink-0 sticky top-0 z-50 bg-cream/95 backdrop-blur-lg border-b border-border pt-safe">
        <div className="flex items-center justify-between px-4 h-14 max-w-lg mx-auto">
          <LeoLogo variant="charcoal" height={17} />
          <h1 className="font-display text-base font-semibold text-ink">My jobs</h1>
          <div className="flex items-center gap-2">
            <LanguageToggle variant="light" />
            <Button type="button" onClick={() => navigate('/settings')} className="relative">
              <Bell size={20} className="text-stone hover:text-ink transition-colors" />
            </Button>
            <Button
              type="button"
              onClick={() => navigate('/settings')}
              className="w-8 h-8 rounded-full bg-terracotta/15 flex items-center justify-center text-terracotta text-[11px] font-bold hover:bg-terracotta/25 transition-colors"
              aria-label="Profile &amp; settings"
            >
              {displayName ? initials : <User size={15} strokeWidth={2} />}
            </Button>
          </div>
        </div>
      </header>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto pb-28 max-w-lg mx-auto w-full">
        {/* Revenue strip */}
        {paidScopes.length > 0 && (
          <div className="mx-4 mt-4 grid grid-cols-2 gap-2">
            <div className="bg-white rounded-sm px-4 py-3 border border-border">
              <p className="text-xs text-stone">In escrow</p>
              <p className="text-base font-bold text-ink">{eur(inEscrowCents)}</p>
            </div>
            <div className="bg-white rounded-sm px-4 py-3 border border-border">
              <p className="text-xs text-stone">Active jobs</p>
              <p className="text-base font-bold text-ink">{paidScopes.length}</p>
            </div>
          </div>
        )}

        <div className="px-4 pt-4 space-y-4">
          {/* Stripe CTA */}
          {!stripeConnected && (
            <Button
              type="button"
              onClick={() => navigate(`/stripe/kyc?contractor=${encodeURIComponent(contractorId || '')}`)}
              className="w-full flex items-center gap-3 px-4 py-3.5 rounded-sm text-left transition-colors active:scale-[0.98] duration-150"
              style={{ background: '#FFF8F0', border: '1.5px solid rgba(198,93,58,0.35)' }}
            >
              <div className="w-10 h-10 rounded-full flex items-center justify-center shrink-0" style={{ background: 'rgba(198,93,58,0.12)' }}>
                <Landmark size={18} style={{ color: '#C65D3A' }} strokeWidth={1.8} />
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-ink">Connect your bank to get paid</p>
                <p className="text-xs leading-relaxed mt-0.5 text-stone">
                  Link your IBAN to receive payments from clients directly.
                </p>
              </div>
              <ChevronRight size={16} style={{ color: '#C65D3A' }} className="shrink-0" />
            </Button>
          )}

          {/* Needs action section */}
          {needsAction.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-stone uppercase tracking-wider mb-2">
                <AlertCircle size={10} className="inline mr-1 mb-0.5" />
                Needs attention
              </p>
              <div className="space-y-2">
                {needsAction.map((scope) => (
                  <div
                    key={scope.token}
                    className="flex items-center gap-3 px-4 py-3 rounded-sm border border-amber-200 bg-amber-50"
                  >
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-ink truncate">{scope.title}</p>
                      <p className="text-xs text-amber-700">Awaiting homeowner payment</p>
                    </div>
                    <Link
                      to={`/canvas/${scope.token}`}
                      className="text-xs font-semibold text-amber-700 hover:text-amber-900 shrink-0"
                    >
                      View →
                    </Link>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* New quote CTA */}
          <Button size="lg" fullWidth className="gap-2.5 text-[15px] active:scale-[0.98] duration-150" type="button"
            onClick={handleNewQuote}
            style={{ background: 'var(--color-ink)' }}><Plus size={18} strokeWidth={2.5} />
            New quote</Button>

          {/* Job list */}
          {loading && (
            <div className="flex items-center justify-center py-16">
              <div className="w-7 h-7 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin" />
            </div>
          )}

          {!loading && error && (
            <div className="text-center py-12">
              <p className="text-sm text-stone mb-1">Could not load your jobs</p>
              <p className="text-xs text-muted">{error}</p>
            </div>
          )}

          {!loading && !error && scopes.length === 0 && (
            <div className="text-center py-16 px-4">
              <div className="w-14 h-14 rounded-full bg-terracotta/10 flex items-center justify-center mx-auto mb-4">
                <Briefcase size={24} className="text-terracotta" />
              </div>
              <p className="text-base font-semibold text-ink mb-1">No quotes yet</p>
              <p className="text-sm text-stone leading-relaxed max-w-xs mx-auto">
                Share your scope with a homeowner to receive your first payment.
              </p>
            </div>
          )}

          {!loading && !error && scopes.length > 0 && (
            <div className="space-y-2.5">
              {scopes.map((scope) => (
                <JobCard
                  key={scope.token}
                  scope={scope}
                  contractorId={contractorId || ''}
                  onSubmitProof={(token, milestones) =>
                    setProofSheet({ open: true, token, milestones })
                  }
                  onCreateVariation={(token) => setVariationSheet({ open: true, token })}
                />
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom tab navigation */}
      <nav className="fixed bottom-0 inset-x-0 z-50 bg-cream/95 backdrop-blur-lg border-t border-border pb-safe">
        <div className="flex items-stretch max-w-lg mx-auto h-16">
          <Button className="flex-1 flex-col text-terracotta" type="button"><Briefcase size={20} strokeWidth={activeTab === 'jobs' ? 2.5 : 1.8} />
            <span className="text-[10px] font-semibold">My jobs</span></Button>
          <Button variant="ghost" className="flex-1 flex-col text-stone/35 cursor-not-allowed" type="button" disabled><MapPin size={20} strokeWidth={1.8} />
            <span className="text-[10px] font-medium">Nearby</span></Button>
          <Button
            type="button"
            onClick={() => navigate('/settings')}
            className="flex-1 flex flex-col items-center justify-center gap-1 text-stone hover:text-ink transition-colors"
          >
            <Settings size={20} strokeWidth={1.8} />
            <span className="text-[10px] font-medium">Settings</span>
          </Button>
        </div>
      </nav>

      {/* Sheets */}
      <SubmitProofSheet
        open={proofSheet.open}
        onClose={() => setProofSheet({ open: false, token: '', milestones: [] })}
        quoteToken={proofSheet.token}
        contractorId={contractorId || ''}
        milestones={proofSheet.milestones}
      />
      <VariationCreateSheet
        open={variationSheet.open}
        onClose={() => setVariationSheet({ open: false, token: '' })}
        quoteToken={variationSheet.token}
        contractorId={contractorId || ''}
      />
    </div>
  );
}
