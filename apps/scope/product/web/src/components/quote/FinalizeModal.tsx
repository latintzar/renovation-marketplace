/**
 * FinalizeModal — Full-screen step shown after the quote is ready.
 *
 * Handles both create (new scope → finalizeScope) and update (edit mode → updateScope).
 * On success calls onConnectBank(token) which routes to Stripe KYC or QuoteSent.
 */

import { useState } from 'react';
import { finalizeScope, updateScope, type QuoteUpdate } from '../../lib/api';
import { track } from '../../lib/tracking';
import { useAuth } from '../../context/AuthContext';
import { computeQuoteTotals, eurFromEuros } from '../../lib/utils';
import { Button } from '@scope/ui';

interface FinalizeModalProps {
  scope: QuoteUpdate;
  contractorId: string;
  /** If set, updates the existing scope instead of creating a new one */
  editToken?: string;
  onConnectBank: (token: string) => void;
  onDismiss: () => void;
}

export function FinalizeModal({ scope, contractorId, editToken, onConnectBank, onDismiss }: FinalizeModalProps) {
  const { user } = useAuth();
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');
  const { total } = computeQuoteTotals(scope);

  const handleConnectBank = async () => {
    setSaving(true);
    setError('');

    let result: { ok: boolean; token?: string; error?: string };
    if (editToken) {
      result = await updateScope(editToken, scope, contractorId);
      if (result.ok) result = { ok: true, token: editToken };
    } else {
      const authUserId = user?.id;
      result = await finalizeScope(contractorId, scope, authUserId);
    }

    setSaving(false);
    if (!result.ok || !result.token) {
      setError(result.error || 'Could not save scope — please try again');
      return;
    }
    track('scope.created', {
      token: result.token,
      value_cents: (result as Record<string, unknown>).amount_total_cents,
      contractor_id: contractorId,
    });
    onConnectBank(result.token);
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-cream animate-in fade-in duration-200 overflow-hidden">

      {/* ── Charcoal hero ─────────────────────────────────────────────────── */}
      <div className="shrink-0 flex flex-col items-center justify-center px-6 pt-12 pb-10 text-cream"
        style={{ background: 'var(--color-ink)' }}>

        {/* Close */}
        <Button size="sm" className="absolute top-4 right-4 w-8 rounded-full text-cream/50 hover:text-cream" type="button"
          onClick={onDismiss}
          aria-label="Close"><svg viewBox="0 0 24 24" className="w-5 h-5" fill="none" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg></Button>

        {/* Bank icon */}
        <div className="mb-6">
          <div
            className="w-20 h-20 flex items-center justify-center shadow-2xl"
            style={{ background: '#2C2825', borderRadius: 'var(--radius-xl)', border: '1.5px solid rgba(250,248,244,0.12)' }}
          >
            <svg viewBox="0 0 32 32" className="w-9 h-9" fill="none" stroke="currentColor" strokeWidth={1.5}
              style={{ color: 'var(--color-cream)' }}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 13.5h24M4 27h24M16 4l12 9.5H4L16 4z" />
              <rect x="7" y="13.5" width="3.5" height="9" rx="0.5" />
              <rect x="14.25" y="13.5" width="3.5" height="9" rx="0.5" />
              <rect x="21.5" y="13.5" width="3.5" height="9" rx="0.5" />
            </svg>
          </div>
        </div>

        <h1 className="font-display text-2xl font-semibold text-cream text-center mb-2 leading-tight">
          Connect your bank<br />to get paid
        </h1>
        <p className="text-sm text-center leading-relaxed" style={{ color: 'rgba(250,248,244,0.6)', maxWidth: 260 }}>
          Your quote is ready. Link your bank account and receive payment directly when the client approves.
        </p>

        {/* Stripe trust badge */}
        <div className="mt-5 flex items-center gap-2 px-3 py-1.5 rounded-full"
          style={{ background: 'rgba(250,248,244,0.08)', border: '1px solid rgba(250,248,244,0.12)' }}>
          <span className="text-xs font-bold tracking-tight" style={{ color: 'rgba(250,248,244,0.75)', fontFamily: 'system-ui, sans-serif' }}>Stripe</span>
          <span className="text-xs" style={{ color: 'rgba(250,248,244,0.35)' }}>·</span>
          <span className="text-xs" style={{ color: 'rgba(250,248,244,0.5)' }}>Secure payments · Encrypted data</span>
        </div>
      </div>

      {/* ── Cream content ──────────────────────────────────────────────────── */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="px-5 pt-5 pb-28">

          {/* Total amount */}
          <div className="flex items-center justify-between px-4 py-3.5 rounded-sm border border-border bg-white/50 mb-5">
            <span className="text-sm font-medium text-stone">
              Quote total{scope.iva_rate ? ` (VAT ${scope.iva_rate}% inc.)` : ''}
            </span>
            <span className="text-base font-bold text-ink">
              {eurFromEuros(total)}
            </span>
          </div>

          {/* How payment works — per-phase escrow */}
          <div className="rounded-sm border border-border bg-white/50 px-4 py-3.5 mb-5">
            <p className="text-xs font-semibold text-ink mb-2.5">How payment works</p>
            <div className="space-y-2.5">
              {[
                ['1', 'Client pays the full amount upfront (held in secure escrow)'],
                ['2', 'You receive payment upon completing each phase of work'],
              ].map(([num, desc]) => (
                <div key={num} className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-terracotta/15 flex items-center justify-center text-terracotta font-bold text-[10px] shrink-0 mt-0.5">{num}</span>
                  <span className="text-xs text-stone leading-snug">{desc}</span>
                </div>
              ))}
            </div>
          </div>

          <p className="text-xs text-muted mb-2 text-center">
            Compatible with CaixaBank, BBVA, Santander, ING, Sabadell and more
          </p>

        </div>
      </div>

      {/* ── Sticky CTA ─────────────────────────────────────────────────────── */}
      <div className="absolute bottom-0 inset-x-0 bg-cream/95 backdrop-blur-sm border-t border-border px-5 pt-3 pb-safe">
        {error && <p className="text-xs text-red-500 mb-2 text-center">{error}</p>}
        <Button size="lg" fullWidth className="text-[15px] active:scale-[0.98] duration-150 disabled:opacity-60" type="button"
          onClick={handleConnectBank}
          disabled={saving}
          style={{ background: 'var(--color-ink)' }}>{saving ? (
            <>
              <div className="w-4 h-4 border-2 border-cream/30 border-t-cream rounded-full animate-spin" />
              Saving…
            </>
          ) : (
            <>
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2}>
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2" />
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16" />
              </svg>
              Connect bank and get paid
            </>
          )}</Button>
        <Button variant="ghost" fullWidth className="text-stone" type="button"
          onClick={onDismiss}>Not now</Button>
      </div>

    </div>
  );
}
