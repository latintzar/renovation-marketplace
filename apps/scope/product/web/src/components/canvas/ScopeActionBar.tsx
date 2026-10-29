/**
 * ScopeActionBar — Bottom action bar on quote canvas pages.
 *
 * Contractor view: send to client, copy link, edit, new quote.
 * Homeowner/anonymous view: pay button + consent drawer.
 * Paid state: escrow confirmation badge.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Pencil, Check, Copy, MessageCircle, ShieldCheck } from 'lucide-react';
import type { QuoteUpdate } from '../../lib/api';
import { supabase } from '../../lib/supabase';
import { isSandbox } from '../../lib/utils';
import { eurFromEuros, computeQuoteTotals } from '../../lib/utils';
import { ConsentDrawer } from '../ConsentDrawer';
import { Button } from '@scope/ui';

// ── Scope edit overlay (used internally by ScopeActionBar) ─────────────────

function ScopeEditOverlay({ token, contractorId, onClose }: { token: string; contractorId: string; onClose: () => void }) {
  const navigate = useNavigate();

  const handleEditInChat = () => {
    navigate(`/quote/first?contractorId=${encodeURIComponent(contractorId)}&editToken=${encodeURIComponent(token)}`);
  };

  return (
    <div
      className="fixed inset-0 z-50 bg-ink/60 backdrop-blur-sm flex items-end justify-center"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg bg-cream rounded-t-3xl shadow-2xl animate-in slide-in-from-bottom duration-300 overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-center pt-3 pb-2">
          <div className="w-10 h-1 rounded-full bg-border" />
        </div>
        <div className="px-5 pb-5 pt-1">
          <p className="text-sm font-semibold text-ink mb-0.5">Edit quote</p>
          <p className="text-xs text-stone mb-4">Leo helps you review phases, pricing and description.</p>
          <Button fullWidth className="py-3.5 active:scale-[0.98] duration-150 mb-2" type="button"
            onClick={handleEditInChat}><Pencil size={14} />
            Edit with Leo</Button>
          <Button variant="ghost" fullWidth className="text-stone" type="button"
            onClick={onClose}>Cancel</Button>
        </div>
      </div>
    </div>
  );
}

// ── ScopeActionBar ─────────────────────────────────────────────────────────

interface ScopeActionBarProps {
  token: string;
  contractorId: string;
  isContractor: boolean;
  isPaid: boolean;
  scope: QuoteUpdate | null;
  /** Pre-computed total from the backend (milestones + materials + fee + IVA). Used on pay button. */
  amountTotalCents?: number;
}

export function ScopeActionBar({ token, contractorId, isContractor, isPaid, scope, amountTotalCents }: ScopeActionBarProps) {
  const navigate = useNavigate();
  const [showEditOverlay, setShowEditOverlay] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showConsentDrawer, setShowConsentDrawer] = useState(false);
  const [homeownerEmail, setHomeownerEmail] = useState('');

  const sandboxMode = isSandbox();

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      if (session?.user?.email) setHomeownerEmail(session.user.email);
    });
  }, []);

  if (isPaid) {
    return (
      <div className="shrink-0 border-t border-border bg-cream/95 backdrop-blur-sm px-4 pt-3 pb-safe">
        <div className="max-w-lg mx-auto">
          <div className="flex items-center gap-3 px-4 py-3 rounded-sm bg-green/10 border border-green/20">
            <ShieldCheck size={20} className="text-green shrink-0" />
            <div>
              <p className="text-sm font-semibold text-ink">
                {isContractor ? 'Payment received — funds held in escrow' : 'Payment confirmed'}
              </p>
              <p className="text-xs text-stone mt-0.5">
                {isContractor
                  ? 'You will receive payment as each phase is completed.'
                  : 'Your payment is held securely until work is completed.'}
              </p>
            </div>
          </div>
          {isContractor && (
            <div className="mt-2 text-center">
              <Button
                type="button"
                onClick={() => navigate('/dashboard')}
                className="text-sm text-stone hover:text-ink underline underline-offset-2 transition-colors"
              >
                My jobs →
              </Button>
            </div>
          )}
          {!isContractor && (
            <div className="mt-2 text-center">
              <Button
                type="button"
                onClick={() => navigate(`/project/${token}`)}
                className="text-sm text-stone hover:text-ink underline underline-offset-2 transition-colors"
              >
                View my project →
              </Button>
            </div>
          )}
        </div>
      </div>
    );
  }

  const canvasUrlShare = `${window.location.origin}${import.meta.env.BASE_URL}canvas/${token}`;

  const handleNewQuote = () => {
    try {
      sessionStorage.removeItem(`leo_chat_scope_professional_${contractorId}`);
    } catch { /* continue */ }
    navigate(`/quote/first?contractorId=${encodeURIComponent(contractorId)}`);
  };

  const handleSendToCustomer = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: scope?.title ?? 'Leo Quote', text: `Here is the quote for ${scope?.title ?? 'your project'}:`, url: canvasUrlShare });
        return;
      } catch { /* fall through to WhatsApp */ }
    }
    const text = encodeURIComponent(`Hi, here is the quote:\n${canvasUrlShare}`);
    window.open(`https://wa.me/?text=${text}`, '_blank');
  };

  const handleCopyLink = async () => {
    try {
      await navigator.clipboard.writeText(canvasUrlShare);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* clipboard unavailable */ }
  };

  if (isContractor) {
    return (
      <>
        <div className="shrink-0 border-t border-border bg-cream/95 backdrop-blur-sm px-4 pt-3 pb-safe">
          <div className="max-w-lg mx-auto space-y-2">
            <div className="flex gap-2">
              <Button className="flex-1 py-3.5 active:scale-[0.98] duration-150" type="button"
                onClick={handleSendToCustomer}
                style={{ background: '#25D366' }}><MessageCircle size={16} fill="white" strokeWidth={0} />
                Send to client</Button>
              <Button variant="secondary" size="lg" className="w-12 text-stone hover:border-terracotta hover:text-terracotta active:scale-[0.98] duration-150 shrink-0" type="button"
                onClick={handleCopyLink}
                title="Copy link">{copied ? <Check size={15} className="text-green" /> : <Copy size={15} />}</Button>
            </div>
            <div className="flex gap-2">
              <Button
                type="button"
                onClick={() => setShowEditOverlay(true)}
                className="flex-1 flex items-center justify-center gap-1.5 py-2.5 rounded-sm border border-border text-stone text-xs font-medium hover:border-terracotta hover:text-terracotta transition-colors"
              >
                <Pencil size={13} />
                Edit
              </Button>
              <Button variant="secondary" size="sm" className="flex-1 text-stone hover:border-terracotta hover:text-terracotta" type="button"
                onClick={handleNewQuote}>New quote</Button>
            </div>
          </div>
        </div>
        {showEditOverlay && (
          <ScopeEditOverlay token={token} contractorId={contractorId} onClose={() => setShowEditOverlay(false)} />
        )}
      </>
    );
  }

  // Homeowner / anonymous view
  const totalEur = amountTotalCents != null ? amountTotalCents / 100 : computeQuoteTotals(scope ?? {}).total;
  const totalLabel = eurFromEuros(totalEur);

  return (
    <>
      <div className="shrink-0 border-t border-border bg-cream/95 backdrop-blur-sm px-4 pt-3 pb-safe">
        <div className="max-w-lg mx-auto">
          {sandboxMode && (
            <div className="mb-2 px-3 py-2 rounded-sm bg-amber-50 border border-amber-200 text-xs text-amber-800">
              <strong>Sandbox</strong> — Use card{' '}
              <code className="font-mono">4242 4242 4242 4242</code>, any future date, any CVC.
            </div>
          )}
          <Button
            type="button"
            onClick={() => setShowConsentDrawer(true)}
            className="w-full flex items-center justify-center gap-2.5 py-4 rounded-sm text-cream text-[15px] font-semibold transition-colors active:scale-[0.98] duration-150"
            style={{ background: 'var(--color-ink)' }}
          >
            Pay {totalLabel} · Start project →
          </Button>
          <p className="text-center text-xs text-muted mt-2 pb-1">
            Secure payment · Funds held in escrow until the work is done
          </p>
        </div>
      </div>

      <ConsentDrawer
        open={showConsentDrawer}
        onClose={() => setShowConsentDrawer(false)}
        quoteToken={token}
        scope={scope}
        amountTotalCents={amountTotalCents ?? 0}
        homeowner_email={homeownerEmail}
        onPaymentReady={(checkoutUrl) => { window.location.href = checkoutUrl; }}
      />
    </>
  );
}
