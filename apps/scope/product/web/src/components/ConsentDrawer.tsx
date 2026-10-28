/**
 * ConsentDrawer — Pre-payment agreement and consent.
 *
 * Full-screen vaul drawer shown before Stripe Checkout. Implements eIDAS
 * Simple Electronic Signature: affirmative checkbox, document visible before
 * agreement, consent record (IP, user_agent, document hash) stored server-side.
 *
 * Flow:
 *   "Pay & start" → drawer opens → homeowner ticks "I agree"
 *   → POST /v1/documents/{token}/record-consent
 *   → POST /v1/payment/create-checkout (with consent_id)
 *   → redirect to Stripe Checkout
 */

import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Shield, ExternalLink, Loader2 } from 'lucide-react';
import { QuoteCanvas , Button , Sheet } from '@scope/ui';
import { DocumentViewer } from './DocumentViewer';
import { API_BASE, apiFetch, type QuoteUpdate } from '../lib/api';
import { eur } from '../lib/utils';
import { track } from '../lib/tracking';

interface ConsentDrawerProps {
  open: boolean;
  onClose: () => void;
  quoteToken: string;
  scope: QuoteUpdate | null;
  amountTotalCents: number;
  homeowner_email?: string;
  onPaymentReady: (checkoutUrl: string) => void;
}

type Tab = 'scope' | 'agreement';

export function ConsentDrawer({
  open,
  onClose,
  quoteToken,
  scope,
  amountTotalCents,
  homeowner_email,
  onPaymentReady,
}: ConsentDrawerProps) {
  const { t } = useTranslation();
  const [tab, setTab] = useState<Tab>('scope');
  const [agreed, setAgreed] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const totalLabel = eur(amountTotalCents);

  const handleConfirm = async () => {
    if (!agreed) return;
    setLoading(true);
    setError('');
    track('payment.started', { token: quoteToken, amount_cents: amountTotalCents });

    try {
      // Step 1: Record consent (eIDAS)
      const consentResp = await apiFetch(`${API_BASE}/v1/documents/${quoteToken}/record-consent`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          homeowner_email: homeowner_email || '',
          user_agent: navigator.userAgent,
        }),
      });

      const consentData = consentResp.ok ? await consentResp.json() : {};
      const consentId = consentData.consent_id;

      // Step 2: Create Stripe Checkout session
      const checkoutResp = await apiFetch(`${API_BASE}/v1/payment/create-checkout`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          quote_token: quoteToken,
          homeowner_email: homeowner_email || undefined,
          consent_id: consentId,
        }),
      });

      if (!checkoutResp.ok) {
        const err = await checkoutResp.json().catch(() => ({}));
        throw new Error(err.detail || 'Could not start payment');
      }

      const checkoutData = await checkoutResp.json();
      if (!checkoutData.checkout_url) throw new Error('No checkout URL returned');

      onPaymentReady(checkoutData.checkout_url);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Payment error — please try again');
      setLoading(false);
    }
  };

  return (
    <Sheet open={open} onClose={onClose}>
          {/* Dark header */}
          <div className="shrink-0 px-5 pt-5 pb-4 flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold text-cream font-display">
                {t('consent_title')}
              </h2>
              <p className="text-xs text-cream/50 mt-0.5">{t('consent_subtitle')}</p>
            </div>
            <Button size="sm" className="w-8 rounded-full bg-cream/10 text-cream/60" type="button"
              onClick={onClose}>×</Button>
          </div>

          {/* Tab bar */}
          <div className="shrink-0 px-5 pb-3 flex gap-2">
            <Button
              type="button"
              onClick={() => setTab('scope')}
              className={`px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                tab === 'scope' ? 'bg-cream text-ink' : 'bg-cream/10 text-cream/60 hover:bg-cream/20'
              }`}
            >
              {t('consent_tab_scope')}
            </Button>
            <Button
              type="button"
              onClick={() => setTab('agreement')}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-colors ${
                tab === 'agreement' ? 'bg-cream text-ink' : 'bg-cream/10 text-cream/60 hover:bg-cream/20'
              }`}
            >
              {t('consent_tab_agreement')}
              <ExternalLink size={10} />
            </Button>
          </div>

          {/* Scrollable content */}
          <div className="flex-1 overflow-y-auto min-h-0 bg-cream">
            {tab === 'scope' && (
              <div className="pb-4">
                <QuoteCanvas scope={scope} />
              </div>
            )}
            {tab === 'agreement' && (
              <div className="p-4">
                <DocumentViewer
                  src={`/v1/documents/${quoteToken}/agreement`}
                  title={t('consent_agreement_title')}
                />
              </div>
            )}
          </div>

          {/* Sticky footer */}
          <div className="shrink-0 bg-cream border-t border-border px-5 pt-4 pb-safe">
            {/* Escrow assurance */}
            <div className="flex items-start gap-2.5 mb-4 px-3 py-2.5 rounded-sm bg-green/8 border border-green/20">
              <Shield size={15} className="text-green shrink-0 mt-0.5" />
              <p className="text-xs text-ink leading-relaxed">{t('consent_escrow_note')}</p>
            </div>

            {/* Consent checkbox */}
            <label className="flex items-start gap-3 mb-4 cursor-pointer select-none">
              <Button
                type="button"
                role="checkbox"
                aria-checked={agreed}
                onClick={() => setAgreed(!agreed)}
                className={`w-5 h-5 rounded flex items-center justify-center shrink-0 mt-0.5 border-2 transition-colors ${
                  agreed ? 'bg-ink border-ink' : 'bg-white border-border hover:border-stone'
                }`}
              >
                {agreed && <Check size={11} className="text-cream" strokeWidth={3} />}
              </Button>
              <span className="text-[13px] text-ink leading-relaxed">
                {t('consent_checkbox_prefix')}{' '}
                <a
                  href="/terms"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="underline hover:text-terracotta transition-colors"
                >
                  {t('consent_terms_link')}
                </a>
                . {t('consent_checkbox_suffix')}
              </span>
            </label>

            {error && <p className="text-xs text-red-500 text-center mb-3">{error}</p>}

            <Button size="lg" fullWidth className="gap-2.5 text-[15px] active:scale-[0.98] duration-150 disabled:opacity-40" type="button"
              onClick={handleConfirm}
              disabled={!agreed || loading}
              style={{ background: agreed ? 'var(--color-ink)' : 'var(--color-muted)' }}>{loading ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  {t('consent_processing')}
                </>
              ) : (
                t('consent_confirm_pay', { amount: totalLabel })
              )}</Button>

            <p className="text-center text-xs text-muted mt-2 pb-1">
              {t('consent_security_note')}
            </p>
          </div>
        </Sheet>
  );
}
