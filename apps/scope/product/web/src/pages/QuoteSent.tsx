/**
 * QuoteSent — The share moment after a scope is finalized.
 *
 * Shows a fintech-style share card with:
 *   - Scope summary (title, total, phases)
 *   - WhatsApp share button (primary)
 *   - Copy link button
 *   - Native share sheet on mobile
 *
 * This page is reached from the StripeReturn page (after KYC)
 * or directly if the contractor wants to share before KYC.
 */

import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Share2, Copy, Check, MessageCircle } from 'lucide-react';
import { QuoteCanvas , Button } from '@scope/ui';
import { computeQuoteTotals, eurFromEuros } from '../lib/utils';
import { useCanvasQuery } from '../hooks/useCanvasQuery';
import { PageLoading } from '../components/PageLoading';
import { LeoLogo } from '../components/LeoLogo';
import { LanguageToggle } from '../components/LanguageToggle';

export default function QuoteSent() {
  const { token } = useParams<{ token: string }>();
  const [copied, setCopied] = useState(false);

  const { data: canvasData, isLoading: loading } = useCanvasQuery(token);
  const scope = canvasData?.scope ?? null;

  const canvasUrl = `${window.location.origin}/app/canvas/${token}`;

  const phases = scope?.line_items ?? [];
  const { total } = computeQuoteTotals(scope ?? {});
  const scopeTitle = scope?.title ?? 'Your scope';

  const handleWhatsApp = () => {
    const text = encodeURIComponent(
      `Hi, here is your quote for ${scopeTitle}:\n${canvasUrl}`,
    );
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(canvasUrl);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback: select input
    }
  };

  const handleNativeShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: scopeTitle,
          text: `Leo quote: ${scopeTitle}`,
          url: canvasUrl,
        });
      } catch { /* cancelled */ }
    } else {
      handleCopy();
    }
  };

  if (loading) return <PageLoading />;

  return (
    <div className="flex flex-col h-dvh bg-cream">
      {/* Header */}
      <header className="shrink-0 flex items-center justify-between px-4 h-12 bg-ink">
        <LeoLogo variant="cream" height={15} />
        <LanguageToggle variant="dark" />
      </header>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto min-h-0">
        <div className="max-w-lg mx-auto px-4 pt-6 pb-32">

          {/* Success badge */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-12 h-12 rounded-full bg-green/10 flex items-center justify-center shrink-0">
              <svg viewBox="0 0 24 24" className="w-6 h-6 text-green" fill="none" stroke="currentColor" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
              </svg>
            </div>
            <div>
              <p className="font-display text-lg font-semibold text-ink">Scope ready to share</p>
              <p className="text-sm text-stone">
                {eurFromEuros(total)} · {phases.length} {phases.length === 1 ? 'phase' : 'phases'}
              </p>
            </div>
          </div>

          {/* Scope preview card */}
          {scope && (
            <div className="rounded-sm overflow-hidden mb-5 border border-border">
              <QuoteCanvas scope={scope} />
            </div>
          )}

          {/* Share link card */}
          <div className="rounded-sm border border-border bg-white/60 px-4 py-3.5 mb-4">
            <p className="text-xs text-stone font-medium mb-1.5">Share link</p>
            <div className="flex items-center gap-2">
              <p className="text-xs text-ink font-mono truncate flex-1">{canvasUrl}</p>
              <Button variant="secondary" size="sm" className="shrink-0 text-stone hover:border-terracotta hover:text-terracotta" type="button"
                onClick={handleCopy}>{copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? 'Copied' : 'Copy'}</Button>
            </div>
          </div>

          {/* Instructions */}
          <div className="rounded-sm bg-terracotta-light border border-terracotta/20 px-4 py-3.5 mb-4">
            <p className="text-sm font-semibold text-ink mb-1">What happens next</p>
            <ul className="space-y-1.5">
              {[
                'Send this link to your customer via WhatsApp',
                'They review the scope and approve it',
                'They pay the full amount through Leo (held in escrow)',
                'You receive payment as each phase is completed',
              ].map((step, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-stone">
                  <span className="w-4 h-4 rounded-full bg-terracotta/20 flex items-center justify-center text-terracotta font-bold text-[10px] shrink-0 mt-0.5">{i + 1}</span>
                  {step}
                </li>
              ))}
            </ul>
          </div>

          {/* Dashboard link */}
          <div className="text-center">
            <Link
              to="/dashboard"
              className="text-sm text-stone hover:text-ink underline underline-offset-2 transition-colors"
            >
              Go to my quotes →
            </Link>
          </div>

        </div>
      </div>

      {/* Sticky share bar */}
      <div className="shrink-0 border-t border-border bg-cream/95 backdrop-blur-sm px-4 pt-3 pb-safe">
        <div className="max-w-lg mx-auto flex gap-2.5">
          {/* WhatsApp — primary */}
          <Button className="flex-1 py-3.5 active:scale-[0.98] duration-150" type="button"
            onClick={handleWhatsApp}
            style={{ background: '#25D366' }}><MessageCircle size={16} fill="white" />
            Send via WhatsApp</Button>

          {/* Native share / copy */}
          <Button variant="secondary" size="lg" className="w-12 text-stone hover:border-terracotta hover:text-terracotta active:scale-[0.98] duration-150 shrink-0" type="button"
            onClick={handleNativeShare}>{copied ? <Check size={16} /> : <Share2 size={16} />}</Button>
        </div>
      </div>
    </div>
  );
}
