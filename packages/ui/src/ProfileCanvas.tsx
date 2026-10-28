import { useState, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import { ArrowLeft, ChevronRight, Search, ExternalLink, Star, Globe, MapPin, ShieldCheck, X, MessageSquare } from 'lucide-react';
import type { ProfileUpdate, ProfileSource, ProfileProject, SocialMention } from './types';
import { PlatformLogo } from './PlatformLogo';
import { Button, Input } from './primitives';

// ── Shared helpers ──────────────────────────────────────────────────────

function Stars({ rating, size = 12 }: { rating: number; size?: number }) {
  const full = Math.floor(rating);
  const half = rating - full >= 0.35;
  return (
    <span className="inline-flex items-center gap-0.5 text-amber-500">
      {Array.from({ length: full }, (_, i) => (
        <Star key={i} size={size} fill="currentColor" strokeWidth={0} />
      ))}
      {half && <Star size={size} fill="currentColor" strokeWidth={0} style={{ clipPath: 'inset(0 50% 0 0)' }} />}
      <span className="ml-0.5 font-semibold tabular-nums" style={{ fontSize: size - 1 }}>
        {rating.toFixed(1)}
      </span>
    </span>
  );
}

function PhotoViewer({ url, onClose }: { url: string; onClose: () => void }) {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80" onClick={onClose}>
      <Button
        type="button"
        onClick={onClose}
        className="absolute top-4 right-4 w-10 h-10 rounded-full bg-white/20 text-white flex items-center justify-center"
        aria-label="Close"
      >
        <X size={22} />
      </Button>
      <img
        src={url}
        alt="Full size"
        className="max-w-[90vw] max-h-[85vh] object-contain rounded-md"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}

function BackBar({ label, onBack }: { label: string; onBack: () => void }) {
  return (
    <Button
      type="button"
      onClick={onBack}
      className="sticky top-0 z-10 w-full flex items-center gap-2 px-4 py-2.5 text-left"
      style={{ background: 'var(--color-cream)', borderBottom: '1px solid var(--color-border)' }}
    >
      <ArrowLeft size={16} style={{ color: 'var(--color-terracotta)' }} />
      <span className="text-[13px] font-semibold" style={{ color: 'var(--color-terracotta)' }}>{label}</span>
    </Button>
  );
}

type View =
  | { kind: 'profile' }
  | { kind: 'reviews'; source: ProfileSource }
  | { kind: 'project'; project: ProfileProject }
  | { kind: 'mentions' };

// ── Main component ──────────────────────────────────────────────────────

export default function ProfileCanvas({ p }: { p: ProfileUpdate | null }) {
  const { t } = useTranslation();
  const [view, setView] = useState<View>({ kind: 'profile' });
  const [viewPhoto, setViewPhoto] = useState<string | null>(null);

  if (!p || (!p.business_name && !p.trade && !p.bio)) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted text-sm leading-relaxed text-center px-6">
          {t('profile_empty_state')}
        </p>
      </div>
    );
  }

  const content = (() => {
    switch (view.kind) {
      case 'reviews':
        return (
          <ReviewsView
            source={view.source}
            onBack={() => setView({ kind: 'profile' })}
          />
        );
      case 'project':
        return (
          <ProjectView
            project={view.project}
            onBack={() => setView({ kind: 'profile' })}
            onViewPhoto={setViewPhoto}
          />
        );
      case 'mentions':
        return (
          <SocialMentionDetailView
            mentions={p.social_mentions ?? []}
            onBack={() => setView({ kind: 'profile' })}
          />
        );
      default:
        return (
          <ProfileView
            p={p}
            onOpenReviews={(source) => setView({ kind: 'reviews', source })}
            onOpenProject={(project) => setView({ kind: 'project', project })}
            onOpenMentions={() => setView({ kind: 'mentions' })}
            onViewPhoto={setViewPhoto}
          />
        );
    }
  })();

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {content}
      {viewPhoto && <PhotoViewer url={viewPhoto} onClose={() => setViewPhoto(null)} />}
    </div>
  );
}

// ── Profile view (default) ──────────────────────────────────────────────

function ProfileView({
  p,
  onOpenReviews,
  onOpenProject,
  onOpenMentions,
  onViewPhoto,
}: {
  p: ProfileUpdate;
  onOpenReviews: (source: ProfileSource) => void;
  onOpenProject: (project: ProfileProject) => void;
  onOpenMentions: () => void;
  onViewPhoto: (url: string) => void;
}) {
  const { t } = useTranslation();
  const services = p.services
    ? (Array.isArray(p.services) ? p.services : String(p.services).split('\n')).map((s: string) => s.trim()).filter(Boolean)
    : [];

  const allProjects = (p.sources ?? []).flatMap((s) =>
    (s.projects ?? []).map((proj) => ({ ...proj, source: proj.source || s.platform })),
  );

  const totalReviews = (p.sources ?? []).reduce((sum, s) => sum + (s.review_count ?? s.reviews?.length ?? 0), 0);

  return (
    <>
      {/* ── Dark header ── */}
      <div className="px-4 pt-3.5 pb-3" style={{ background: 'var(--color-ink)' }}>
        <div className="flex items-start gap-3">
          {p.avatar_url && (
            <div
              className="w-16 h-16 rounded-full shrink-0 flex items-center justify-center overflow-hidden"
              style={{ border: '2px solid rgba(255,255,255,.15)', background: 'var(--card)' }}
            >
              <img
                src={p.avatar_url}
                alt=""
                className="w-full h-full object-contain p-1"
              />
            </div>
          )}
          <div className="min-w-0 flex-1">
            {p.trade && (
              <span
                className="inline-block text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-md mb-1.5"
                style={{ background: 'rgba(218,101,77,.3)', color: '#FBBF90', letterSpacing: '.04em' }}
              >
                {p.trade.split(/[—–\-,]/)[0].trim()}
              </span>
            )}
            <h3 className="font-display text-[17px] font-semibold mb-0.5" style={{ color: 'var(--color-cream)' }}>
              {p.business_name || 'Business profile'}
            </h3>
            <div className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
              {p.location && (
                <span className="flex items-center gap-1 text-xs" style={{ color: 'var(--color-muted)' }}>
                  <MapPin size={10} />
                  {p.location}
                </span>
              )}
              {p.verified && (
                <span className="flex items-center gap-1 text-[10px] font-semibold" style={{ color: '#10B981' }}>
                  <ShieldCheck size={11} /> {t('profile_verified')}
                </span>
              )}
            </div>
            {p.website && (
              <a
                href={p.website}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[11px] mt-1"
                style={{ color: 'var(--color-terracotta)' }}
              >
                <Globe size={10} />
                {p.website.replace(/^https?:\/\//, '').replace(/\/$/, '')}
              </a>
            )}
          </div>
        </div>
      </div>

      {/* ── Light body ── */}
      <div className="flex-1" style={{ background: 'var(--color-cream)' }}>

        {/* Service area mini-map placeholder */}
        {p.service_area_km && (
          <div className="px-4 pt-3 pb-2">
            <div
              className="rounded-sm overflow-hidden flex items-center justify-center"
              style={{
                height: '72px',
                background: 'linear-gradient(135deg, var(--color-cream-dk) 0%, var(--color-border) 100%)',
                border: '1px solid var(--color-border)',
              }}
            >
              <div className="flex items-center gap-2 text-[11px]" style={{ color: 'var(--color-muted)' }}>
                <MapPin size={14} style={{ color: 'var(--color-terracotta)' }} />
                <span>{p.location ?? 'Service area'} · <strong>{p.service_area_km} km radius</strong></span>
              </div>
            </div>
          </div>
        )}

        {/* ── Platform review cards ── */}
        {(p.sources ?? []).length > 0 && (
          <div className="px-4 pt-2 pb-1">
            <div className="flex gap-2 overflow-x-auto pb-1">
              {(p.sources ?? []).map((src) => (
                <PlatformReviewCard key={src.platform} source={src} onTap={() => onOpenReviews(src)} />
              ))}
            </div>
          </div>
        )}

        {/* ── Social mentions (Facebook groups + forums) ── */}
        {(p.social_mentions ?? []).length > 0 && (
          <div className="px-4 pt-1 pb-1">
            <div
              className="text-[10px] font-semibold uppercase tracking-wide mb-1.5"
              style={{ color: 'var(--color-muted)' }}
            >
              {t('profile_mentioned_online')}
            </div>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {(p.social_mentions ?? []).map((m, i) => (
                <SocialMentionCard key={i} mention={m} onTap={onOpenMentions} />
              ))}
            </div>
          </div>
        )}

        {/* ── Review summary ── */}
        {p.review_summary && (
          <div className="px-4 pt-2 pb-1">
            <div
              className="rounded-sm p-3 text-[12px] leading-relaxed"
              style={{ background: 'rgba(17,94,89,.06)', border: '1px solid rgba(17,94,89,.12)', color: 'var(--color-teal)' }}
            >
              <div className="flex items-center gap-1.5 mb-1">
                <span className="font-semibold text-[11px] uppercase tracking-wide" style={{ color: '#0D9488' }}>
                  {t('profile_ai_review_summary')}
                </span>
                <span className="text-[10px]" style={{ color: '#5EEAD4' }}>
                  · {totalReviews} reviews across {(p.sources ?? []).length} platform{(p.sources ?? []).length !== 1 ? 's' : ''}
                </span>
              </div>
              {p.review_summary}
            </div>
          </div>
        )}

        {/* ── About ── */}
        {p.bio && (
          <div className="px-4 pt-3 pb-1">
            <div className="text-[11px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: 'var(--color-muted)' }}>
              {t('profile_about')}
            </div>
            <p className="text-[13px] leading-relaxed whitespace-pre-wrap" style={{ color: 'var(--color-stone)' }}>
              {p.bio}
            </p>
          </div>
        )}

        {/* ── Quick details row ── */}
        {(p.years_experience || p.languages) && (
          <div className="px-4 pt-2 pb-1 flex flex-wrap gap-x-4 gap-y-1">
            {p.years_experience && (
              <div className="text-xs">
                <span style={{ color: 'var(--color-muted)' }}>{t('profile_experience')}: </span>
                <span className="font-medium" style={{ color: 'var(--color-ink)' }}>{p.years_experience} years</span>
              </div>
            )}
            {p.languages && (
              <div className="text-xs">
                <span style={{ color: 'var(--color-muted)' }}>{t('profile_languages')}: </span>
                <span className="font-medium" style={{ color: 'var(--color-ink)' }}>{p.languages}</span>
              </div>
            )}
          </div>
        )}

        {/* ── Portfolio projects ── */}
        {allProjects.length > 0 && (
          <div className="px-4 pt-3 pb-1">
            <div className="text-[11px] font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-muted)' }}>
              {t('profile_portfolio')}
            </div>
            <div className="grid grid-cols-2 gap-2">
              {allProjects.map((proj, i) => (
                <PortfolioThumb key={i} project={proj} onTap={() => onOpenProject(proj)} />
              ))}
            </div>
          </div>
        )}

        {/* ── Gallery (all images across sources, deduplicated) ── */}
        {(p.portfolio_images ?? []).length > 0 && (
          <div className="px-4 pt-3 pb-1">
            <div className="text-[11px] font-semibold uppercase tracking-wide mb-2" style={{ color: 'var(--color-muted)' }}>
              Gallery
            </div>
            <div className="flex gap-1.5 overflow-x-auto pb-1">
              {(p.portfolio_images ?? []).map((url, i) => (
                <Button
                  key={i}
                  type="button"
                  className="shrink-0 w-20 h-20 rounded-sm overflow-hidden"
                  style={{ border: '1px solid var(--color-border)' }}
                  onClick={() => onViewPhoto(url)}
                >
                  <img src={url} alt="" className="w-full h-full object-cover" loading="lazy" />
                </Button>
              ))}
            </div>
          </div>
        )}

        {/* ── Services (tags) ── */}
        {services.length > 0 && (
          <div className="px-4 pt-3 pb-1">
            <div className="text-[11px] font-semibold uppercase tracking-wide mb-1.5" style={{ color: 'var(--color-muted)' }}>
              {t('profile_services')}
            </div>
            <div className="flex flex-wrap gap-1.5">
              {services.map((s) => (
                <span
                  key={s}
                  className="text-[11px] font-medium px-2.5 py-1 rounded-full"
                  style={{ background: 'rgba(17,94,89,.1)', color: 'var(--color-teal)' }}
                >
                  {s}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* ── Certifications ── */}
        {p.certifications && (
          <div className="px-4 pt-3 pb-1">
            <div
              className="rounded-sm p-3"
              style={{ border: '1px solid var(--color-border)', background: 'var(--color-cream-dark)' }}
            >
              <div className="text-[10px] font-semibold uppercase tracking-wide mb-0.5" style={{ color: 'var(--color-muted)' }}>
                {t('profile_certifications')}
              </div>
              <div className="text-[12px] whitespace-pre-wrap" style={{ color: 'var(--color-stone)' }}>
                {p.certifications}
              </div>
            </div>
          </div>
        )}

        {/* ── Leo work history (if any) ── */}
        {(p.leo_jobs_completed ?? 0) > 0 && (
          <div className="px-4 pt-3 pb-1">
            <div
              className="rounded-sm p-3 flex items-center gap-3"
              style={{ border: '1px solid var(--color-border)', background: 'var(--color-cream)' }}
            >
              <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0" style={{ background: 'var(--color-ink)' }}>
                <span className="text-[11px] font-bold" style={{ color: 'var(--color-cream)' }}>L</span>
              </div>
              <div>
                <div className="text-[13px] font-semibold" style={{ color: 'var(--color-ink)' }}>
                  {p.leo_jobs_completed} job{p.leo_jobs_completed !== 1 ? 's' : ''} completed on Leo
                </div>
                {p.leo_rating != null && (
                  <div className="flex items-center gap-1 mt-0.5">
                    <Stars rating={p.leo_rating} size={10} />
                    <span className="text-[10px]" style={{ color: 'var(--color-muted)' }}>from homeowners</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* ── Source attribution footer ── */}
        {(p.sources ?? []).length > 0 && (
          <div className="text-center px-4 pt-4 pb-4">
            <span className="text-[10px]" style={{ color: 'var(--color-muted)' }}>
              Profile built from{' '}
              {(p.sources ?? []).map((s) => s.platform).join(', ')}
            </span>
          </div>
        )}
      </div>
    </>
  );
}

// ── Platform review card ────────────────────────────────────────────────

function PlatformReviewCard({ source, onTap }: { source: ProfileSource; onTap: () => void }) {
  const count = source.review_count ?? source.reviews?.length ?? 0;
  const rating = source.rating ?? (() => {
    const rated = (source.reviews ?? []).filter((r) => r.rating != null).map((r) => r.rating!);
    return rated.length > 0 ? Math.round((rated.reduce((a, b) => a + b, 0) / rated.length) * 10) / 10 : undefined;
  })();
  const knownPlatform = ['habitissimo', 'houzz', 'cronoshare', 'hogami'].includes(source.platform?.toLowerCase());
  return (
    <Button
      type="button"
      onClick={onTap}
      className="shrink-0 flex items-center gap-2.5 rounded-sm px-3 py-2.5 text-left transition-colors"
      style={{ border: '1px solid var(--color-border)', background: 'var(--color-cream)', minWidth: '160px' }}
    >
      {knownPlatform ? (
        <PlatformLogo
          platform={source.platform.toLowerCase() as 'habitissimo' | 'houzz' | 'cronoshare' | 'hogami'}
          size="md"
          variant="card"
        />
      ) : source.platform_logo ? (
        <img src={source.platform_logo} alt="" className="w-7 h-7 rounded-md object-contain shrink-0" />
      ) : (
        <div
          className="w-7 h-7 rounded-md shrink-0 flex items-center justify-center text-[9px] font-bold"
          style={{ background: 'var(--color-border)', color: 'var(--color-muted)' }}
        >
          {source.platform.charAt(0).toUpperCase()}
        </div>
      )}
      <div className="min-w-0 flex-1">
        <div className="text-[11px] font-semibold truncate" style={{ color: 'var(--color-ink)' }}>
          {source.platform}
        </div>
        <div className="flex items-center gap-1">
          {rating != null && <Stars rating={rating} size={9} />}
          {count > 0 && (
            <span className="text-[10px]" style={{ color: 'var(--color-muted)' }}>
              · {count} review{count !== 1 ? 's' : ''}
            </span>
          )}
        </div>
      </div>
      <ChevronRight size={14} className="shrink-0" style={{ color: 'var(--color-border)' }} />
    </Button>
  );
}

// ── Social mention icon pill ────────────────────────────────────────────

const SOURCE_STYLES: Record<string, { bg: string; color: string; label: string }> = {
  forocoches: { bg: '#E34C26', color: '#fff', label: 'FC' },
  mediavida:  { bg: '#1DA462', color: '#fff', label: 'MV' },
  'reddit es': { bg: '#FF4500', color: '#fff', label: 'R' },
  reddit:     { bg: '#FF4500', color: '#fff', label: 'R' },
};

function sourcePill(source_name: string): { bg: string; color: string; label: string } {
  const key = source_name.toLowerCase();
  for (const k in SOURCE_STYLES) {
    if (key.includes(k)) return SOURCE_STYLES[k];
  }
  if (key.includes('facebook')) return { bg: '#1877F2', color: '#fff', label: 'F' };
  // Default: terra initials
  return { bg: 'var(--color-terracotta)', color: '#fff', label: source_name.charAt(0).toUpperCase() };
}

// ── Social mention card (horizontal scroll row) ─────────────────────────

function SocialMentionCard({ mention, onTap }: { mention: SocialMention; onTap: () => void }) {
  const pill = sourcePill(mention.source_name);
  return (
    <Button
      type="button"
      onClick={onTap}
      className="shrink-0 flex items-center gap-2.5 rounded-sm px-3 py-2.5 text-left transition-colors"
      style={{ border: '1px solid var(--color-border)', background: 'var(--color-cream)', minWidth: '172px', maxWidth: '220px' }}
    >
      {/* Source icon pill */}
      <div
        className="w-7 h-7 rounded-md shrink-0 flex items-center justify-center text-[9px] font-bold"
        style={{ background: pill.bg, color: pill.color }}
      >
        {pill.label}
      </div>
      <div className="min-w-0 flex-1 overflow-hidden">
        <div className="text-[11px] font-semibold truncate" style={{ color: 'var(--color-ink)' }}>
          {mention.source_name}
        </div>
        <div className="text-[10px] truncate" style={{ color: 'var(--color-muted)' }}>
          {mention.snippet}
        </div>
      </div>
      <ChevronRight size={14} className="shrink-0" style={{ color: 'var(--color-border)' }} />
    </Button>
  );
}

// ── Social mention detail view (drill-down) ─────────────────────────────

function SocialMentionDetailView({
  mentions,
  onBack,
}: {
  mentions: SocialMention[];
  onBack: () => void;
}) {
  const { t } = useTranslation();
  return (
    <>
      {/* Dark header */}
      <div className="px-4 pt-3 pb-3" style={{ background: 'var(--color-ink)' }}>
        <div className="flex items-center gap-2.5">
          <div
            className="w-8 h-8 rounded-md shrink-0 flex items-center justify-center"
            style={{ background: 'rgba(218,101,77,.25)' }}
          >
            <MessageSquare size={16} style={{ color: '#FBBF90' }} />
          </div>
          <div>
            <div className="text-[15px] font-semibold" style={{ color: 'var(--color-cream)' }}>
              {t('profile_mentioned_online')}
            </div>
            <div className="text-[11px]" style={{ color: 'var(--color-muted)' }}>
              {mentions.length} mention{mentions.length !== 1 ? 's' : ''} found
            </div>
          </div>
        </div>
      </div>

      <BackBar label={t('profile_back_to_profile')} onBack={onBack} />

      {/* Mention list */}
      <div className="flex-1 px-4 pb-4" style={{ background: 'var(--color-cream)' }}>
        {mentions.map((m, i) => {
          const pill = sourcePill(m.source_name);
          return (
            <div
              key={i}
              className="py-3.5"
              style={{ borderBottom: i < mentions.length - 1 ? '1px solid var(--color-border)' : 'none' }}
            >
              {/* Author row */}
              <div className="flex items-center justify-between gap-2 mb-2">
                <div className="flex items-center gap-2 min-w-0">
                  {m.author_avatar ? (
                    <img
                      src={m.author_avatar}
                      alt=""
                      className="w-8 h-8 rounded-full object-cover shrink-0"
                    />
                  ) : (
                    <div
                      className="w-8 h-8 rounded-full shrink-0 flex items-center justify-center text-[11px] font-bold"
                      style={{ background: 'var(--color-border)', color: 'var(--color-muted)' }}
                    >
                      {m.author_name ? m.author_name.charAt(0).toUpperCase() : '?'}
                    </div>
                  )}
                  <div className="min-w-0">
                    {m.author_name && (
                      m.author_url ? (
                        <a
                          href={m.author_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-[13px] font-semibold block truncate"
                          style={{ color: 'var(--color-terracotta)' }}
                        >
                          {m.author_name}
                        </a>
                      ) : (
                        <span className="text-[13px] font-semibold block truncate" style={{ color: 'var(--color-ink)' }}>
                          {m.author_name}
                        </span>
                      )
                    )}
                    {m.date && (
                      <span className="text-[10px]" style={{ color: 'var(--color-muted)' }}>{m.date}</span>
                    )}
                  </div>
                </div>
                {/* Source badge */}
                <span
                  className="shrink-0 text-[9px] font-bold px-2 py-0.5 rounded-full"
                  style={{ background: pill.bg, color: pill.color }}
                >
                  {m.source_name}
                </span>
              </div>

              {/* Snippet as terra blockquote */}
              {m.snippet && (
                <div
                  className="rounded-sm px-3 py-2.5 text-[12px] leading-relaxed mb-2"
                  style={{
                    background: 'rgba(218,101,77,.06)',
                    borderLeft: '3px solid var(--color-terracotta)',
                    color: 'var(--color-stone)',
                  }}
                >
                  "{m.snippet}"
                </div>
              )}

              {/* View full thread link */}
              <a
                href={m.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 text-[11px] font-medium"
                style={{ color: 'var(--color-terracotta)' }}
              >
                <ExternalLink size={10} />
                {t('profile_view_thread')}
              </a>
            </div>
          );
        })}
      </div>
    </>
  );
}

// ── Portfolio thumbnail ─────────────────────────────────────────────────

function PortfolioThumb({ project, onTap }: { project: ProfileProject; onTap: () => void }) {
  const { t } = useTranslation();
  const thumb = project.images?.[0];
  return (
    <Button
      type="button"
      onClick={onTap}
      className="rounded-sm overflow-hidden text-left"
      style={{ border: '1px solid var(--color-border)' }}
    >
      {thumb ? (
        <img src={thumb} alt="" className="w-full aspect-[4/3] object-cover" loading="lazy" />
      ) : (
        <div className="w-full aspect-[4/3]" style={{ background: 'var(--color-cream-dark)' }} />
      )}
      <div className="px-2.5 py-2" style={{ background: 'var(--color-cream)' }}>
        <div className="text-[12px] font-semibold truncate" style={{ color: 'var(--color-ink)' }}>
          {project.title || t('profile_project_fallback')}
        </div>
        {project.source && (
          <div className="text-[10px] mt-0.5" style={{ color: 'var(--color-muted)' }}>
            via {project.source}
          </div>
        )}
      </div>
    </Button>
  );
}

// ── Reviews view (per-platform, with search) ────────────────────────────

function ReviewsView({ source, onBack }: { source: ProfileSource; onBack: () => void }) {
  const { t } = useTranslation();
  const [query, setQuery] = useState('');
  const reviews = source.reviews ?? [];
  const rating = source.rating ?? (() => {
    const rated = reviews.filter((r) => r.rating != null).map((r) => r.rating!);
    return rated.length > 0 ? Math.round((rated.reduce((a, b) => a + b, 0) / rated.length) * 10) / 10 : undefined;
  })();

  const filtered = useMemo(() => {
    if (!query.trim()) return reviews;
    const q = query.toLowerCase();
    return reviews.filter(
      (r) =>
        r.text?.toLowerCase().includes(q) ||
        r.author?.toLowerCase().includes(q),
    );
  }, [reviews, query]);

  return (
    <>
      {/* Dark header with platform identity */}
      <div className="px-3 pt-3 pb-2.5" style={{ background: 'var(--color-ink)' }}>
        <div className="flex items-center gap-2.5">
          {['habitissimo', 'houzz', 'cronoshare', 'hogami'].includes(source.platform?.toLowerCase()) ? (
            <PlatformLogo
              platform={source.platform.toLowerCase() as 'habitissimo' | 'houzz' | 'cronoshare' | 'hogami'}
              size="md"
              variant="card"
            />
          ) : source.platform_logo ? (
            <img src={source.platform_logo} alt="" className="w-8 h-8 rounded-md object-contain shrink-0" />
          ) : (
            <div
              className="w-8 h-8 rounded-md shrink-0 flex items-center justify-center text-[11px] font-bold"
              style={{ background: 'rgba(255,255,255,.1)', color: 'var(--color-cream)' }}
            >
              {source.platform.charAt(0).toUpperCase()}
            </div>
          )}
          <div>
            <div className="text-[15px] font-semibold" style={{ color: 'var(--color-cream)' }}>
              {source.platform}
            </div>
            <div className="flex items-center gap-1.5">
              {rating != null && <Stars rating={rating} size={11} />}
              <span className="text-[11px]" style={{ color: 'var(--color-muted)' }}>
                · {reviews.length} review{reviews.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
        </div>
        {source.platform_url && (
          <a
            href={source.platform_url.startsWith('http') ? source.platform_url : `https://${source.platform_url}`}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 text-[10px] mt-1.5 ml-[42px]"
            style={{ color: 'var(--color-terracotta)' }}
          >
            <ExternalLink size={9} />
            {source.platform_url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
          </a>
        )}
      </div>

      <BackBar label={t('profile_back_to_profile')} onBack={onBack} />

      {/* Search bar */}
      <div className="px-4 pt-2.5 pb-1" style={{ background: 'var(--color-cream)' }}>
        <div
          className="flex items-center gap-2 rounded-sm px-3 py-2"
          style={{ border: '1px solid var(--color-border)', background: '#fff' }}
        >
          <Search size={14} style={{ color: 'var(--color-muted)' }} />
          <Input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={t('profile_search_reviews')}
            className="flex-1 text-[13px] bg-transparent outline-none placeholder:text-stone-400"
          />
          {query && (
            <Button type="button" onClick={() => setQuery('')} className="text-stone-400">
              <X size={14} />
            </Button>
          )}
        </div>
        {query && (
          <div className="text-[11px] mt-1.5" style={{ color: 'var(--color-muted)' }}>
            {filtered.length} {t('profile_results')}
          </div>
        )}
      </div>

      {/* Review list */}
      <div className="flex-1 px-4 pb-4" style={{ background: 'var(--color-cream)' }}>
        {filtered.length === 0 ? (
          <p className="text-center text-[13px] pt-8" style={{ color: 'var(--color-muted)' }}>
            {query ? t('profile_no_reviews_match') : t('profile_no_reviews_yet')}
          </p>
        ) : (
          filtered.map((rev, i) => (
            <div
              key={i}
              className="py-3"
              style={{ borderBottom: i < filtered.length - 1 ? '1px solid var(--color-border)' : 'none' }}
            >
              <div className="flex flex-wrap items-center gap-1.5 mb-1">
                {rev.author && (
                  <span className="text-[13px] font-semibold" style={{ color: 'var(--color-ink)' }}>
                    {rev.author}
                  </span>
                )}
                {rev.rating != null && <Stars rating={rev.rating} size={11} />}
                {rev.date && (
                  <span className="text-[10px] ml-auto" style={{ color: 'var(--color-muted)' }}>
                    {rev.date}
                  </span>
                )}
              </div>
              {rev.text && (
                <p className="text-[13px] leading-relaxed" style={{ color: 'var(--color-stone)' }}>
                  {rev.text}
                </p>
              )}
            </div>
          ))
        )}
      </div>
    </>
  );
}

// ── Project view (full case study) ──────────────────────────────────────

function ProjectView({
  project,
  onBack,
  onViewPhoto,
}: {
  project: ProfileProject;
  onBack: () => void;
  onViewPhoto: (url: string) => void;
}) {
  const { t } = useTranslation();
  const images = project.images ?? [];
  return (
    <>
      {/* Hero image */}
      {images[0] && (
        <Button type="button" onClick={() => onViewPhoto(images[0])} className="w-full">
          <img src={images[0]} alt="" className="w-full aspect-[16/9] object-cover" />
        </Button>
      )}

      <BackBar label={t('profile_back_to_profile')} onBack={onBack} />

      <div className="flex-1 px-4 pt-3 pb-4" style={{ background: 'var(--color-cream)' }}>
        <h3 className="font-display text-[17px] font-semibold mb-1" style={{ color: 'var(--color-ink)' }}>
          {project.title || t('profile_project_fallback')}
        </h3>

        {project.source && (
          <div className="flex items-center gap-1.5 mb-3">
            <span className="text-[11px]" style={{ color: 'var(--color-muted)' }}>
              {t('profile_found_on')} <strong style={{ color: 'var(--color-stone)' }}>{project.source}</strong>
            </span>
            {project.url && (
              <a
                href={project.url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-0.5 text-[11px]"
                style={{ color: 'var(--color-terracotta)' }}
              >
                <ExternalLink size={9} /> {t('profile_view_original')}
              </a>
            )}
          </div>
        )}

        {project.description && (
          <p className="text-[13px] leading-relaxed whitespace-pre-wrap mb-4" style={{ color: 'var(--color-stone)' }}>
            {project.description}
          </p>
        )}

        {/* Image grid */}
        {images.length > 1 && (
          <div className="grid grid-cols-2 gap-1.5">
            {images.map((url, i) => (
              <Button
                key={i}
                type="button"
                onClick={() => onViewPhoto(url)}
                className="rounded-sm overflow-hidden"
                style={{ border: '1px solid var(--color-border)' }}
              >
                <img src={url} alt="" className="w-full aspect-square object-cover" loading="lazy" />
              </Button>
            ))}
          </div>
        )}
      </div>
    </>
  );
}
