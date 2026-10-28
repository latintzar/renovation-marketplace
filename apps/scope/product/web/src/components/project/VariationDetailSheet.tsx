/**
 * VariationDetailSheet — Full-screen bottom drawer for a change order.
 *
 * Homeowner can approve (→ Stripe Checkout) or decline.
 * Calls new JWT-authenticated endpoints:
 *   POST /v1/projects/:token/variations/:id/approve
 *   POST /v1/projects/:token/variations/:id/decline
 */

import { useState } from 'react';
import { Check, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import { Button, Sheet, StatusBadge } from '@scope/ui';
import { API_BASE, apiFetch } from '../../lib/api';
import { eur } from '../../lib/utils';
import type { VariationOrder } from './types';

interface VariationDetailSheetProps {
  variation: VariationOrder | null;
  quoteToken: string;
  onClose: () => void;
  onActioned: () => void;
}

export function VariationDetailSheet({
  variation, quoteToken, onClose, onActioned,
}: VariationDetailSheetProps) {
  const [approving, setApproving] = useState(false);
  const [declining, setDeclining] = useState(false);
  const [declineConfirm, setDeclineConfirm] = useState(false);

  if (!variation) return null;
  const amountEur = eur(variation.amount_cents);

  const handleApprove = async () => {
    setApproving(true);
    try {
      const resp = await apiFetch(
        `${API_BASE}/v1/projects/${quoteToken}/variations/${variation.id}/approve`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' } },
      );
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Failed to approve');
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      } else {
        toast.success('Change order approved');
        onActioned();
        onClose();
      }
    } catch (err: unknown) {
      toast.error(err instanceof Error ? err.message : 'Failed to approve change order');
      setApproving(false);
    }
  };

  const handleDecline = async () => {
    if (!declineConfirm) { setDeclineConfirm(true); return; }
    setDeclining(true);
    try {
      await apiFetch(
        `${API_BASE}/v1/projects/${quoteToken}/variations/${variation.id}/decline`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' } },
      );
      toast.success('Change order declined. The contractor has been notified.');
      onActioned();
      onClose();
    } catch {
      toast.error('Failed to decline');
      setDeclining(false);
    }
  };

  return (
    <Sheet open={!!variation} onClose={onClose}>
      <div className="overflow-y-auto px-6 pt-2 pb-10">
            <div className="flex items-start justify-between mb-4">
              <div>
                <p className="text-[10px] font-semibold uppercase tracking-widest text-amber-700 mb-1">Change order</p>
                <h2 className="text-xl font-semibold text-ink font-display">{variation.title}</h2>
              </div>
              <Button className="p-1.5 -mr-1 text-muted" type="button" onClick={onClose}><X size={20} /></Button>
            </div>

            <div className="bg-amber-50 border border-amber-200 rounded-sm px-4 py-3 mb-4">
              <p className="text-xs text-amber-700 mb-0.5">Additional cost</p>
              <p className="text-2xl font-semibold text-ink font-display">+{amountEur}</p>
            </div>

            {variation.description && (
              <div className="mb-4">
                <p className="text-xs font-medium text-stone uppercase tracking-wide mb-1.5">Description</p>
                <p className="text-sm text-ink leading-relaxed">{variation.description}</p>
              </div>
            )}

            {variation.reason && (
              <div className="mb-4 bg-white border border-border rounded-sm px-4 py-3">
                <p className="text-xs font-medium text-stone uppercase tracking-wide mb-1.5">Contractor's reason</p>
                <p className="text-sm text-stone italic leading-relaxed">"{variation.reason}"</p>
              </div>
            )}

            {variation.photos.length > 0 && (
              <div className="mb-4">
                <p className="text-xs font-medium text-stone uppercase tracking-wide mb-2">Photos</p>
                <div className="flex gap-2 overflow-x-auto pb-1">
                  {variation.photos.map((p, i) => (
                    <img key={i} src={p} alt={`Photo ${i + 1}`} className="w-20 h-20 object-cover rounded-sm border border-border shrink-0" />
                  ))}
                </div>
              </div>
            )}

            <p className="text-xs text-muted mb-6">
              Proposed on {new Date(variation.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'long' })}
            </p>

            {variation.status === 'pending' && (
              <div className="space-y-3">
                <Button size="lg" fullWidth className="text-[15px] disabled:opacity-60 active:scale-[0.98] transition-transform" type="button"
                  onClick={handleApprove}
                  disabled={approving || declining}
                  style={{ background: 'var(--color-teal)' }}>{approving ? <Loader2 size={16} className="animate-spin" /> : <Check size={16} strokeWidth={2.5} />}
                  {approving ? 'Processing…' : `Approve & pay +${amountEur}`}</Button>

                <Button
                  type="button"
                  onClick={handleDecline}
                  disabled={approving || declining}
                  className={`w-full py-3 text-sm font-medium transition-colors ${declineConfirm ? 'text-red-600 font-semibold' : 'text-stone hover:text-ink'}`}
                >
                  {declining ? 'Declining…' : declineConfirm ? 'Sure? Tap again to confirm' : 'Decline change order'}
                </Button>
              </div>
            )}

            {variation.status !== 'pending' && (
              <div className="py-2 text-center">
                <StatusBadge status={variation.status} />
              </div>
            )}
          </div>
        
      
    </Sheet>
  );
}
