import React from 'react';
import { useTranslation } from 'react-i18next';
import type { QuoteContingencyDraft, QuoteUpdate } from './types';
import { ChangeOrderCanvas } from './ChangeOrderCanvas';

/**
 * ScopeCanvas — the Leo quote document.
 *
 * Structure:
 *   1. Dark header (title, status, location)
 *   2. Description
 *   3. Work phases (single merged section — NO duplicate payment schedule)
 *      · Materials upfront row first (if any)
 *      · Phase rows: number, description, duration, amount
 *      · Proportional payment bar
 *   4. Financial summary: subtotal → IVA → Leo service fee → total
 *   5. Escrow badge
 *   6. Terms + Leo contract link
 */
export default function QuoteCanvas({ scope: rawScope }: { scope: Record<string, unknown> | null }) {
  const scope = rawScope as QuoteUpdate | null;
  const { t } = useTranslation();

  if (!scope || (!scope.title && !scope.description)) {
    return (
      <div className="flex items-center justify-center py-16 px-6">
        <p className="text-muted text-sm leading-relaxed text-center">
          {t('scope_empty_state')}
        </p>
      </div>
    );
  }

  const phases = scope.line_items ?? [];
  const materialsUpfront = scope.materials_upfront ?? 0;
  const ivaRate = scope.iva_rate;
  const feePct = scope.service_fee_percent || 0;

  // Financial totals — mirror backend _compute_scope_financials exactly
  const labourSubtotal = phases.reduce((s, li) => s + (li.amount || 0), 0);
  const workTotal = labourSubtotal + materialsUpfront;
  const feeAmount = labourSubtotal * feePct / 100;
  const ivaAmount = ivaRate ? (workTotal * ivaRate) / 100 : 0;
  const grandTotal = workTotal + feeAmount + ivaAmount;

  const fmtEur = (n: number) =>
    new Intl.NumberFormat('es-ES', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: n % 1 === 0 ? 0 : 2,
      maximumFractionDigits: 2,
    }).format(n);

  const LABEL: React.CSSProperties = {
    color: '#78716C',
    letterSpacing: '.06em',
    fontSize: 10,
    fontWeight: 700,
    textTransform: 'uppercase',
  };

  const statusLabel: Record<string, string> = {
    draft: t('scope_status_draft'),
    sent: t('scope_status_sent'),
    approved: t('scope_status_approved'),
    complete: t('scope_status_complete'),
  };

  // Contingency drafts by phase index
  const drafts: QuoteContingencyDraft[] = scope.contingency_drafts ?? [];
  const byPhase = new Map<number, QuoteContingencyDraft[]>();
  for (const d of drafts) {
    const arr = byPhase.get(d.after_phase_index) ?? [];
    arr.push(d);
    byPhase.set(d.after_phase_index, arr);
  }

  // Payment bar segments
  const barTotal = grandTotal || 1;
  const barSegments: { label: string; amount: number; color: string }[] = [];
  if (materialsUpfront > 0) {
    barSegments.push({ label: 'Mat.', amount: materialsUpfront, color: '#0D9488' });
  }
  const phaseColors = ['#C65D3A', '#A84E30', '#E07A5F', '#B5654C', '#D4785A'];
  phases.forEach((li, i) => {
    barSegments.push({
      label: `F${i + 1}`,
      amount: li.amount || 0,
      color: phaseColors[i % phaseColors.length],
    });
  });
  // Add Leo fee as last segment
  if (feeAmount > 0) {
    barSegments.push({ label: 'Leo', amount: feeAmount, color: '#78716C' });
  }

  return (
    <div className="flex flex-col overflow-y-auto">

      {/* ── Dark header ──────────────────────────────────────────── */}
      <div className="px-4 pt-4 pb-3.5" style={{ background: '#1C1917' }}>
        <h3
          className="font-display font-semibold leading-snug mb-1"
          style={{ color: '#FAFAF9', fontSize: 17 }}
        >
          {scope.title}
        </h3>
        <div style={{ color: 'rgba(255,255,255,.45)', fontSize: 11 }}>
          {statusLabel[scope.status] || scope.status}
          {scope.location ? ` · ${scope.location}` : ''}
          {scope.created_at ? ` · ${scope.created_at}` : ''}
        </div>
      </div>

      {/* ── Cream body ───────────────────────────────────────────── */}
      <div className="px-4 pt-4 pb-6" style={{ background: '#FAF8F4' }}>

        {/* 1 — Description */}
        {scope.description ? (
          <div className="mb-4">
            <div style={LABEL} className="mb-1.5">
              {t('scope_description', 'Descripción')}
            </div>
            <p style={{ color: '#57534E', fontSize: 13, lineHeight: 1.55 }}>
              {scope.description}
            </p>
          </div>
        ) : null}

        {/* 2 — Work phases (single unified section) */}
        {(phases.length > 0 || materialsUpfront > 0) && (
          <div className="mb-4">
            <div style={LABEL} className="mb-2">
              {t('scope_phases', 'Fases del trabajo')}
            </div>

            {/* Contingency drafts before first phase */}
            {(byPhase.get(-1) ?? []).map((d, di) => (
              <div key={`pre-${di}`} className="mb-2">
                <ChangeOrderCanvas
                  co={{ title: d.title, reason: d.reason, line_items: d.line_items, status: 'pending', market_range_low: d.market_range_low, market_range_high: d.market_range_high }}
                  mode="compact"
                />
              </div>
            ))}

            {/* Materials upfront — first item if present */}
            {materialsUpfront > 0 && (
              <div
                className="flex items-start gap-3 py-2.5 border-b"
                style={{ borderColor: '#E7E1D8' }}
              >
                <div
                  className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                  style={{ background: 'rgba(13,148,136,.12)' }}
                >
                  <span style={{ color: '#0D9488', fontSize: 10, fontWeight: 700 }}>M</span>
                </div>
                <div className="flex-1 min-w-0">
                  <div style={{ color: '#1C1917', fontSize: 13, fontWeight: 600 }}>
                    {t('scope_materials_upfront_label', 'Materiales y compras')}
                  </div>
                  <div style={{ color: '#A8A29E', fontSize: 11, marginTop: 1 }}>
                    {t('scope_materials_upfront_trigger', 'Pago inicial · antes de empezar')}
                  </div>
                </div>
                <div className="shrink-0 text-right">
                  <div style={{ color: '#1C1917', fontSize: 13, fontWeight: 700 }}>
                    {fmtEur(materialsUpfront)}
                  </div>
                </div>
              </div>
            )}

            {/* Phase rows */}
            {phases.map((li, i) => (
              <React.Fragment key={i}>
                <div
                  className="flex items-start gap-3 py-2.5 border-b"
                  style={{ borderColor: '#E7E1D8' }}
                >
                  {/* Phase number badge */}
                  <div
                    className="w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5"
                    style={{ background: 'rgba(198,93,58,.12)' }}
                  >
                    <span style={{ color: '#C65D3A', fontSize: 10, fontWeight: 700 }}>{i + 1}</span>
                  </div>

                  {/* Description + duration */}
                  <div className="flex-1 min-w-0">
                    <div
                      style={{ color: '#1C1917', fontSize: 13, lineHeight: 1.4, wordBreak: 'break-word' }}
                    >
                      {li.description}
                    </div>
                    <div style={{ color: '#A8A29E', fontSize: 11, marginTop: 2 }}>
                      {li.duration_label ? `${li.duration_label} · ` : ''}
                      {t('scope_on_completion', 'Al completar')}
                    </div>
                  </div>

                  {/* Amount */}
                  <div className="shrink-0 text-right" style={{ minWidth: 56 }}>
                    <div style={{ color: '#1C1917', fontSize: 13, fontWeight: 700 }}>
                      {fmtEur(li.amount)}
                    </div>
                  </div>
                </div>

                {/* Contingency drafts after this phase */}
                {(byPhase.get(i) ?? []).map((d, di) => (
                  <div key={`draft-${i}-${di}`} className="my-2">
                    <ChangeOrderCanvas
                      co={{ title: d.title, reason: d.reason, line_items: d.line_items, status: 'pending', market_range_low: d.market_range_low, market_range_high: d.market_range_high }}
                      mode="compact"
                    />
                  </div>
                ))}
              </React.Fragment>
            ))}

            {/* Proportional payment bar */}
            {barSegments.length > 0 && barTotal > 0 && (
              <div className="mt-3">
                {/* Bar */}
                <div className="flex rounded-lg overflow-hidden h-2.5 gap-px">
                  {barSegments.map((seg, i) => (
                    <div
                      key={i}
                      style={{
                        width: `${(seg.amount / barTotal) * 100}%`,
                        background: seg.color,
                        minWidth: seg.amount > 0 ? 3 : 0,
                      }}
                    />
                  ))}
                </div>
                {/* Labels */}
                <div className="flex gap-3 mt-2 flex-wrap">
                  {barSegments.map((seg, i) => (
                    <div key={i} className="flex items-center gap-1">
                      <span
                        className="w-2 h-2 rounded-sm shrink-0"
                        style={{ background: seg.color }}
                      />
                      <span style={{ color: '#A8A29E', fontSize: 10 }}>
                        {seg.label} {fmtEur(seg.amount)}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}

        {/* 3 — Financial summary */}
        {(phases.length > 0 || materialsUpfront > 0) && (
          <div className="mb-4 rounded-xl overflow-hidden" style={{ border: '1px solid #E7E1D8' }}>
            <div className="px-3.5 py-3 space-y-2" style={{ background: '#FFFFFF60' }}>

              {/* Mano de obra */}
              <div className="flex justify-between items-center">
                <span style={{ color: '#78716C', fontSize: 12 }}>
                  {t('scope_labour', 'Mano de obra')}
                </span>
                <span style={{ color: '#57534E', fontSize: 12 }}>
                  {fmtEur(labourSubtotal)}
                </span>
              </div>

              {/* Materials (if any) */}
              {materialsUpfront > 0 && (
                <div className="flex justify-between items-center">
                  <span style={{ color: '#78716C', fontSize: 12 }}>
                    {t('scope_materials_short', 'Materiales')}
                  </span>
                  <span style={{ color: '#57534E', fontSize: 12 }}>
                    {fmtEur(materialsUpfront)}
                  </span>
                </div>
              )}

              {/* IVA */}
              {ivaRate && ivaAmount > 0 && (
                <div className="flex justify-between items-center">
                  <span style={{ color: '#78716C', fontSize: 12 }}>
                    IVA ({ivaRate}%)
                  </span>
                  <span style={{ color: '#57534E', fontSize: 12 }}>
                    {fmtEur(ivaAmount)}
                  </span>
                </div>
              )}

              {/* Leo service fee — separate, prominent */}
              {feePct > 0 && feeAmount > 0 && (
                <div
                  className="flex justify-between items-center pt-2 mt-1"
                  style={{ borderTop: '1px solid #E7E1D8' }}
                >
                  <div>
                    <span style={{ color: '#78716C', fontSize: 12 }}>
                      {t('scope_service_fee_label', 'Comisión Leo')} ({feePct}%)
                    </span>
                    <div style={{ color: '#A8A29E', fontSize: 10, marginTop: 1 }}>
                      {t('scope_service_fee_note', 'Gestión de pago · cobrada al inicio')}
                    </div>
                  </div>
                  <span style={{ color: '#78716C', fontSize: 12 }}>
                    {fmtEur(feeAmount)}
                  </span>
                </div>
              )}
            </div>

            {/* Total row */}
            <div
              className="flex justify-between items-center px-3.5 py-3"
              style={{ background: '#1C1917' }}
            >
              <span
                className="font-semibold"
                style={{ color: '#FAF8F4', fontSize: 14 }}
              >
                Total{ivaRate ? ` (IVA inc.)` : ''}
              </span>
              <span
                className="font-bold"
                style={{ color: '#FAF8F4', fontSize: 16 }}
              >
                {fmtEur(grandTotal)}
              </span>
            </div>
          </div>
        )}

        {/* 4 — Escrow protection */}
        {(phases.length > 0 || materialsUpfront > 0) && (
          <div
            className="flex items-center gap-2 px-3.5 py-2.5 rounded-lg mb-4"
            style={{ background: 'rgba(13,148,136,.07)', border: '1px solid rgba(13,148,136,.2)' }}
          >
            <svg width="14" height="14" viewBox="0 0 24 24" style={{ stroke: '#0D9488', fill: 'none', strokeWidth: 2, flexShrink: 0 }}>
              <rect x="3" y="11" width="18" height="11" rx="2" />
              <path d="M7 11V7a5 5 0 0110 0v4" />
            </svg>
            <div>
              <span style={{ color: '#0D9488', fontSize: 12, fontWeight: 600 }}>
                {t('scope_payment_protected', 'Pagos protegidos por custodia')}
              </span>
              <div style={{ color: '#A8A29E', fontSize: 10, marginTop: 1 }}>
                {t('scope_escrow_note', 'El dinero se libera fase a fase, cuando confirmas que el trabajo está hecho.')}
              </div>
            </div>
          </div>
        )}

        {/* 5 — Terms */}
        {scope.terms && scope.terms.length > 0 && (
          <div>
            <div style={LABEL} className="mb-1.5">
              {t('scope_terms', 'Condiciones')}
            </div>
            <ul className="space-y-1 mb-2.5 pl-4 list-disc" style={{ color: '#57534E', fontSize: 12, lineHeight: 1.5 }}>
              {scope.terms.map((term, i) => (
                <li key={i}>{term}</li>
              ))}
            </ul>
            <a
              href="https://leo.casa/terms"
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: '#C65D3A', fontSize: 12, fontWeight: 600, textDecoration: 'underline', textUnderlineOffset: 3 }}
            >
              {t('scope_contract_link', 'Ver contrato de construcción Leo →')}
            </a>
          </div>
        )}

      </div>
    </div>
  );
}
