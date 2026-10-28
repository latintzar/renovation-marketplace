import { useEffect, useState, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import { ArrowLeft, Star, ExternalLink, MessageCircle, Briefcase, Clock, ChevronDown, CheckCircle, Send } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { fetchInbox, approveOutreach, type InboxData, type InboxResponse, type ProfileUpdate } from '../lib/api';
import { ProfileCanvas, BriefCanvas , Button } from '@scope/ui';
import { LanguageToggle } from '../components/LanguageToggle';
import { PageLoading } from '../components/PageLoading';

type Panel = 'list' | 'profile';

export default function JobInbox() {
  const { t } = useTranslation();
  const { token } = useParams<{ token: string }>();
  const [data, setData] = useState<InboxData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [panel, setPanel] = useState<Panel>('list');
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const [briefOpen, setBriefOpen] = useState(false);
  const [approving, setApproving] = useState(false);
  const [approvalDone, setApprovalDone] = useState(false);
  const [approvalError, setApprovalError] = useState('');

  const load = useCallback(async () => {
    if (!token) return;
    setLoading(true);
    const result = await fetchInbox(token);
    if (result.error) {
      setError(result.error);
    } else {
      setData(result);
    }
    setLoading(false);
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const selected: InboxResponse | null = data?.responses[selectedIdx] ?? null;

  const handleViewProfile = (idx: number) => {
    setSelectedIdx(idx);
    setPanel('profile');
  };

  const handleViewBrief = () => {
    setBriefOpen((o) => !o);
  };

  const handleBack = () => {
    setPanel('list');
    setSelectedIdx(-1);
  };

  const handleApproveOutreach = async () => {
    if (!token || approving || approvalDone) return;
    setApproving(true);
    setApprovalError('');
    const result = await approveOutreach(token);
    setApproving(false);
    if (result.ok) {
      setApprovalDone(true);
      await load();
    } else {
      setApprovalError(result.error || t('approval_failed'));
    }
  };

  const waLink = (r: InboxResponse) => {
    const phone = r.contractor_phone.replace(/[^0-9]/g, '');
    const msg = encodeURIComponent(
      `Hi ${r.contractor_name || ''}! I saw your response on Leo and I'd love to discuss the project further.`
    );
    return `https://wa.me/${phone}?text=${msg}`;
  };

  // ── Loading / Error ─────────────────────────────────────────────

  if (loading) return <PageLoading label={t('inbox_loading')} />;

  if (error || !data) {
    return (
      <div className="flex items-center justify-center h-dvh bg-cream">
        <div className="text-center px-6">
          <p className="text-lg font-display font-semibold text-ink mb-2">{t('inbox_not_found')}</p>
          <p className="text-sm text-muted">{error || t('inbox_link_expired')}</p>
        </div>
      </div>
    );
  }

  const { job, responses, total_responses } = data;
  const briefTitle = job.brief?.title || t('inbox_your_job');

  // ── Header ──────────────────────────────────────────────────────

  const header = (
    <header
      className="shrink-0 flex items-center justify-between px-4 h-14 bg-ink"
    >
      <div className="flex items-center gap-3">
        {panel !== 'list' ? (
          <Button className="p-1.5 -ml-1.5" onClick={handleBack}
            aria-label="Back to list"><ArrowLeft className="w-5 h-5 text-white/80" /></Button>
        ) : null}
        <h1 className="font-display text-[15px] font-semibold text-white truncate">
          {panel === 'profile' && selected
            ? selected.contractor_name || t('inbox_contractor_profile')
            : t('inbox_title')}
        </h1>
      </div>
      {panel === 'list' ? (
        <Button size="sm" onClick={handleViewBrief}
          style={{ background: 'rgba(255,255,255,0.1)', color: '#F5F5F4' }}>{briefOpen ? t('inbox_close_brief') : t('inbox_view_brief')}</Button>
      ) : null}
      <LanguageToggle variant="dark" />
    </header>
  );

  // ── Profile panel ───────────────────────────────────────────────

  if (panel === 'profile' && selected) {
    const profileData: ProfileUpdate | null = selected.profile && 'business_name' in selected.profile
      ? selected.profile as ProfileUpdate
      : null;

    return (
      <div className="flex flex-col h-dvh bg-cream">
        {header}
        <div className="flex-1 overflow-y-auto">
          {/* Profile card area — mirrors the PreviewPanel vellum look */}
          <div
            className="mx-3 mt-3 rounded-sm overflow-hidden"
            style={{ background: 'var(--color-cream)', border: '1px solid var(--color-border)' }}
          >
            <div className="p-4">
              {profileData ? (
                <ProfileCanvas p={profileData} />
              ) : (
                <div className="space-y-3 text-stone">
                  <h3 className="font-display text-lg font-semibold text-ink">
                    {selected.contractor_name || 'Contractor'}
                  </h3>
                  {selected.houzz_profile_url ? (
                    <a
                      href={selected.houzz_profile_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 text-xs text-terra hover:underline"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                      View on Houzz
                    </a>
                  ) : null}
                  <p className="text-sm text-muted">
                    {t('inbox_profile_incomplete')}
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Voice note response */}
          {selected.voice_transcript || selected.reaction ? (
            <div
              className="mx-3 mt-3 rounded-sm overflow-hidden p-4"
              style={{ background: 'var(--color-cream)', border: '1px solid var(--color-border)' }}
            >
              <h4 className="text-xs font-semibold uppercase tracking-wide text-muted mb-3">
                {t('inbox_their_response')}
              </h4>
              {selected.reaction ? (
                <div className="mb-2.5">
                  <dt className="text-xs text-muted font-medium mb-0.5">{t('inbox_initial_reaction')}</dt>
                  <dd className="text-sm text-stone">{selected.reaction}</dd>
                </div>
              ) : null}
              {selected.site_visit_needs ? (
                <div className="mb-2.5">
                  <dt className="text-xs text-muted font-medium mb-0.5">{t('inbox_site_visit')}</dt>
                  <dd className="text-sm text-stone">{selected.site_visit_needs}</dd>
                </div>
              ) : null}
              {selected.availability ? (
                <div className="mb-2.5">
                  <dt className="text-xs text-muted font-medium mb-0.5">{t('inbox_availability')}</dt>
                  <dd className="text-sm text-stone">{selected.availability}</dd>
                </div>
              ) : null}
              {selected.voice_transcript && !selected.reaction ? (
                <p className="text-sm text-stone whitespace-pre-wrap italic">
                  "{selected.voice_transcript}"
                </p>
              ) : null}
            </div>
          ) : null}

          {/* AI commentary */}
          {selected.ai_commentary ? (
            <div
              className="mx-3 mt-3 rounded-sm overflow-hidden p-4"
              style={{ background: 'rgba(17,94,89,.06)', border: '1px solid rgba(17,94,89,.12)' }}
            >
              <h4 className="text-xs font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-teal)' }}>
                {t('inbox_leos_take')}
              </h4>
              <p className="text-sm" style={{ color: 'var(--color-teal)' }}>{selected.ai_commentary}</p>
            </div>
          ) : null}

          {/* WhatsApp CTA */}
          <div className="px-3 py-4">
            <a
              href={waLink(selected)}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center justify-center gap-2 w-full py-3 rounded-sm text-white text-sm font-semibold transition-transform active:scale-[0.98]"
              style={{ background: '#25D366' }}
            >
              <MessageCircle className="w-4 h-4" />
              {t('inbox_chat_whatsapp')}
            </a>
          </div>
        </div>
      </div>
    );
  }

  // ── Response list ───────────────────────────────────────────────

  const statusBadge = job.status === 'collecting' ? (
    <span
      className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-md"
      style={{ background: 'rgba(217,119,6,.12)', color: '#B45309' }}
    >
      {t('inbox_status_collecting')}
    </span>
  ) : job.status === 'ready' ? (
    <span
      className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-md"
      style={{ background: 'rgba(17,94,89,.12)', color: 'var(--color-teal)' }}
    >
      {t('inbox_status_ready')}
    </span>
  ) : null;

  return (
    <div className="flex flex-col h-dvh bg-cream relative overflow-hidden">
      {header}
      <div className="shrink-0 px-4 py-3 flex items-center justify-between" style={{ background: 'var(--color-cream)', borderBottom: '1px solid var(--color-border)' }}>
        <div>
          <h2 className="font-display text-sm font-semibold text-ink">{briefTitle}</h2>
          <p className="text-xs text-muted mt-0.5">
            {total_responses} response{total_responses !== 1 ? 's' : ''} · {job.outreach_count} contacted
          </p>
        </div>
        {statusBadge}
      </div>

      {/* Approval banner — shown when outreach is pending founder sign-off */}
      {(job.outreach_approval_status === 'pending_approval' || approvalDone) && panel === 'list' ? (
        <div
          className="shrink-0 mx-3 mt-3 rounded-sm p-4"
          style={{
            background: approvalDone
              ? 'rgba(17,94,89,.06)'
              : 'rgba(217,119,6,.06)',
            border: approvalDone
              ? '1px solid rgba(17,94,89,.2)'
              : '1px solid rgba(217,119,6,.2)',
          }}
        >
          {approvalDone ? (
            <div className="flex items-start gap-3">
              <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" style={{ color: 'var(--color-teal)' }} />
              <div>
                <p className="text-sm font-semibold" style={{ color: 'var(--color-teal)' }}>
                  {t('inbox_outreach_started')}
                </p>
                <p className="text-xs mt-0.5" style={{ color: 'var(--color-teal)', opacity: 0.8 }}>
                  {t('inbox_outreach_started_desc')}
                </p>
              </div>
            </div>
          ) : (
            <div>
              <div className="flex items-start gap-3 mb-3">
                <Send className="w-4 h-4 shrink-0 mt-0.5" style={{ color: '#B45309' }} />
                <div>
                  <p className="text-sm font-semibold" style={{ color: '#B45309' }}>
                    {t('inbox_discovery_complete')}
                  </p>
                  <p className="text-xs mt-0.5" style={{ color: '#B45309', opacity: 0.8 }}>
                    {(job.houzz_candidates_count ?? 0) + (job.fb_candidates_count ?? 0)} contractors found
                    {job.houzz_candidates_count ? ` · ${job.houzz_candidates_count} from Houzz` : ''}
                    {job.fb_candidates_count ? ` · ${job.fb_candidates_count} from Facebook` : ''}
                  </p>
                </div>
              </div>
              {approvalError ? (
                <p className="text-xs mb-2" style={{ color: '#DC2626' }}>{approvalError}</p>
              ) : null}
              <Button fullWidth className="active:scale-[0.98] disabled:opacity-60" onClick={handleApproveOutreach}
                disabled={approving}
                style={{ background: '#B45309', color: '#fff' }}>{approving ? t('inbox_sending') : t('inbox_approve_outreach')}</Button>
            </div>
          )}
        </div>
      ) : null}

      {/* Response cards */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-2.5">
        {responses.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-6">
            <Briefcase className="w-10 h-10 text-muted/30 mb-3" />
            <p className="font-display text-sm font-semibold text-ink mb-1">{t('inbox_no_responses')}</p>
            <p className="text-xs text-muted leading-relaxed">
              {t('inbox_no_responses_desc')}
            </p>
          </div>
        ) : (
          responses.map((r, i) => (
            <ResponseCard
              key={r.id}
              response={r}
              rank={i + 1}
              onViewProfile={() => handleViewProfile(i)}
              waLink={waLink(r)}
            />
          ))
        )}
      </div>

      {/* Brief slide-up overlay */}
      <div
        className="absolute inset-x-0 bottom-0 z-20 bg-cream transition-transform duration-300 ease-[cubic-bezier(0.4,0,0.2,1)] rounded-t-xl shadow-[0_-4px_20px_rgba(0,0,0,0.12)]"
        style={{
          top: '56px',
          transform: briefOpen ? 'translateY(0)' : 'translateY(100%)',
          pointerEvents: briefOpen ? 'auto' : 'none',
        }}
      >
        <div className="flex flex-col h-full">
          <div className="flex-1 overflow-y-auto">
            <BriefCanvas b={job.brief} photos={job.brief_photos} />
          </div>
          <Button
            onClick={() => setBriefOpen(false)}
            className="shrink-0 flex items-center justify-center gap-1.5 py-3 text-sm font-medium text-stone border-t border-border"
          >
            <ChevronDown className="w-4 h-4" />
            {t('inbox_close_brief')}
          </Button>
        </div>
      </div>
    </div>
  );
}


// ── Response Card ─────────────────────────────────────────────────

function ResponseCard({
  response: r,
  rank,
  onViewProfile,
  waLink,
}: {
  response: InboxResponse;
  rank: number;
  onViewProfile: () => void;
  waLink: string;
}) {
  const { t } = useTranslation();
  const sourceLabel: Record<string, string> = {
    houzz: 'Houzz',
    facebook: 'Facebook',
    direct: 'Direct',
    habitissimo: 'Habitissimo',
  };

  const isTopRanked = r.ai_rank === 1;

  return (
    <div
      className="rounded-sm overflow-hidden"
      style={{
        background: 'var(--color-cream)',
        border: isTopRanked ? '1.5px solid rgba(17,94,89,.3)' : '1px solid var(--color-border)',
        boxShadow: isTopRanked ? '0 0 0 1px rgba(17,94,89,.08)' : undefined,
      }}
    >
      {/* Card header */}
      <div className="px-4 pt-3.5 pb-3 flex items-start justify-between">
        <div className="flex items-center gap-3 min-w-0">
          {/* Rank badge */}
          <div
            className="w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style={{
              background: isTopRanked ? 'rgba(17,94,89,.15)' : 'var(--color-cream-dark)',
              color: isTopRanked ? 'var(--color-teal)' : 'var(--color-muted)',
            }}
          >
            {r.ai_rank ?? rank}
          </div>
          <div className="min-w-0">
            <h3 className="font-display text-sm font-semibold text-ink truncate">
              {r.contractor_name || 'Contractor'}
            </h3>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-[10px] text-muted">via {sourceLabel[r.source] || r.source}</span>
              {r.onboarding_complete ? (
                <span
                  className="text-[9px] font-semibold uppercase tracking-wider px-1.5 py-px rounded"
                  style={{ background: 'rgba(17,94,89,.1)', color: 'var(--color-teal)' }}
                >
                  {t('inbox_verified')}
                </span>
              ) : null}
            </div>
          </div>
        </div>
        {isTopRanked ? (
          <Star className="w-4 h-4 shrink-0" style={{ color: '#D97706', fill: '#D97706' }} />
        ) : null}
      </div>

      {/* Quick info row */}
      {(r.reaction || r.availability) ? (
        <div className="px-4 pb-2.5 flex flex-wrap gap-x-4 gap-y-1 text-xs">
          {r.reaction ? (
            <p className="text-stone line-clamp-2">"{r.reaction}"</p>
          ) : null}
          {r.availability ? (
            <div className="flex items-center gap-1 text-muted">
              <Clock className="w-3 h-3" />
              <span>{r.availability}</span>
            </div>
          ) : null}
        </div>
      ) : null}

      {/* AI commentary */}
      {r.ai_commentary ? (
        <div className="px-4 pb-3">
          <p className="text-xs leading-relaxed" style={{ color: 'var(--color-teal)' }}>
            {r.ai_commentary}
          </p>
        </div>
      ) : null}

      {/* Actions */}
      <div className="px-4 pb-3.5 flex gap-2">
        <Button size="sm" className="flex-1" onClick={onViewProfile}
          style={{ background: 'var(--color-cream-dark)', color: '#44403C' }}>{t('inbox_view_profile')}</Button>
        <a
          href={waLink}
          target="_blank"
          rel="noopener noreferrer"
          className="flex-1 py-2 rounded-sm text-xs font-semibold text-center text-white transition-transform active:scale-[0.98]"
          style={{ background: '#25D366' }}
        >
          {t('inbox_chat_whatsapp')}
        </a>
      </div>
    </div>
  );
}
