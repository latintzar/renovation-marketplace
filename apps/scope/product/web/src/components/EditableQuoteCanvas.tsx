/**
 * EditableQuoteCanvas — same visual structure as QuoteCanvas but editable.
 *
 * Sections: Description → Milestones (with duration) → Materials upfront → Payment schedule.
 *
 * NOT part of @scope/ui — scope-builder-specific, lives in apps/web.
 */

import React from 'react';
import { Button, ChangeOrderCanvas, Input, Textarea, type ChangeOrderUpdate } from '@scope/ui';
import type { QuoteContingencyDraft, QuoteUpdate } from '../lib/api';
import { computeQuoteTotals, eurFromEuros } from '../lib/utils';

interface Props {
  scope: QuoteUpdate;
  onChange: (updated: QuoteUpdate) => void;
  lang?: 'es' | 'en';
}

function draftToChangeOrder(d: QuoteContingencyDraft): ChangeOrderUpdate {
  return {
    title: d.title,
    reason: d.reason,
    line_items: d.line_items,
    status: 'pending',
    market_range_low: d.market_range_low,
    market_range_high: d.market_range_high,
  };
}

const LABEL: React.CSSProperties = { color: 'var(--color-muted)', letterSpacing: '.06em' };

const INPUT_BASE =
  'w-full bg-transparent border-b border-border focus:border-terracotta outline-none py-1 text-[13px] text-ink transition-colors placeholder-muted';

const AMOUNT_INPUT =
  'bg-transparent border-b border-border focus:border-terracotta outline-none py-1 text-[13px] text-ink text-right w-24 transition-colors';

// Parse "2 days" / "1 week" / "3 días" (legacy Spanish) → { n: '2', unit: 'days' | 'weeks' }
function parseDuration(label?: string): { n: string; unit: 'days' | 'weeks' } {
  if (!label) return { n: '', unit: 'days' };
  const isWeek = /semana|week/i.test(label);
  const match = label.match(/(\d+)/);
  return { n: match?.[1] ?? '', unit: isWeek ? 'weeks' : 'days' };
}

function buildDuration(n: string, unit: 'days' | 'weeks'): string {
  const num = parseInt(n);
  if (!n || isNaN(num) || num <= 0) return '';
  if (unit === 'weeks') return num === 1 ? '1 week' : `${num} weeks`;
  return num === 1 ? '1 day' : `${num} days`;
}

/** Inline contingency draft card between milestones. */
function ContingencyDraftRow({
  draft,
  lang,
  onRemove,
}: {
  draft: QuoteContingencyDraft;
  lang: 'es' | 'en';
  onRemove: () => void;
}) {
  return (
    <div className="relative mb-3 mt-1">
      <ChangeOrderCanvas co={draftToChangeOrder(draft)} mode="compact" />
      <Button variant="danger" className="absolute top-1 right-1 w-5 h-5 rounded-full text-muted hover:text-red-400 text-[15px] leading-none" type="button"
        onClick={onRemove}
        title={lang === 'es' ? 'Quitar variación' : 'Remove contingency'}>×</Button>
    </div>
  );
}

export default function EditableQuoteCanvas({ scope, onChange, lang = 'en' }: Props) {
  const milestones = scope.line_items ?? [];
  const drafts = scope.contingency_drafts ?? [];
  const { labour: milestonesSubtotal, materials: materialsUpfront, fee: feeAmount, iva: ivaAmount, total: grandTotal } = computeQuoteTotals(scope);
  const ivaRate = scope.iva_rate;
  const workTotal = milestonesSubtotal + materialsUpfront;

  const fmtEur = eurFromEuros;

  const updateMilestone = (i: number, field: 'description' | 'amount' | 'duration_label', value: string | number) => {
    const items = milestones.map((li, idx) =>
      idx === i
        ? {
            ...li,
            [field]: field === 'amount' ? (Number(value) || 0) : value,
          }
        : li,
    );
    onChange({ ...scope, line_items: items });
  };

  const addMilestone = () => {
    onChange({ ...scope, line_items: [...milestones, { description: '', amount: 0 }] });
  };

  const removeMilestone = (i: number) => {
    onChange({ ...scope, line_items: milestones.filter((_, idx) => idx !== i) });
  };

  const removeContingency = (afterIdx: number, title: string) => {
    onChange({
      ...scope,
      contingency_drafts: drafts.filter(
        (d) => !(d.after_phase_index === afterIdx && d.title === title),
      ),
    });
  };

  // Contingency drafts keyed by after_phase_index
  const byPhase = new Map<number, QuoteContingencyDraft[]>();
  for (const d of drafts) {
    const arr = byPhase.get(d.after_phase_index) ?? [];
    arr.push(d);
    byPhase.set(d.after_phase_index, arr);
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto">

      {/* ── Dark header ──────────────────────────────────────────────────────── */}
      <div className="px-4 pt-3.5 pb-3" style={{ background: 'var(--color-ink)' }}>
        <Input
          type="text"
          value={scope.title || ''}
          onChange={(e) => onChange({ ...scope, title: e.target.value })}
          placeholder={lang === 'es' ? 'Título del trabajo…' : 'Job title…'}
          className="w-full bg-transparent border-b border-white/20 focus:border-terracotta outline-none font-display text-[17px] font-semibold text-cream placeholder-white/30 pb-0.5 transition-colors"
        />
        {scope.location !== undefined && (
          <Input
            type="text"
            value={scope.location || ''}
            onChange={(e) => onChange({ ...scope, location: e.target.value })}
            placeholder={lang === 'es' ? 'Ubicación…' : 'Location…'}
            className="w-full bg-transparent border-b border-white/10 focus:border-terracotta/60 outline-none text-[11px] text-white/50 placeholder-white/20 mt-1.5 pb-0.5 transition-colors"
          />
        )}
      </div>

      {/* ── Cream body ───────────────────────────────────────────────────────── */}
      <div className="px-4 pt-3.5 pb-6 flex-1" style={{ background: 'var(--color-cream)' }}>

        {/* 1 — Description */}
        <div className="text-[10px] font-bold uppercase tracking-wide mb-1.5" style={LABEL}>
          {lang === 'es' ? 'Descripción' : 'Description'}
        </div>
        <Textarea
          value={scope.description || ''}
          onChange={(e) => onChange({ ...scope, description: e.target.value })}
          placeholder={lang === 'es' ? 'Descripción general del trabajo…' : 'General job description…'}
          rows={2}
          className="w-full bg-transparent border-b border-border focus:border-terracotta outline-none text-[13px] text-ink resize-none mb-4 py-1 transition-colors placeholder-muted"
        />

        {/* 2 — Milestones */}
        <div className="text-[10px] font-bold uppercase tracking-wide mb-2" style={LABEL}>
          {lang === 'es' ? 'Fases del trabajo' : 'Milestones'}
        </div>

        {/* Column headers */}
        {milestones.length > 0 && (
          <div className="flex items-center gap-2 mb-1 text-[10px]" style={{ color: 'var(--color-muted)' }}>
            <span className="flex-1">{lang === 'es' ? 'Descripción' : 'Description'}</span>
            <span className="text-right" style={{ minWidth: 52 }}>{lang === 'es' ? 'Tiempo' : 'Time'}</span>
            <span className="w-24 text-right mr-6">{lang === 'es' ? 'Precio' : 'Amount'}</span>
          </div>
        )}

        <div className="mb-2">
          {/* Contingency drafts before phase 0 */}
          {(byPhase.get(-1) ?? []).map((d) => (
            <ContingencyDraftRow
              key={`draft-before-${d.title}`}
              draft={d}
              lang={lang}
              onRemove={() => removeContingency(d.after_phase_index, d.title)}
            />
          ))}

          {milestones.map((li, i) => (
            <React.Fragment key={i}>
              <div className="flex items-center gap-2 mb-2 group">
                <Input
                  type="text"
                  value={li.description}
                  onChange={(e) => updateMilestone(i, 'description', e.target.value)}
                  placeholder={lang === 'es' ? `Fase ${i + 1}…` : `Phase ${i + 1}…`}
                  className={INPUT_BASE + ' flex-1'}
                />
                {/* Duration: structured number + unit toggle */}
                {(() => {
                  const { n, unit } = parseDuration(li.duration_label);
                  const setDuration = (newN: string, newUnit: 'days' | 'weeks') =>
                    updateMilestone(i, 'duration_label', buildDuration(newN, newUnit));
                  return (
                    <div className="flex items-center gap-0.5 shrink-0">
                      <Input
                        type="number"
                        value={n}
                        onChange={(e) => setDuration(e.target.value, unit)}
                        min={1}
                        inputMode="numeric"
                        className="bg-transparent border-b border-border focus:border-terracotta outline-none py-1 text-[12px] text-stone text-right w-7 transition-colors"
                      />
                      <Button
                        type="button"
                        onClick={() => setDuration(n, unit === 'days' ? 'weeks' : 'days')}
                        className="text-[11px] text-stone hover:text-terracotta transition-colors px-0.5 py-1 border-b border-border whitespace-nowrap"
                        title={lang === 'es' ? 'Cambiar unidad' : 'Change unit'}
                      >
                        {unit}
                      </Button>
                    </div>
                  );
                })()}
                <div className="flex items-center gap-1 shrink-0">
                  <span className="text-[12px] text-stone">€</span>
                  <Input
                    type="number"
                    value={li.amount || ''}
                    onChange={(e) => updateMilestone(i, 'amount', e.target.value)}
                    placeholder="0"
                    min={0}
                    className={AMOUNT_INPUT}
                    inputMode="decimal"
                  />
                  <Button
                    type="button"
                    onClick={() => removeMilestone(i)}
                    aria-label={lang === 'es' ? 'Eliminar fase' : 'Remove milestone'}
                    className="ml-1 opacity-0 group-hover:opacity-100 w-5 h-5 rounded-full text-muted hover:text-red-400 transition-all text-[16px] leading-none flex items-center justify-center"
                  >
                    ×
                  </Button>
                </div>
              </div>

              {/* Contingency drafts after this phase */}
              {(byPhase.get(i) ?? []).map((d) => (
                <ContingencyDraftRow
                  key={`draft-after-${i}-${d.title}`}
                  draft={d}
                  lang={lang}
                  onRemove={() => removeContingency(d.after_phase_index, d.title)}
                />
              ))}
            </React.Fragment>
          ))}

          <Button className="mt-1 text-[12px] text-terracotta hover:text-terracotta/80" type="button"
            onClick={addMilestone}><span className="text-[16px] leading-none">+</span>
            {lang === 'es' ? ' Añadir fase' : ' Add milestone'}</Button>
        </div>

        {/* 3 — Materials upfront */}
        <div className="mt-3 mb-4">
          <div className="text-[10px] font-bold uppercase tracking-wide mb-1.5" style={LABEL}>
            {lang === 'es' ? 'Materiales (por adelantado)' : 'Materials (upfront)'}
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[13px] text-stone flex-1">
              {lang === 'es'
                ? 'Dinero necesario para comprar materiales antes de empezar'
                : 'Amount needed to purchase materials before starting'}
            </span>
            <div className="flex items-center gap-1 shrink-0">
              <span className="text-[12px] text-stone">€</span>
              <Input
                type="number"
                value={materialsUpfront || ''}
                onChange={(e) => onChange({ ...scope, materials_upfront: Number(e.target.value) || 0 })}
                placeholder="0"
                min={0}
                className={AMOUNT_INPUT}
                inputMode="decimal"
              />
            </div>
          </div>
          <p className="text-[11px] mt-1" style={{ color: 'var(--color-muted)' }}>
            {lang === 'es'
              ? 'Dejar en 0 si no se necesitan materiales por adelantado'
              : 'Leave 0 if no upfront materials cost'}
          </p>
        </div>

        {/* 4 — IVA / VAT */}
        <div className="mb-4">
          <div className="text-[10px] font-bold uppercase tracking-wide mb-2" style={LABEL}>
            {lang === 'es' ? 'IVA' : 'VAT'}
          </div>
          <div className="flex flex-col gap-2">
            {([
              { rate: 10, label: lang === 'es' ? '10% — reforma residencial (lo más habitual)' : '10% — residential renovation (most common)' },
              { rate: 21, label: lang === 'es' ? '21% — obra nueva o local comercial' : '21% — new build or commercial premises' },
              { rate: undefined, label: lang === 'es' ? 'Ya incluido en mis precios' : 'Already included in my prices' },
            ] as const).map(({ rate, label }) => (
              <label key={String(rate)} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="radio"
                  name="iva_rate"
                  checked={scope.iva_rate === rate}
                  onChange={() => onChange({ ...scope, iva_rate: rate })}
                  className="w-3.5 h-3.5 accent-terracotta"
                />
                <span className="text-[12px] text-ink">{label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* 5 — Totals summary (read-only, matches QuoteCanvas format) */}
        {(milestones.length > 0 || materialsUpfront > 0) && (
          <div className="mt-2 mb-4 space-y-1.5 border-t border-border pt-3">
            {materialsUpfront > 0 && (
              <div className="flex justify-between text-[12px]">
                <span className="text-stone">{lang === 'es' ? 'Materiales (adelanto)' : 'Materials (upfront)'}</span>
                <span className="text-stone">{fmtEur(materialsUpfront)}</span>
              </div>
            )}
            {(scope.service_fee_percent || 0) > 0 && (
              <div className="flex justify-between text-[12px]">
                <span className="text-stone">Leo fee ({scope.service_fee_percent}%)</span>
                <span className="text-stone">{fmtEur(feeAmount)}</span>
              </div>
            )}
            {ivaRate && ivaAmount > 0 && (
              <>
                <div className="flex justify-between text-[12px]">
                  <span className="text-stone">{lang === 'es' ? 'Subtotal' : 'Subtotal'}</span>
                  <span className="text-stone">{fmtEur(workTotal + feeAmount)}</span>
                </div>
                <div className="flex justify-between text-[12px]">
                  <span className="text-stone">{lang === 'es' ? 'IVA' : 'VAT'} ({ivaRate}%)</span>
                  <span className="text-stone">{fmtEur(ivaAmount)}</span>
                </div>
                <div className="h-px bg-border" />
              </>
            )}
            <div className="flex justify-between">
              <span className="text-[13px] font-bold text-ink">
                Total{ivaRate ? ` (${lang === 'es' ? 'IVA' : 'VAT'} inc.)` : ''}
              </span>
              <span className="text-[13px] font-bold text-ink">{fmtEur(grandTotal)}</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
