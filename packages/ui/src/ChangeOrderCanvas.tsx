import { useTranslation } from 'react-i18next';
import type { ChangeOrderUpdate } from './types';
import { Button } from './primitives';

/**
 * ChangeOrderCanvas — the fourth Leo Document canvas.
 *
 * A change order is a mid-job scope addition: something unexpected found during
 * work that needs approval before the tradesperson can continue. It always
 * includes: what changed, why, line items, optional photos from site, and a
 * market fairness indicator.
 *
 * Two display modes:
 * - 'full'    (default) — standalone card matching the H5 "Know about changes" section
 *             in homeowners.html. Used in chat preview / Canvas.tsx page.
 * - 'compact' — single row for embedding inside MilestoneList or a job progress view.
 *             Shows title + total + status badge only.
 *
 * React: import { ChangeOrderCanvas } from '@scope/ui'
 * Static HTML reference: H5 "Know about changes before you're billed" in homeowners.html
 */

interface ChangeOrderCanvasProps {
  co: ChangeOrderUpdate | null;
  mode?: 'full' | 'compact';
  onApprove?: () => void;
  onGetHelp?: () => void;
}

const fmt = (n: number) => `€${n.toLocaleString('es-ES', { minimumFractionDigits: 0, maximumFractionDigits: 2 })}`;

const total = (co: ChangeOrderUpdate) =>
  co.line_items.reduce((s, i) => s + i.amount, 0);

/* ─── Status badge ── */
const ChangeOrderStatusBadge = ({ status }: { status: ChangeOrderUpdate['status'] }) => {
  const { t } = useTranslation();
  const map = {
    pending:  { label: t('co_status_pending'),  bg: 'rgba(245,158,11,.12)', color: '#92400E' },
    approved: { label: t('co_status_approved'), bg: 'rgba(16,185,129,.12)', color: '#065F46' },
    rejected: { label: t('co_status_rejected'), bg: 'rgba(239,68,68,.1)',   color: '#991B1B' },
  } as const;
  const s = map[status] ?? map.pending;
  return (
    <span
      style={{
        fontSize: 9,
        fontWeight: 700,
        padding: '2px 8px',
        borderRadius: 'var(--r-pill, 999px)',
        textTransform: 'uppercase',
        letterSpacing: '.04em',
        background: s.bg,
        color: s.color,
      }}
    >
      {s.label}
    </span>
  );
};

/* ─── Market fairness bar ── */
const MarketBar = ({ low, high, value }: { low: number; high: number; value: number }) => {
  const { t } = useTranslation();
  const range = high - low;
  const pct = Math.max(0, Math.min(100, ((value - low) / range) * 100));
  const inRange = value >= low && value <= high;
  return (
    <div>
      <div
        style={{
          fontSize: 9,
          color: 'var(--muted, #A8A29E)',
          marginBottom: 3,
          fontWeight: 700,
          letterSpacing: '.05em',
          textTransform: 'uppercase',
        }}
      >
        {t('co_fair_market_range')}
      </div>
      <div
        style={{
          height: 5,
          background: 'var(--cream-dk, #F0EBE3)',
          borderRadius: 'var(--radius-xs)',
          position: 'relative',
        }}
      >
        <div
          style={{
            position: 'absolute',
            height: '100%',
            background: 'rgba(17,94,89,.12)',
            borderRadius: 'var(--radius-xs)',
            left: '10%',
            width: '60%',
          }}
        />
        <div
          style={{
            position: 'absolute',
            top: -3,
            left: `${pct}%`,
            width: 11,
            height: 11,
            borderRadius: '50%',
            background: 'var(--color-terracotta)',
            border: '2px solid var(--card, #fff)',
            transform: 'translateX(-50%)',
            boxShadow: '0 1px 4px rgba(218,101,77,.3)',
          }}
        />
      </div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          fontSize: 10,
          color: 'var(--muted, #A8A29E)',
          marginTop: 2,
        }}
      >
        <span>{fmt(low)}</span>
        <span>{fmt(high)}</span>
      </div>
      {inRange && (
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 8px',
            background: 'rgba(0,128,128,.06)',
            borderRadius: 'var(--r, 8px)',
            marginTop: 8,
          }}
        >
          <svg viewBox="0 0 24 24" width={12} height={12} style={{ fill: 'var(--color-teal)', flexShrink: 0 }}>
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
          </svg>
          <span style={{ fontSize: 10, color: 'var(--color-teal)', fontWeight: 600 }}>
            {t('co_price_in_range')}
          </span>
        </div>
      )}
    </div>
  );
};

/* ─── Compact row (for MilestoneList / progress views) ── */
const CompactRow = ({ co }: { co: ChangeOrderUpdate }) => {
  const { t } = useTranslation();
  return (
  <div
    style={{
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      padding: '10px 14px',
      background: 'var(--card, #fff)',
      border: '1px solid var(--border, var(--color-border))',
      borderLeft: '3px solid var(--amber, #D97706)',
      borderRadius: 'var(--r, 8px)',
    }}
  >
    {/* Amber + icon */}
    <div
      style={{
        width: 20,
        height: 20,
        borderRadius: '50%',
        background: 'var(--amber, #D97706)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexShrink: 0,
      }}
    >
      <svg viewBox="0 0 24 24" width={10} height={10} style={{ stroke: '#fff', fill: 'none', strokeWidth: 2.5, strokeLinecap: 'round' }}>
        <path d="M12 5v14M5 12h14" />
      </svg>
    </div>

    <div style={{ flex: 1, minWidth: 0 }}>
      <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--color-ink)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
        {co.title}
      </div>
      <div style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--amber, #D97706)', marginTop: 1 }}>
        {t('co_add_on')}
      </div>
    </div>

    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 3, flexShrink: 0 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--color-ink)' }}>
        {fmt(total(co))}
      </div>
      <ChangeOrderStatusBadge status={co.status} />
    </div>
  </div>
  );
};

/* ─── Full card ── */
const FullCard = ({ co, onApprove, onGetHelp }: { co: ChangeOrderUpdate; onApprove?: () => void; onGetHelp?: () => void }) => {
  const { t } = useTranslation();
  const jobTotal = total(co);

  return (
    <div
      style={{
        background: 'var(--card, #fff)',
        border: '1px solid var(--border, var(--color-border))',
        borderLeft: '3px solid var(--amber, #D97706)',
        borderRadius: 'var(--r, 8px)',
        padding: '12px 14px',
        maxWidth: 380,
      }}
    >
      {/* Header row */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <div
            style={{
              width: 20,
              height: 20,
              borderRadius: '50%',
              background: 'var(--amber, #D97706)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg viewBox="0 0 24 24" width={10} height={10} style={{ stroke: '#fff', fill: 'none', strokeWidth: 2.5, strokeLinecap: 'round' }}>
              <path d="M12 5v14M5 12h14" />
            </svg>
          </div>
          <span style={{ fontSize: 9, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--amber, #D97706)' }}>
            {t('co_add_on')}
          </span>
        </div>
        <ChangeOrderStatusBadge status={co.status} />
      </div>

      {/* Title + reason */}
      <div style={{ fontFamily: 'var(--serif, Georgia, serif)', fontSize: 14, fontWeight: 600, color: 'var(--color-ink)', marginBottom: 3 }}>
        {co.title}
      </div>
      <p style={{ fontSize: 12, color: 'var(--color-stone)', lineHeight: 1.4, marginBottom: co.photo_urls?.length ? 8 : 10 }}>
        {co.reason}
      </p>

      {/* Photo evidence */}
      {co.photo_urls?.length ? (
        <div style={{ display: 'flex', gap: 4, marginBottom: 10 }}>
          {co.photo_urls.slice(0, 3).map((url, i) => (
            <div
              key={i}
              style={{
                flex: i === 0 ? '0 0 56px' : 1,
                height: 56,
                borderRadius: 'var(--r, 8px)',
                overflow: 'hidden',
                border: '1px solid var(--border, var(--color-border))',
                position: 'relative',
              }}
            >
              <img src={url} alt={`Evidence ${i + 1}`} style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
              {i === 1 && co.contractor_name && (
                <div style={{ position: 'absolute', bottom: 3, right: 3, fontSize: 8, fontWeight: 600, background: 'rgba(0,0,0,.6)', color: '#fff', padding: '1px 5px', borderRadius: 'var(--radius-xs)' }}>
                  Photo from {co.contractor_name.split(' ')[0]}
                </div>
              )}
            </div>
          ))}
        </div>
      ) : null}

      {/* Line items */}
      <div style={{ fontSize: 11, marginBottom: 8 }}>
        {co.line_items.map((item, i) => (
          <div
            key={i}
            style={{
              display: 'flex',
              justifyContent: 'space-between',
              padding: '3px 0',
              borderBottom: i < co.line_items.length - 1 ? '1px solid rgba(0,0,0,.04)' : undefined,
            }}
          >
            <span style={{ color: 'var(--color-stone)' }}>{item.description}</span>
            <span style={{ color: 'var(--color-ink)', fontWeight: 600 }}>{fmt(item.amount)}</span>
          </div>
        ))}
        <div style={{ display: 'flex', justifyContent: 'space-between', padding: '3px 0', borderTop: '1px solid rgba(0,0,0,.06)', marginTop: 1 }}>
          <span style={{ color: 'var(--color-ink)', fontWeight: 700 }}>{t('co_total')}</span>
          <span style={{ color: 'var(--color-ink)', fontWeight: 700 }}>{fmt(jobTotal)}</span>
        </div>
      </div>

      {/* Fair market range */}
      {co.market_range_low != null && co.market_range_high != null && (
        <div style={{ marginBottom: 12 }}>
          <MarketBar low={co.market_range_low} high={co.market_range_high} value={jobTotal} />
        </div>
      )}

      {/* Action buttons */}
      <div style={{ display: 'flex', gap: 8 }}>
        <Button
          type="button"
          onClick={onApprove}
          style={{
            flex: 1,
            padding: 10,
            background: 'var(--color-teal)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--r, 8px)',
            fontWeight: 600,
            fontSize: 13,
            fontFamily: 'var(--sans, sans-serif)',
            cursor: 'pointer',
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 6,
          }}
        >
          <svg width={14} height={14} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round" aria-hidden>
            <polyline points="20 6 9 17 4 12" />
          </svg>
          {t('co_approve')}
        </Button>
        <Button
          type="button"
          onClick={onGetHelp}
          style={{
            flex: 1,
            padding: 10,
            background: 'var(--card, #fff)',
            color: 'var(--color-stone)',
            border: '1px solid var(--border, var(--color-border))',
            borderRadius: 'var(--r, 8px)',
            fontWeight: 600,
            fontSize: 13,
            fontFamily: 'var(--sans, sans-serif)',
            cursor: 'pointer',
          }}
        >
          {t('co_get_help')}
        </Button>
      </div>
    </div>
  );
};

/* ─── Export ── */
export function ChangeOrderCanvas({ co, mode = 'full', onApprove, onGetHelp }: ChangeOrderCanvasProps) {
  if (!co) return null;
  if (mode === 'compact') return <CompactRow co={co} />;
  return <FullCard co={co} onApprove={onApprove} onGetHelp={onGetHelp} />;
}
