/**
 * StripeReturn — Handles return from Stripe Connect onboarding.
 *
 * Stripe redirects here when the contractor finishes (or exits) the
 * hosted onboarding form. We check their account status and either:
 *   - Show success + scope share link (if fully verified)
 *   - Show "still processing" state (if submitted but pending review)
 *   - Show "not complete" state (if they exited early)
 */

import { useEffect, useState } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { getStripeAccountStatus } from '../lib/api';
import { getLeoAuth, mergeLeoAuth } from '../lib/utils';
import { Button } from '@scope/ui';

type ReturnState = 'checking' | 'complete' | 'pending' | 'incomplete';

export default function StripeReturn() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const contractorId = searchParams.get('contractor') ?? '';

  const [state, setState] = useState<ReturnState>('checking');
  const [error, setError] = useState('');

  const quoteToken = (getLeoAuth().quote_token as string) || '';

  useEffect(() => {
    if (!contractorId) {
      setState('incomplete');
      return;
    }

    const checkStatus = async () => {
      const status = await getStripeAccountStatus(contractorId);
      if (!status.ok) {
        setError(status.error || 'Could not check account status');
        setState('incomplete');
        return;
      }

      if (status.onboarding_complete) {
        // Persist flag so future scope finalizations skip KYC in the same session
        mergeLeoAuth({ stripe_onboarding_complete: true });
        setState('complete');
      } else if (status.details_submitted) {
        setState('pending');
      } else {
        setState('incomplete');
      }
    };

    checkStatus();
  }, [contractorId]);

  const handleViewScope = () => {
    if (quoteToken) {
      // Show the share moment page (fintech celebration + share card)
      navigate(`/quote/sent/${encodeURIComponent(quoteToken)}`, { replace: true });
    }
  };

  const handleCompleteKyc = () => {
    navigate(`/stripe/kyc?contractor=${encodeURIComponent(contractorId)}${quoteToken ? `&scope=${encodeURIComponent(quoteToken)}` : ''}`, { replace: true });
  };

  return (
    <div className="flex flex-col items-center justify-center h-dvh bg-cream px-6">
      <div className="w-full max-w-sm text-center">

        {state === 'checking' && (
          <>
            <div className="w-10 h-10 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm text-stone">Checking your account…</p>
          </>
        )}

        {state === 'complete' && (
          <>
            <div className="w-20 h-20 rounded-full bg-green/10 flex items-center justify-center mx-auto mb-6 relative">
              <svg viewBox="0 0 24 24" className="w-10 h-10 text-green" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
              <span className="absolute inset-0 rounded-full bg-green/20 animate-ping" style={{ animationIterationCount: 2 } as React.CSSProperties} />
            </div>

            <h1 className="font-display text-2xl font-semibold text-ink mb-2">
              You're all set! 🎉
            </h1>
            <p className="text-sm text-stone mb-8 leading-relaxed max-w-xs mx-auto">
              Your bank is connected. As soon as a homeowner approves your scope, you'll get paid directly to your account.
            </p>

            {quoteToken && (
              <Button size="lg" fullWidth className="text-[15px] active:scale-[0.98] duration-150 mb-3" type="button"
                onClick={handleViewScope}>View your scope →</Button>
            )}

            <p className="text-xs text-muted mb-4">
              Share the scope link with your customer. They can approve it and pay through Leo.
            </p>
            <Link
              to="/dashboard"
              className="text-sm text-stone hover:text-ink underline underline-offset-2 transition-colors"
            >
              Go to my quotes →
            </Link>
          </>
        )}

        {state === 'pending' && (
          <>
            <div className="w-16 h-16 rounded-full bg-amber-50 flex items-center justify-center mx-auto mb-5">
              <svg viewBox="0 0 24 24" className="w-8 h-8 text-amber-500" fill="none" stroke="currentColor" strokeWidth={2}>
                <circle cx="12" cy="12" r="10"/>
                <path d="M12 6v6l4 2"/>
              </svg>
            </div>

            <h2 className="font-display text-xl font-semibold text-ink mb-2">
              Verification in progress
            </h2>
            <p className="text-sm text-stone mb-8 leading-relaxed max-w-xs mx-auto">
              Stripe is reviewing your details. This usually takes a few minutes to a few hours.
              You'll be able to receive payments once they confirm your account.
            </p>

            {quoteToken && (
              <Button size="lg" fullWidth className="text-[15px] active:scale-[0.98] duration-150 mb-3" type="button"
                onClick={handleViewScope}>View your scope</Button>
            )}

            <p className="text-xs text-muted">
              We'll notify you when your account is verified.
            </p>
          </>
        )}

        {state === 'incomplete' && (
          <>
            <div className="w-16 h-16 rounded-full bg-border flex items-center justify-center mx-auto mb-5">
              <svg viewBox="0 0 24 24" className="w-8 h-8 text-stone" fill="none" stroke="currentColor" strokeWidth={2}>
                <rect x="2" y="7" width="20" height="14" rx="2" ry="2"/>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
              </svg>
            </div>

            <h2 className="font-display text-xl font-semibold text-ink mb-2">
              Bank not connected yet
            </h2>
            <p className="text-sm text-stone mb-8 leading-relaxed max-w-xs mx-auto">
              {error || "You'll need to connect your bank account before you can receive payments."}
            </p>

            <Button variant="terracotta" size="lg" fullWidth className="text-[15px] active:scale-[0.98] duration-150 mb-3" type="button"
              onClick={handleCompleteKyc}>Complete verification</Button>

            {quoteToken && (
              <Button variant="secondary" fullWidth className="text-stone hover:border-terracotta hover:text-terracotta" type="button"
                onClick={handleViewScope}>View scope first</Button>
            )}
          </>
        )}

      </div>
    </div>
  );
}
