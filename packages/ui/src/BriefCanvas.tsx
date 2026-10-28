import { useTranslation } from 'react-i18next';
import type { BriefUpdate } from './types';

export default function BriefCanvas({ b, photos = [] }: { b: BriefUpdate | null; photos?: string[] }) {
  const { t } = useTranslation();

  if (!b || (!b.title && !b.description)) {
    return (
      <div className="flex items-center justify-center h-full">
        <p className="text-muted text-sm leading-relaxed text-center px-6">
          {t('brief_empty_state')}
        </p>
      </div>
    );
  }

  const metaItems: { label: string; value: string }[] = [];
  if (b.urgency) metaItems.push({ label: t('brief_timing'), value: b.urgency });
  if (b.materials_mentioned) metaItems.push({ label: t('brief_materials'), value: b.materials_mentioned });
  if (b.measurements) metaItems.push({ label: t('brief_measurements'), value: b.measurements });
  if (b.budget_indication) metaItems.push({ label: t('brief_budget'), value: b.budget_indication });

  const displayPhotos = photos.slice(0, 4);
  const overflowCount = photos.length - 3;

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Dark header — category + title + location */}
      <div className="px-4 pt-3.5 pb-3" style={{ background: 'var(--color-ink)' }}>
        <div className="flex items-center gap-2 mb-2.5">
          <span
            className="text-[10px] font-semibold uppercase tracking-wide px-2 py-0.5 rounded-md"
            style={{ background: 'rgba(17,94,89,.35)', color: 'var(--color-teal-lt)', letterSpacing: '.04em' }}
          >
            {b.title?.split(' ')[0] || t('brief_job_fallback')}
          </span>
          <span className="text-[11px]" style={{ color: 'var(--color-muted)' }}>{t('brief_just_now')}</span>
        </div>
        <h3
          className="font-display text-[17px] font-semibold mb-1.5"
          style={{ color: 'var(--color-cream)' }}
        >
          {b.title || t('brief_title_fallback')}
        </h3>
        {b.location ? (
          <div className="flex items-center gap-1.5 text-xs" style={{ color: 'var(--color-muted)' }}>
            <span
              className="w-2.5 h-2.5 rounded-full shrink-0"
              style={{
                background: 'rgba(218,101,77,.25)',
                border: '2px solid var(--color-terracotta)',
                boxSizing: 'border-box',
              }}
              aria-hidden
            />
            {b.location}
          </div>
        ) : null}
      </div>

      {/* Light body */}
      <div className="px-4 pt-3.5 pb-4 flex-1" style={{ background: 'var(--color-cream)' }}>
        {b.description ? (
          <p className="text-[13px] leading-relaxed mb-3 whitespace-pre-wrap" style={{ color: 'var(--color-stone)' }}>
            {b.description}
          </p>
        ) : null}

        {/* Meta fields */}
        {metaItems.length > 0 ? (
          <div className="flex flex-wrap gap-x-4 gap-y-1.5 mb-3">
            {metaItems.map((item) => (
              <div key={item.label} className="text-xs">
                <span style={{ color: 'var(--color-muted)' }}>{item.label}: </span>
                <span className="font-medium" style={{ color: 'var(--color-ink)' }}>{item.value}</span>
              </div>
            ))}
          </div>
        ) : null}

        {/* Photo thumbnails */}
        {displayPhotos.length > 0 ? (
          <div className="flex gap-1.5 mb-3.5">
            {displayPhotos.slice(0, 3).map((url, i) => (
              <div
                key={i}
                className="w-[72px] h-[72px] rounded-md overflow-hidden shrink-0"
                style={{ border: '1px solid var(--color-border)' }}
              >
                <img src={url} alt="" className="w-full h-full object-cover" />
              </div>
            ))}
            {overflowCount > 0 ? (
              <div
                className="w-[72px] h-[72px] rounded-md flex items-center justify-center text-xs font-semibold shrink-0"
                style={{ background: 'var(--color-cream-dark)', border: '1px solid var(--color-border)', color: 'var(--color-stone)' }}
              >
                +{overflowCount}
              </div>
            ) : null}
          </div>
        ) : null}

        {/* Map placeholder */}
        <div
          className="rounded-md overflow-hidden relative"
          style={{ border: '1px solid var(--color-border)', height: '110px', background: 'var(--color-cream-dark)' }}
        >
          {b.location ? (
            <>
              <div className="absolute inset-0 flex items-center justify-center">
                <div
                  className="w-20 h-20 rounded-full"
                  style={{
                    background: 'rgba(218,101,77,.15)',
                    boxShadow: '0 0 0 2px rgba(218,101,77,.4)',
                  }}
                />
              </div>
              <div
                className="absolute bottom-1.5 left-2 text-[9px] font-semibold px-1.5 py-0.5 rounded-sm"
                style={{ color: 'var(--color-stone)', background: 'rgba(255,255,255,.9)' }}
              >
                {b.location}
              </div>
              <div
                className="absolute bottom-1.5 right-2 text-[9px] px-1.5 py-0.5 rounded-sm"
                style={{ color: 'var(--color-muted)', background: 'rgba(255,255,255,.9)' }}
              >
                {t('brief_approximate')}
              </div>
            </>
          ) : (
            <div className="flex items-center justify-center h-full">
              <span className="text-xs" style={{ color: 'var(--color-muted)' }}>{t('brief_location_placeholder')}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
