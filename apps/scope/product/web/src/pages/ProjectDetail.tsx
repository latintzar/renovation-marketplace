/**
 * ProjectDetail — Project tracking page for both homeowners and contractors.
 *
 * Shell component: handles data fetching, auth gates, and layout.
 * All sub-components live under components/project/.
 *
 * Route: /app/project/:token  (+ redirect from /app/my-project/:token)
 */

import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import Lightbox from 'yet-another-react-lightbox';
import 'yet-another-react-lightbox/styles.css';
import {
  Bell, MessageCircle, Check, ChevronDown, ChevronUp,
  Star, FileText, Loader2, ArrowLeft, X,
  WifiOff,
} from 'lucide-react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { StatusBadge, GradientScreen, GlassCard, GRADIENT_THEMES , Button } from '@scope/ui';
import { API_BASE, apiFetch } from '../lib/api';
import { useAuth } from '../context/AuthContext';

import { InlineLogin } from '../components/project/InlineLogin';
import { LeoLogo } from '../components/LeoLogo';
import { MilestoneDetailSheet } from '../components/project/MilestoneDetailSheet';
import { useReelStepDriver } from '../reel/useReelStepDriver';
import { setReelData } from '../reel/engine';
import { ReviewSheet } from '../components/project/ReviewSheet';
import { VariationDetailSheet } from '../components/project/VariationDetailSheet';
import { CancelJobSheet } from '../components/project/CancelJobSheet';
import { LanguageToggle } from '../components/LanguageToggle';
import { eur } from '../lib/utils';
import type { Milestone, MilestoneUpdate, VariationOrder, TimelineEvent } from '../components/project/types';
import { PageSkeleton } from '../components/project/PageSkeleton';
import { DocumentSheet } from '../components/project/DocumentSheet';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function getMilestoneBarStyle(status?: string): React.CSSProperties {
  if (status === 'released') return { background: '#fff' };
  if (status === 'proof_submitted' || status === 'approved') {
    return { background: 'linear-gradient(90deg, #fff 60%, rgba(255,255,255,0.28) 60%)' };
  }
  if (status === 'in_progress') return { background: 'rgba(255,255,255,0.55)' };
  return { background: 'rgba(255,255,255,0.28)' };
}

function useUnreadCount(token: string | undefined, milestoneUpdates: MilestoneUpdate[]) {
  const [count, setCount] = useState(0);
  const markSeen = useCallback(() => {
    if (!token) return;
    localStorage.setItem(`leo_seen_${token}`, String(Date.now()));
    setCount(0);
  }, [token]);

  useEffect(() => {
    if (!token || !milestoneUpdates.length) return;
    const lastSeen = Number(localStorage.getItem(`leo_seen_${token}`) || 0);
    const unseen = milestoneUpdates.filter((mu) => new Date(mu.created_at).getTime() > lastSeen).length;
    setCount(unseen);
  }, [token, milestoneUpdates]);

  return { count, markSeen };
}

function OfflineBanner() {
  const [offline, setOffline] = useState(!navigator.onLine);
  useEffect(() => {
    const on = () => setOffline(false);
    const off = () => setOffline(true);
    window.addEventListener('online', on);
    window.addEventListener('offline', off);
    return () => { window.removeEventListener('online', on); window.removeEventListener('offline', off); };
  });
  if (!offline) return null;
  return (
    <div className="shrink-0 flex items-center justify-center gap-1.5 py-1.5 px-4 text-[11px] text-amber-800 bg-amber-50 border-b border-amber-200">
      <WifiOff size={11} /> No connection
    </div>
  );
}

// Header gradient themes come from the shared @scope/ui design system
// GRADIENT_THEMES.homeowner and GRADIENT_THEMES.contractor

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------

declare const __BUILD_TIMESTAMP__: string;

export default function ProjectDetail() {
  if (typeof __BUILD_TIMESTAMP__ !== 'undefined') {
    (window as unknown as Record<string, unknown>).__leo_build = __BUILD_TIMESTAMP__;
  }

  const { token } = useParams<{ token: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user, role, contractorId: authContractorId, signOut } = useAuth();
  const [searchParams] = useSearchParams();

  const [lightboxPhotos, setLightboxPhotos] = useState<string[]>([]);
  const [lightboxIndex, setLightboxIndex] = useState(0);
  const [milestoneDetail, setMilestoneDetail] = useState<{ open: boolean; milestoneIndex: number }>({ open: false, milestoneIndex: 0 });
  const [showReview, setShowReview] = useState(false);
  const [timelineExpanded, setTimelineExpanded] = useState(false);
  const [selectedVariation, setSelectedVariation] = useState<VariationOrder | null>(null);
  const [showCancelSheet, setShowCancelSheet] = useState(false);
  const [showNotifications, setShowNotifications] = useState(false);
  const [documentSheet, setDocumentSheet] = useState<{ open: boolean; type: 'agreement' | 'invoice' }>({ open: false, type: 'agreement' });
  const [refreshing, setRefreshing] = useState(false);

  const { data: canvas, isLoading, error } = useQuery({
    queryKey: ['canvas', token],
    queryFn: () => apiFetch(`${API_BASE}/v1/canvas/${token}`).then((r) => r.json()),
    enabled: Boolean(token),
    staleTime: 30_000,
  });

  const { data: milestoneUpdates = [] } = useQuery<MilestoneUpdate[]>({
    queryKey: ['milestone-updates', token],
    queryFn: () => apiFetch(`${API_BASE}/v1/milestone-updates/${token}`).then((r) => r.ok ? r.json() : []),
    enabled: Boolean(token),
    refetchInterval: 60_000,
  });

  const { data: variations = [] } = useQuery<VariationOrder[]>({
    queryKey: ['variations', token],
    queryFn: () => apiFetch(`${API_BASE}/v1/variation-orders/${token}`).then((r) => r.ok ? r.json() : []),
    enabled: Boolean(token),
    refetchInterval: 60_000,
  });

  const { count: unreadCount, markSeen } = useUnreadCount(token, milestoneUpdates);

  const refetchAll = useCallback(async () => {
    setRefreshing(true);
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['canvas', token] }),
      queryClient.invalidateQueries({ queryKey: ['milestone-updates', token] }),
      queryClient.invalidateQueries({ queryKey: ['variations', token] }),
    ]);
    setTimeout(() => setRefreshing(false), 800);
  }, [queryClient, token]);

  const handleReleased = useCallback(() => {
    queryClient.invalidateQueries({ queryKey: ['canvas', token] });
    queryClient.invalidateQueries({ queryKey: ['milestone-updates', token] });
  }, [queryClient, token]);

  // Reel mode: auto-play the "review + release a milestone" walkthrough.
  useReelStepDriver(
    'approve-release',
    () => [
      {
        caption: 'Your contractor finishes a phase and submits photo proof.',
        action: () => {
          queryClient.invalidateQueries({ queryKey: ['canvas', token] });
          queryClient.invalidateQueries({ queryKey: ['milestone-updates', token] });
        },
        holdMs: 1800,
      },
      {
        caption: 'You open it and review the work.',
        action: () => setMilestoneDetail({ open: true, milestoneIndex: 1 }),
        holdMs: 4600,
      },
      {
        caption: 'Happy with it — you release the escrow payment with one tap.',
        action: async () => {
          setReelData<{ canvas: { milestones: { status: string }[] } }>((d) => {
            d.canvas.milestones[1].status = 'released';
          });
          await queryClient.invalidateQueries({ queryKey: ['canvas', token] });
        },
        holdMs: 3800,
      },
      {
        caption: 'Paid instantly, only when you approved. The next phase begins.',
        action: () => setMilestoneDetail({ open: false, milestoneIndex: 0 }),
        holdMs: 4400,
      },
    ],
    [token, queryClient],
  );

  if (isLoading) return <PageSkeleton />;

  if (error || !canvas) {
    return (
      <div className="flex items-center justify-center h-dvh bg-cream">
        <p className="text-sm text-stone">Project not found</p>
      </div>
    );
  }

  const scope = canvas.scope ?? canvas;
  const milestones: Milestone[] = canvas.milestones || scope?.milestones || [];
  const contractorName: string = canvas.contractor_name || 'Your contractor';
  const contractorTrade: string = canvas.contractor_trade || '';
  const homeownerEmail: string = canvas.homeowner_email || '';
  const prefillEmail = searchParams.get('email') || homeownerEmail;

  // Role detection
  const isProjectContractor = role === 'contractor' && authContractorId === canvas.contractor_id;
  const isWrongContractor = role === 'contractor' && authContractorId !== canvas.contractor_id;
  const userEmail = user?.email?.toLowerCase() || '';
  const projectEmail = homeownerEmail.toLowerCase();
  const isProjectHomeowner = role === 'homeowner' && projectEmail && userEmail === projectEmail;
  const isWrongHomeowner = role === 'homeowner' && projectEmail && userEmail !== projectEmail;
  const isHomeowner = isProjectHomeowner;
  const isUnauthenticated = !user;
  const headerTheme = isProjectContractor ? GRADIENT_THEMES.contractor : GRADIENT_THEMES.homeowner;

  const totalCents = canvas.amount_total_cents || 0;
  const scopeStatus = canvas.status || canvas.payment_status || 'paid';
  const isComplete = scopeStatus === 'complete';
  const isPaid = canvas.payment_status === 'paid';
  const totalLabel = eur(totalCents);

  const latestUpdateByIndex: Record<number, MilestoneUpdate> = {};
  for (const mu of milestoneUpdates) {
    const idx = mu.milestone_index;
    if (!latestUpdateByIndex[idx] || mu.created_at > latestUpdateByIndex[idx].created_at) {
      latestUpdateByIndex[idx] = mu;
    }
  }

  const proofCount = milestones.filter((m) => m.status === 'proof_submitted' || m.status === 'approved').length;
  const releasedCount = milestones.filter((m) => m.status === 'released').length;
  const statusText = (() => {
    if (isComplete) return { text: 'Work completed ✓', color: '#16A34A' };
    if (proofCount > 0) return { text: `${proofCount === 1 ? '1 phase ready' : `${proofCount} phases ready`} for review`, color: 'var(--color-terracotta)' };
    const activeIndex = milestones.findIndex((m) => m.status === 'in_progress');
    if (activeIndex >= 0) return { text: `Phase ${activeIndex + 1} in progress`, color: 'var(--color-teal)' };
    if (releasedCount > 0) return { text: 'Waiting for next phase', color: 'rgba(250,248,244,0.6)' };
    return { text: 'Your contractor has not started yet', color: 'rgba(250,248,244,0.6)' };
  })();

  const currentStep = milestones.filter((m) => m.status === 'released').length + 1;

  const timelineEvents: TimelineEvent[] = [];
  if (isPaid) timelineEvents.push({ icon: '✓', label: `Payment received · ${totalLabel} in escrow`, date: '' });
  for (let i = 0; i < milestones.length; i++) {
    const mu = latestUpdateByIndex[i];
    if (!mu) continue;
    const date = new Date(mu.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
    if (mu.status === 'proof_submitted') timelineEvents.push({ icon: '📷', label: `${contractorName} submitted photos of phase ${i + 1}`, date });
    if (mu.status === 'released' && mu.released_at) {
      const rDate = new Date(mu.released_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' });
      const amt = milestones[i]?.amount_cents ?? Math.round((milestones[i]?.amount ?? 0) * 100);
      timelineEvents.push({ icon: '✓', label: `${eur(amt)} released to ${contractorName}`, date: rDate });
    }
  }
  if (isComplete) timelineEvents.push({ icon: '🎉', label: 'Work completed', date: '' });
  const visibleEvents = timelineExpanded ? timelineEvents : timelineEvents.slice(-3);
  const canCancel = isPaid && milestones.every((m) => !m.status || m.status === 'pending');

  // ── Auth gates ──

  const GateLogo = () => (
    <>
      <LeoLogo variant="cream" height={26} className="mb-1" />
      <p className="text-[13px] mb-6" style={{ color: 'rgba(250,248,244,0.5)' }}>
        {contractorName}{contractorTrade ? ` · ${contractorTrade}` : ''}
      </p>
    </>
  );

  if (isUnauthenticated) {
    return (
      <GradientScreen preset="homeowner">
        <div className="flex-1 flex flex-col items-center justify-center px-6">
          <GateLogo />
          <div className="w-full max-w-sm mt-2">
            <InlineLogin prefillEmail={prefillEmail} />
          </div>
        </div>
      </GradientScreen>
    );
  }

  if (isWrongContractor) {
    return (
      <GradientScreen preset="homeowner">
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <GateLogo />
          <div className="w-full max-w-sm space-y-4">
            <GlassCard>
              <p className="text-sm text-cream mb-1">You are logged in as a contractor</p>
              <p className="text-xs" style={{ color: 'rgba(250,248,244,0.5)' }}>This link is for the homeowner. Sign out to enter as homeowner.</p>
            </GlassCard>
            <Button type="button" onClick={async () => { await signOut(); }} className="w-full flex items-center justify-center gap-2 py-3 rounded-sm bg-white text-ink text-sm font-semibold active:scale-[0.98] transition-transform">
              <X size={14} /> Sign out and enter as homeowner
            </Button>
          </div>
        </div>
      </GradientScreen>
    );
  }

  if (isWrongHomeowner) {
    return (
      <GradientScreen preset="homeowner">
        <div className="flex-1 flex flex-col items-center justify-center px-6 text-center">
          <GateLogo />
          <div className="w-full max-w-sm space-y-4">
            <GlassCard>
              <p className="text-sm text-cream mb-1">Wrong account</p>
              <p className="text-xs" style={{ color: 'rgba(250,248,244,0.5)' }}>You are logged in as {userEmail}. This project belongs to another account.</p>
            </GlassCard>
            <Button type="button" onClick={async () => { await signOut(); }} className="w-full flex items-center justify-center gap-2 py-3 rounded-sm bg-white text-ink text-sm font-semibold active:scale-[0.98] transition-transform">
              Switch account
            </Button>
          </div>
        </div>
      </GradientScreen>
    );
  }

  // ── Main project view ──

  return (
    <GradientScreen
      preset={isProjectContractor ? 'contractor' : 'homeowner'}
      style={headerTheme}
    >
      <OfflineBanner />

      <div className="shrink-0">
        <div className="flex items-center justify-between px-5 pt-4 pb-2">
            <Button
              type="button"
              onClick={() => navigate(isProjectContractor ? '/dashboard' : '/my-projects')}
              className="flex items-center gap-1 text-sm transition-colors"
              style={{ color: 'rgba(250,248,244,0.5)' }}
            >
              <ArrowLeft size={16} />
              {isProjectContractor ? 'Dashboard' : 'My projects'}
            </Button>
            <div className="flex items-center gap-3">
              <LanguageToggle variant="dark" />
              <Button type="button" onClick={() => navigate(`/job-chat/${token}`)} className="relative" aria-label="Chat">
                <MessageCircle size={20} style={{ color: 'rgba(250,248,244,0.6)' }} />
              </Button>
              <Button
                type="button"
                onClick={() => { markSeen(); setShowNotifications(true); }}
                className="relative"
                aria-label="Notifications"
              >
                <Bell size={20} style={{ color: 'rgba(250,248,244,0.6)' }} />
                {unreadCount > 0 && (
                  <span className="absolute -top-1 -right-1 w-4 h-4 rounded-full bg-terracotta text-white text-[9px] font-bold flex items-center justify-center">
                    {unreadCount > 9 ? '9+' : unreadCount}
                  </span>
                )}
              </Button>
              <Button
                type="button"
                onClick={async () => { await signOut(); }}
                className="text-[10px] px-2 py-1 rounded-sm transition-colors"
                style={{ color: 'rgba(250,248,244,0.4)', background: 'rgba(255,255,255,0.06)' }}
                aria-label="Sign out"
              >
                Sign out
              </Button>
            </div>
          </div>

          <div className="px-5 pb-5">
            <p className="text-cream font-display text-[20px] font-semibold leading-tight mb-1">
              {isComplete ? 'Project completed'
                : proofCount > 0
                  ? isHomeowner
                    ? `Phase ${milestones.findIndex((m) => m.status === 'proof_submitted') + 1} · Review photos`
                    : `Phase ${milestones.findIndex((m) => m.status === 'proof_submitted') + 1} · Photos sent`
                : releasedCount > 0 && releasedCount < milestones.length ? `Phase ${releasedCount + 1} of ${milestones.length}`
                : `${milestones.length} phases · Awaiting start`}
            </p>
            <div className="flex items-center gap-2 mb-3">
              <span className="text-[13px] font-medium" style={{ color: 'rgba(250,248,244,0.7)' }}>{totalLabel} in escrow</span>
              <span className="text-[10px]" style={{ color: 'rgba(250,248,244,0.3)' }}>·</span>
              <span className="text-[10px] uppercase tracking-wide" style={{ color: 'rgba(250,248,244,0.4)' }}>
                {contractorName}{contractorTrade ? ` · ${contractorTrade}` : ''}
              </span>
            </div>
            {milestones.length > 0 && (
              <div>
                <div className="flex gap-1 mb-1">
                  {milestones.map((m, i) => (
                    <div key={i} className="flex-1 rounded-full" style={{ height: '4px', ...getMilestoneBarStyle(m.status) }} />
                  ))}
                </div>
                <div className="flex items-center justify-between">
                  <p className="text-[11px]" style={{ color: statusText.color }}>{statusText.text}</p>
                  {!isComplete && milestones.length > 1 && (
                    <p className="text-[10px]" style={{ color: 'rgba(250,248,244,0.3)' }}>
                      {Math.min(currentStep, milestones.length)}/{milestones.length}
                    </p>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

      <div className="flex-1 overflow-y-auto min-h-0">

        {refreshing && (
          <div className="flex justify-center py-3">
            <Loader2 size={16} className="text-cream/40 animate-spin" />
          </div>
        )}
        <div className="bg-white min-h-[80dvh] rounded-t-xl shadow-[0_-4px_20px_rgba(0,0,0,0.12)]">
          <div className="px-5 pt-6 pb-10 max-w-xl mx-auto">
            <div className="flex items-center gap-2 mb-5">
              <StatusBadge status={scopeStatus} />
              {isComplete && <span className="text-xs text-stone">Work completed</span>}
            </div>

            {milestones.map((milestone, index) => {
              const status = milestone.status || 'pending';
              const update = latestUpdateByIndex[index];
              const amountCents = milestone.amount_cents ?? Math.round(milestone.amount * 100);
              const amountLabel = eur(amountCents);
              const milestoneVariations = variations.filter((v) => (v as VariationOrder & { milestone_index?: number }).milestone_index === index);

              return (
                <div key={index}>
                  <div className="flex items-start gap-3 py-4 border-b border-border last:border-b-0">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-0.5 border-2 ${
                      status === 'released' ? 'border-transparent bg-ink'
                      : status === 'proof_submitted' || status === 'approved' ? 'border-terracotta bg-terracotta/10'
                      : status === 'in_progress' ? 'border-stone/40 bg-stone/5'
                      : 'border-border bg-cream'
                    }`}>
                      {status === 'released' && <Check size={14} className="text-cream" strokeWidth={2.5} />}
                      {(status === 'proof_submitted' || status === 'approved') && <span className="w-2.5 h-2.5 rounded-full bg-terracotta" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-2 mb-0.5">
                        <p className={`text-[13px] font-semibold ${status === 'released' ? 'text-stone line-through' : 'text-ink'}`}>{milestone.title}</p>
                        <span className="text-[13px] font-semibold text-ink shrink-0">{amountLabel}</span>
                      </div>
                      {status === 'released' && (
                        <p className="text-[11px] text-green mt-0.5">
                          Released from escrow{update?.released_at ? ` · ${new Date(update.released_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}` : ''}
                        </p>
                      )}
                      {(status === 'proof_submitted' || status === 'approved' || status === 'released') && update && (
                        <div className="mt-2.5">
                          {update.photos.length > 0 && (
                            <div className="flex gap-2 mb-2.5 overflow-x-auto pb-1">
                              {update.photos.slice(0, 3).map((photo, pi) => (
                                <div key={pi} className="shrink-0 relative">
                                  <img src={photo} alt={`Photo ${pi + 1}`} className="w-[72px] h-[72px] object-cover rounded-sm border border-border"
                                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
                                  {pi === 2 && update.photos.length > 3 && (
                                    <div className="absolute inset-0 bg-ink/40 rounded-sm flex items-center justify-center">
                                      <span className="text-white text-xs font-semibold">+{update.photos.length - 3}</span>
                                    </div>
                                  )}
                                </div>
                              ))}
                            </div>
                          )}
                          {update.note && <p className="text-[11px] text-stone italic mb-2.5 line-clamp-1">"{update.note}"</p>}
                          {(status === 'proof_submitted' || status === 'approved') && (
                            <Button
                              type="button"
                              onClick={() => setMilestoneDetail({ open: true, milestoneIndex: index })}
                              className="w-full flex items-center justify-center gap-2 py-3 rounded-sm text-[13px] font-semibold active:scale-[0.98] transition-transform border-2"
                              style={{ borderColor: 'var(--color-teal)', color: 'var(--color-teal)' }}
                            >
                              {isHomeowner ? `Review phase ${index + 1}` : `View photos · Phase ${index + 1}`}
                            </Button>
                          )}
                          {status === 'released' && (
                            <Button type="button" onClick={() => setMilestoneDetail({ open: true, milestoneIndex: index })} className="text-[11px] text-stone hover:text-ink transition-colors mt-1">
                              View details →
                            </Button>
                          )}
                        </div>
                      )}
                      {status === 'in_progress' && <p className="text-[11px] text-stone mt-0.5">{contractorName} is working on this phase</p>}
                      {(!status || status === 'pending') && <p className="text-[11px] text-muted mt-0.5">Waiting for {contractorName}</p>}
                    </div>
                  </div>
                  {milestoneVariations.map((v) => (
                    <Button
                      key={v.id}
                      type="button"
                      onClick={() => setSelectedVariation(v)}
                      className="w-full ml-11 mb-3 rounded-sm overflow-hidden border border-amber-200 text-left active:scale-[0.98] transition-transform"
                      style={{ borderLeft: '3px solid #D97706' }}
                    >
                      <div className="px-3 py-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] font-semibold text-amber-700 uppercase tracking-wide">Change order</span>
                          <StatusBadge status={v.status} />
                        </div>
                        <p className="text-[13px] font-medium text-ink">{v.title}</p>
                        <div className="flex items-center justify-between mt-1">
                          <span className="text-[13px] font-semibold text-ink">+{eur(v.amount_cents)}</span>
                          {v.status === 'pending' && <span className="text-[10px] text-stone">View details →</span>}
                        </div>
                      </div>
                    </Button>
                  ))}
                </div>
              );
            })}

            {timelineEvents.length > 0 && (
              <div className="mt-6">
                <div className="flex items-center justify-between mb-3">
                  <h3 className="text-[13px] font-semibold text-ink">History</h3>
                  {timelineEvents.length > 3 && (
                    <Button type="button" onClick={() => setTimelineExpanded(!timelineExpanded)} className="flex items-center gap-1 text-[11px] text-stone hover:text-ink transition-colors">
                      {timelineExpanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
                      {timelineExpanded ? 'Show less' : 'Show all'}
                    </Button>
                  )}
                </div>
                <div className="space-y-2.5">
                  {visibleEvents.map((event, i) => (
                    <div key={i} className="flex items-start gap-2.5">
                      <span className="text-sm leading-none mt-0.5">{event.icon}</span>
                      <div className="flex-1 flex items-start justify-between gap-2">
                        <span className="text-stone text-[11px] leading-relaxed">{event.label}</span>
                        {event.date && <span className="text-muted text-[10px] shrink-0">{event.date}</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            <Button variant="ghost" fullWidth className="mt-4 text-[11px] text-muted/60 hover:text-stone text-center" type="button" onClick={refetchAll}>Refresh</Button>

            {isComplete && (
              <div className="mt-6 py-5 px-4 rounded-sm text-center" style={{ background: 'rgba(22, 163, 74, 0.07)', border: '1px solid rgba(22, 163, 74, 0.18)' }}>
                <Check size={22} className="text-green mx-auto mb-2" />
                <p className="text-[13px] font-semibold text-ink">Work completed</p>
                <p className="text-[11px] text-stone mt-0.5">All payments have been released</p>
                <div className="flex gap-2 mt-4">
                  <Button type="button" onClick={() => setShowReview(true)} className="flex-1 flex items-center justify-center gap-1.5 py-3 rounded-sm bg-ink text-cream text-[13px] font-semibold">
                    <Star size={13} /> Review
                  </Button>
                  <Button type="button" onClick={() => setDocumentSheet({ open: true, type: 'invoice' })} className="flex-1 flex items-center justify-center gap-1.5 py-3 rounded-sm border border-border text-stone text-[13px] font-medium">
                    <FileText size={13} /> Invoice
                  </Button>
                </div>
              </div>
            )}

            <div className="mt-5 flex gap-3">
              <Button type="button" onClick={() => setDocumentSheet({ open: true, type: 'agreement' })} className="flex items-center gap-1.5 text-[11px] text-stone hover:text-ink transition-colors">
                <FileText size={12} /> View agreement
              </Button>
            </div>

            {isHomeowner && canCancel && !isComplete && (
              <div className="mt-6 text-center">
                <Button type="button" onClick={() => setShowCancelSheet(true)} className="text-[11px] text-muted/60 hover:text-stone transition-colors underline underline-offset-2">
                  Cancel this job
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>

      <Lightbox
        open={lightboxPhotos.length > 0}
        close={() => setLightboxPhotos([])}
        index={lightboxIndex}
        slides={lightboxPhotos.map((src) => ({ src }))}
      />

      {milestones[milestoneDetail.milestoneIndex] && (
        <MilestoneDetailSheet
          open={milestoneDetail.open}
          onClose={() => setMilestoneDetail({ open: false, milestoneIndex: 0 })}
          milestone={milestones[milestoneDetail.milestoneIndex]}
          milestoneIndex={milestoneDetail.milestoneIndex}
          update={latestUpdateByIndex[milestoneDetail.milestoneIndex]}
          contractorName={contractorName}
          quoteToken={token!}
          onReleased={handleReleased}
          navigateToChat={() => { setMilestoneDetail({ open: false, milestoneIndex: 0 }); navigate(`/job-chat/${token}`); }}
          onOpenLightbox={(photos, idx) => { setLightboxPhotos(photos); setLightboxIndex(idx); }}
          canRelease={Boolean(isHomeowner)}
        />
      )}

      <ReviewSheet open={showReview} onClose={() => setShowReview(false)} quoteToken={token!} />

      <VariationDetailSheet
        variation={selectedVariation}
        quoteToken={token!}
        onClose={() => setSelectedVariation(null)}
        onActioned={() => queryClient.invalidateQueries({ queryKey: ['variations', token] })}
      />

      <CancelJobSheet
        open={showCancelSheet}
        onClose={() => setShowCancelSheet(false)}
        totalCents={totalCents}
        contractorName={contractorName}
        quoteToken={token!}
        onCancelled={() => queryClient.invalidateQueries({ queryKey: ['canvas', token] })}
        navigateToChat={() => navigate(`/job-chat/${token}`)}
      />

      {showNotifications && (
        <>
          <div className="fixed inset-0 z-40 bg-ink/40" onClick={() => setShowNotifications(false)} />
          <div
            className="fixed top-0 left-0 right-0 z-50 rounded-b-sm overflow-hidden"
            style={{ background: 'var(--color-cream)', maxHeight: '75dvh', animation: 'slideDown 0.25s ease-out' }}
          >
            <style>{`@keyframes slideDown { from { transform: translateY(-100%); } to { transform: translateY(0); } }`}</style>
            <div className="shrink-0 flex items-center justify-between px-5 pt-5 pb-3 border-b border-border/50">
              <h3 className="text-base font-semibold text-ink font-display">Recent activity</h3>
              <Button type="button" onClick={() => setShowNotifications(false)} className="p-1.5 rounded-sm text-muted hover:text-ink hover:bg-border/50 transition-colors">
                <X size={18} />
              </Button>
            </div>
            <div className="overflow-y-auto px-5 pt-4 pb-6" style={{ maxHeight: 'calc(75dvh - 60px)' }}>
              {timelineEvents.length === 0 ? (
                <p className="text-sm text-stone text-center py-4">No activity yet</p>
              ) : (
                <div className="space-y-3">
                  {timelineEvents.map((event, i) => (
                    <div key={i} className="flex items-start gap-3">
                      <span className="text-base leading-none mt-0.5">{event.icon}</span>
                      <div className="flex-1">
                        <p className="text-sm text-ink leading-relaxed">{event.label}</p>
                        {event.date && <p className="text-[10px] text-muted mt-0.5">{event.date}</p>}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </>
      )}

      <DocumentSheet
        open={documentSheet.open}
        onClose={() => setDocumentSheet({ ...documentSheet, open: false })}
        src={documentSheet.type === 'agreement' ? `/v1/documents/${token}/agreement` : `/v1/documents/${token}/invoice`}
        title={documentSheet.type === 'agreement' ? 'Construction Agreement' : 'Work Invoice'}
      />
    </GradientScreen>
  );
}
