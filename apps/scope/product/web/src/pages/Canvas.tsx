/**
 * Canvas — Shareable document URL page.
 *
 * Renders a brief, profile, or scope document by token.
 *
 * For scope canvases:
 *   - Contractor view: Edit button (detects via sessionStorage contractor_id match)
 *   - Homeowner/anonymous view: Pay button (Google auth gate if not signed in)
 *   - Paid state: green "Paid — funds in escrow" badge for both views
 *
 * For profile canvases: claim or approve action drawer.
 */

import { useEffect, useState } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { Check, Clock, MessageCircle, ShieldCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { track } from '../lib/tracking';
import { BriefCanvas, ProfileCanvas, QuoteCanvas , Button } from '@scope/ui';
import { useAuth } from '../context/AuthContext';
import { useCanvasQuery } from '../hooks/useCanvasQuery';
import { LanguageToggle } from '../components/LanguageToggle';
import { ClaimProfileDrawer } from '../components/canvas/ClaimProfileDrawer';
import { ProfileActionDrawer } from '../components/canvas/ProfileActionDrawer';
import { ScopeActionBar } from '../components/canvas/ScopeActionBar';
import { PageLoading } from '../components/PageLoading';
import { LeoLogo } from '../components/LeoLogo';

// ── Post-submit confirmation modal (profile) ───────────────────────────────

function ProfileSubmitModal({ onDismiss }: { onDismiss: () => void }) {
  const { t } = useTranslation();
  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 backdrop-blur-sm animate-in fade-in duration-300"
      onClick={onDismiss}
    >
      <div
        className="w-full max-w-lg bg-cream rounded-t-3xl shadow-2xl animate-in slide-in-from-bottom duration-400 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="bg-green h-1.5 w-full" />
        <div className="px-6 pt-6 pb-8">
          <div className="flex flex-col items-center text-center mb-6">
            <div className="w-16 h-16 rounded-full bg-green/10 flex items-center justify-center mb-4 relative">
              <Check size={32} className="text-green" strokeWidth={2.5} />
              <span
                className="absolute inset-0 rounded-full bg-green/20 animate-ping"
                style={{ animationDuration: '1.4s', animationIterationCount: '2' } as React.CSSProperties}
              />
            </div>
            <h2 className="font-display text-2xl font-semibold text-ink mb-2">{t('canvas_profile_saved')}</h2>
            <p className="text-stone text-[15px] leading-relaxed max-w-sm">
              {t('canvas_profile_saved_desc')}
            </p>
          </div>

          <div className="flex items-start gap-3 bg-[#E8F8F2] rounded-sm px-4 py-3.5 mb-6">
            <MessageCircle size={20} className="text-[#25D366] shrink-0 mt-0.5" fill="#25D366" />
            <div>
              <p className="text-sm font-semibold text-ink mb-0.5">{t('canvas_job_leads_whatsapp')}</p>
              <p className="text-xs text-stone leading-relaxed">
                {t('canvas_job_leads_desc')}
              </p>
            </div>
          </div>

          <div className="space-y-2.5 mb-6">
            {[
              { icon: Clock, text: t('canvas_match_notice') },
              { icon: Check, text: t('canvas_respond_notice') },
            ].map(({ icon: Icon, text }, i) => (
              <div key={i} className="flex items-center gap-2.5 text-sm text-stone">
                <span className="w-5 h-5 rounded-full bg-border flex items-center justify-center shrink-0">
                  <Icon size={11} className="text-stone" />
                </span>
                {text}
              </div>
            ))}
          </div>

          <Button size="lg" fullWidth className="py-3.5 active:scale-[0.98] duration-150" type="button"
            onClick={onDismiss}>{t('done')}</Button>
        </div>
      </div>
    </div>
  );
}


// ── Scope edit overlay ─────────────────────────────────────────────────────


// ── Main page ──────────────────────────────────────────────────────────────

export default function Canvas() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const [searchParams] = useSearchParams();
  const [showSubmitModal, setShowSubmitModal] = useState(false);
  const { role: authRole, contractorId: authContractorId } = useAuth();

  const { data, isLoading: loading, error: queryError } = useCanvasQuery(token);
  const error = queryError?.message ?? (data?.error ?? '');

  // Tracking + sandbox auto-enable side effects when data arrives
  useEffect(() => {
    if (!data || data.error) return;
    if (data.canvas_type === 'quote' && token) {
      track('scope.viewed', { token, viewer_role: authRole ?? 'homeowner' });
    }
    // Auto-enable sandbox if the scope was created in sandbox mode.
    // Homeowner opens the link and checkout routes through test Stripe automatically.
    if (data.is_sandbox) {
      try {
        localStorage.setItem('leo_sandbox_mode', 'true');
        const prev = JSON.parse(localStorage.getItem('leo_sandbox_state') || '{}');
        localStorage.setItem('leo_sandbox_state', JSON.stringify({ ...prev, enabled: true }));
      } catch { /* storage unavailable */ }
    }
  }, [data, token, authRole]);

  // ?paid=true — show a brief success flash when returning from Stripe Checkout
  const paidParam = searchParams.get('paid') === 'true';
  const [showPaidFlash, setShowPaidFlash] = useState(paidParam);
  useEffect(() => {
    if (paidParam && token) {
      track('payment.completed', { token });
      const t = setTimeout(() => setShowPaidFlash(false), 4000);
      return () => clearTimeout(t);
    }
  }, [paidParam]);

  if (loading) return <PageLoading label={t('loading')} />;

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-dvh bg-cream">
        <div className="text-center px-6">
          <p className="text-lg font-display font-semibold text-ink mb-2">{t('canvas_not_found')}</p>
          <p className="text-sm text-muted">{error || t('canvas_link_expired')}</p>
        </div>
      </div>
    );
  }

  const body = (() => {
    switch (data.canvas_type) {
      case 'brief':
        return <BriefCanvas b={data.brief ?? null} photos={data.photos} />;
      case 'profile':
        return <ProfileCanvas p={data.profile ?? null} />;
      case 'quote':
      case 'scope':
        return <QuoteCanvas scope={data.quote ?? data.scope ?? data.quote_data ?? null} />;
      default:
        return <p className="text-sm text-muted p-6">{t('canvas_unknown_type')}</p>;
    }
  })();

  const isProfile = data.canvas_type === 'profile';
  const isScope = data.canvas_type === 'quote';
  const contractorId = data.contractor_id || token || '';
  const isClaimed = Boolean(data.claimed);

  // Determine if the current viewer is the contractor who owns this scope
  const isContractor = (() => {
    if (!isScope) return false;
    try {
      return Boolean(authContractorId && authContractorId === contractorId);
    } catch {
      return false;
    }
  })();

  const isPaid = isScope && data.payment_status === 'paid';

  return (
    <div className="flex flex-col h-dvh bg-cream">
      {/* Minimal Leo header */}
      <header className="shrink-0 flex items-center justify-between px-4 h-12 bg-ink">
        <LeoLogo variant="cream" height={15} />
        <div className="flex items-center gap-3">
          <LanguageToggle variant="dark" />
          {isContractor && (
            <a
              href="/app/dashboard"
              className="text-xs font-medium transition-colors"
              style={{ color: 'rgba(250,248,244,0.55)' }}
            >
              My jobs
            </a>
          )}
        </div>
      </header>

      {/* Paid flash banner */}
      {showPaidFlash && (
        <div className="shrink-0 flex items-center gap-2.5 px-4 py-2.5 bg-green/10 border-b border-green/20 animate-in fade-in duration-300">
          <Check size={16} className="text-green shrink-0" strokeWidth={2.5} />
          <p className="text-sm font-semibold text-green">Payment received — your funds are held securely in escrow</p>
        </div>
      )}

      {/* Canvas body — scrollable */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="mx-auto" style={{ maxWidth: '640px' }}>
          {/* Paid badge for scope */}
          {isScope && isPaid && (
            <div className="mx-3 mt-3 flex items-center gap-2.5 rounded-sm bg-green/10 border border-green/20 px-4 py-3">
              <ShieldCheck size={18} className="text-green shrink-0" />
              <div>
                <p className="text-sm font-semibold text-ink">Paid — funds held in escrow</p>
              <p className="text-xs text-stone mt-0.5">Full amount secured until each phase is completed.</p>
              </div>
            </div>
          )}

          {/* Context banner for unclaimed profile canvases */}
          {isProfile && !isClaimed && (
            <div className="mx-3 mt-3 rounded-sm bg-terracotta-light border border-terracotta/20 px-4 py-3">
              <p className="text-sm font-semibold text-ink mb-0.5">Your Leo profile is ready</p>
              <p className="text-xs text-stone leading-relaxed">
                Claim it below to start making quotes and getting paid through Leo.
              </p>
            </div>
          )}
          {isProfile && isClaimed && (
            <div className="mx-3 mt-3 rounded-sm bg-terracotta-light border border-terracotta/20 px-4 py-3">
              <p className="text-sm font-semibold text-ink mb-0.5">{t('canvas_profile_banner_title')}</p>
              <p className="text-xs text-stone leading-relaxed">
                {t('canvas_profile_banner_desc')}
              </p>
            </div>
          )}
          <div
            className="mx-3 mt-3 mb-6 rounded-sm overflow-hidden"
            style={{ border: '1px solid var(--color-border)' }}
          >
            {body}
          </div>
        </div>
      </div>

      {/* Sticky action drawers */}
      {isProfile && !isClaimed && token && (
        <ClaimProfileDrawer canvasToken={token} />
      )}
      {isProfile && isClaimed && contractorId && (
        <ProfileActionDrawer
          contractorId={contractorId}
          onSubmit={() => setShowSubmitModal(true)}
        />
      )}
      {isScope && token && (
        <ScopeActionBar
          token={token}
          contractorId={contractorId}
          isContractor={isContractor}
          isPaid={isPaid}
          scope={data.scope ?? null}
          amountTotalCents={data.amount_total_cents}
        />
      )}

      {showSubmitModal && (
        <ProfileSubmitModal onDismiss={() => setShowSubmitModal(false)} />
      )}
    </div>
  );
}
