/**
 * StripeRefresh — Regenerates an expired Stripe Account Link.
 *
 * Stripe Account Links expire quickly. If the contractor's link expired
 * (or they navigated back), Stripe redirects here. We generate a new link
 * and immediately redirect them back to Stripe.
 */

import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getStripeAccountLink } from '../lib/api';
import { Button } from '@scope/ui';

export default function StripeRefresh() {
  const [searchParams] = useSearchParams();
  const contractorId = searchParams.get('contractor') ?? '';
  const [error, setError] = useState('');

  useEffect(() => {
    if (!contractorId) {
      setError('Missing contractor ID');
      return;
    }

    const refresh = async () => {
      const result = await getStripeAccountLink(contractorId);
      if (!result.ok || !result.url) {
        setError(result.error || 'Could not generate onboarding link');
        return;
      }
      window.location.href = result.url;
    };

    refresh();
  }, [contractorId]);

  return (
    <div className="flex flex-col items-center justify-center h-dvh bg-cream px-6">
      <div className="w-full max-w-sm text-center">
        {error ? (
          <>
            <p className="text-base font-semibold text-ink mb-2">Could not refresh link</p>
            <p className="text-sm text-stone mb-6">{error}</p>
            <Button
              type="button"
              onClick={() => window.history.back()}
              className="w-full py-3.5 rounded-sm bg-ink text-cream text-sm font-semibold hover:bg-stone transition-colors"
            >
              Go back
            </Button>
          </>
        ) : (
          <>
            <div className="w-10 h-10 border-2 border-terracotta/30 border-t-terracotta rounded-full animate-spin mx-auto mb-4" />
            <p className="text-sm text-stone">Refreshing your onboarding link…</p>
          </>
        )}
      </div>
    </div>
  );
}
