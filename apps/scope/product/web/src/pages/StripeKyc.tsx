/**
 * StripeKyc — Transition screen while Stripe Connect onboarding link is generated.
 *
 * Flow:
 *   1. Create/find Stripe Express account for contractor
 *   2. Generate single-use Account Link
 *   3. Full-page redirect to Stripe's hosted KYC (Spanish locale, collects DNI/NIF + IBAN)
 *   4. Stripe returns to /stripe/complete (StripeReturn)
 *
 * This screen is shown for ~2–4 seconds while the API calls complete.
 * Design mirrors the FinalizeModal hero so the transition feels seamless.
 */

import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { createStripeAccount, getStripeAccountLink } from '../lib/api';
import { Button } from '@scope/ui';

type KycState = 'preparing' | 'redirecting' | 'error';

const SPANISH_BANKS = [
  { name: 'CaixaBank', color: '#005A9C' },
  { name: 'BBVA',      color: '#004A97' },
  { name: 'Santander', color: '#EC0000' },
  { name: 'ING',       color: '#FF6200' },
  { name: 'Sabadell',  color: '#007DB7' },
  { name: 'Bankinter', color: '#F15A22' },
];

export default function StripeKyc() {
  const [searchParams] = useSearchParams();
  const contractorId = searchParams.get('contractor') ?? '';

  const [state, setState] = useState<KycState>('preparing');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!contractorId) {
      setError('Contractor ID not found — go back and try again.');
      setState('error');
      return;
    }

    const launch = async () => {
      const accountResult = await createStripeAccount(contractorId);
      if (!accountResult.ok) {
        setError(accountResult.error || 'Could not set up your account');
        setState('error');
        return;
      }

      setState('redirecting');
      const linkResult = await getStripeAccountLink(contractorId);
      if (!linkResult.ok || !linkResult.url) {
        setError(linkResult.error || 'Could not generate the verification link');
        setState('error');
        return;
      }

      window.location.href = linkResult.url;
    };

    launch();
  }, [contractorId]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: 'var(--color-ink)' }}>

      {/* ── Charcoal hero ─────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 pb-4 text-cream">

        {/* Bank icon */}
        <div className="mb-8">
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

        {state !== 'error' && (
          <>
            <h1 className="font-display text-2xl font-semibold text-cream text-center mb-3 leading-tight">
              {state === 'preparing' ? 'Setting up your account…' : 'Opening Stripe…'}
            </h1>
            <p className="text-sm text-center leading-relaxed mb-2" style={{ color: 'rgba(250,248,244,0.55)', maxWidth: 280 }}>
              Stripe will ask you to create a quick account (or sign in if you already have one).
              It only takes a few minutes.
            </p>
            <p className="text-xs text-center leading-relaxed mb-6 px-2" style={{ color: 'rgba(250,248,244,0.35)', maxWidth: 280 }}>
              You'll see a Stripe screen — that's where you securely connect your bank account.
            </p>

            {/* Animated progress dots */}
            <div className="flex items-center gap-1.5 mb-8">
              {[0, 1, 2].map((i) => (
                <span
                  key={i}
                  className="w-2 h-2 rounded-full"
                  style={{
                    background: 'rgba(250,248,244,0.4)',
                    animation: `pulse 1.2s ${i * 0.2}s ease-in-out infinite`,
                  }}
                />
              ))}
            </div>

            {/* What Stripe will ask for */}
            <div className="w-full max-w-xs space-y-2.5">
              {[
                { icon: '🪪', label: 'Your government-issued ID' },
                { icon: '🏦', label: 'Your IBAN' },
                { icon: '📷', label: 'A photo of your document' },
              ].map(({ icon, label }) => (
                <div key={label} className="flex items-center gap-3 px-4 py-2.5 rounded-sm"
                  style={{ background: 'rgba(250,248,244,0.07)', border: '1px solid rgba(250,248,244,0.1)' }}>
                  <span className="text-base">{icon}</span>
                  <span className="text-sm" style={{ color: 'rgba(250,248,244,0.75)' }}>{label}</span>
                </div>
              ))}
            </div>
          </>
        )}

        {state === 'error' && (
          <div className="text-center max-w-xs">
            <div className="w-14 h-14 rounded-full flex items-center justify-center mx-auto mb-5"
              style={{ background: 'rgba(239,68,68,0.15)' }}>
              <svg viewBox="0 0 24 24" className="w-7 h-7" fill="none" stroke="currentColor" strokeWidth={2}
                style={{ color: '#F87171' }}>
                <circle cx="12" cy="12" r="10" />
                <path strokeLinecap="round" d="M12 8v4M12 16h.01" />
              </svg>
            </div>
            <h2 className="font-display text-xl font-semibold text-cream mb-2">
              {error.includes('Connect') || error.includes('connect')
                ? 'Payments being activated'
                : 'Something went wrong'}
            </h2>
            <p className="text-sm mb-6" style={{ color: 'rgba(250,248,244,0.55)' }}>
              {error.includes('Connect') || error.includes('connect')
                ? 'The payment system is being activated. Try again in a few minutes or contact Leo.'
                : 'Could not connect to Stripe. Go back and try again.'}
            </p>
            <Button
              type="button"
              onClick={() => window.history.back()}
              className="px-6 py-3 rounded-sm text-sm font-semibold transition-colors"
              style={{ background: 'rgba(250,248,244,0.1)', color: 'var(--color-cream)', border: '1px solid rgba(250,248,244,0.2)' }}
            >
              Go back
            </Button>
          </div>
        )}
      </div>

      {/* ── Bottom trust bar ──────────────────────────────────────────────── */}
      {state !== 'error' && (
        <div className="shrink-0 px-5 pb-8 pt-4"
          style={{ borderTop: '1px solid rgba(250,248,244,0.08)' }}>

          {/* Bank logos */}
          <div className="flex flex-wrap justify-center gap-2 mb-4">
            {SPANISH_BANKS.map((bank) => (
              <div
                key={bank.name}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-sm"
                style={{
                  background: 'rgba(250,248,244,0.07)',
                  border: '1px solid rgba(250,248,244,0.1)',
                }}
              >
                <span className="w-2 h-2 rounded-full shrink-0" style={{ background: bank.color }} />
                <span className="text-xs font-medium" style={{ color: 'rgba(250,248,244,0.6)' }}>{bank.name}</span>
              </div>
            ))}
          </div>

          <p className="text-center text-xs" style={{ color: 'rgba(250,248,244,0.3)' }}>
            Powered by Stripe · Your data is encrypted and protected
          </p>
        </div>
      )}

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 0.3; transform: scale(0.8); }
          50%       { opacity: 1;   transform: scale(1.2); }
        }
      `}</style>
    </div>
  );
}
