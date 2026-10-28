/**
 * MilestoneDetailSheet — Bottom drawer showing full proof details for a milestone.
 *
 * Homeowners can review photos/notes and release the payment from here.
 * Contractors see a read-only view.
 */

import { useState, useRef, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { Check, Loader2, X } from 'lucide-react';
import { toast } from 'sonner';
import { API_BASE, apiFetch } from '../../lib/api';
import { track } from '../../lib/tracking';
import { eur } from '../../lib/utils';
import type { Milestone, MilestoneUpdate } from './types';
import { Button , Sheet } from '@scope/ui';

interface MilestoneDetailSheetProps {
  open: boolean;
  onClose: () => void;
  milestone: Milestone;
  milestoneIndex: number;
  update: MilestoneUpdate | undefined;
  contractorName: string;
  quoteToken: string;
  onReleased: () => void;
  navigateToChat: () => void;
  onOpenLightbox: (photos: string[], index: number) => void;
  canRelease?: boolean;
}

export function MilestoneDetailSheet({
  open, onClose, milestone, milestoneIndex, update, contractorName, quoteToken,
  onReleased, navigateToChat, onOpenLightbox, canRelease = true,
}: MilestoneDetailSheetProps) {
  const { t } = useTranslation();
  const [showConfirm, setShowConfirm] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const confirmRef = useRef<HTMLDivElement>(null);
  const amountEur = eur(milestone.amount_cents ?? Math.round(milestone.amount * 100));
  const status = milestone.status || 'pending';
  const photos = update?.photos || [];

  useEffect(() => { if (open) { setShowConfirm(false); setError(''); } }, [open]);
  useEffect(() => {
    if (showConfirm && confirmRef.current) {
      confirmRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [showConfirm]);

  const handleRelease = async () => {
    setLoading(true);
    setError('');
    try {
      const resp = await apiFetch(
        `${API_BASE}/v1/projects/${quoteToken}/milestones/${milestoneIndex}/release`,
        { method: 'POST', headers: { 'Content-Type': 'application/json' } },
      );
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || 'Release failed');
      }
      track('milestone.released', { token: quoteToken, milestone_index: milestoneIndex });
      toast.success(`${amountEur} released to ${contractorName}`);
      onReleased();
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setLoading(false);
    }
  };

  const statusLabel = () => {
    if (status === 'proof_submitted') return t('milestone_proof_review');
    if (status === 'released') return t('ms_released_label');
    if (status === 'approved') return t('co_status_approved');
    return t('milestone_proof_pending');
  };

  return (
    <Sheet open={open} onClose={onClose}>
          <div className="flex justify-center pt-3 pb-1">
            <div className="w-10 h-1 rounded-full bg-border" />
          </div>

          <div className="shrink-0 flex items-center justify-between px-5 py-3 border-b border-border/50">
            <div>
              <h2 className="text-lg font-semibold text-ink font-display">{milestone.title}</h2>
              <p className="text-xs text-stone mt-0.5">{amountEur} · {contractorName}</p>
            </div>
            <Button variant="secondary" className="p-1.5 text-muted" type="button" onClick={onClose}><X size={18} /></Button>
          </div>

          <div className="flex-1 overflow-y-auto">
            <div className="px-5 pt-5 pb-10">

              <div className="flex items-center gap-2 mb-5">
                <div className={`w-2 h-2 rounded-full ${
                  status === 'released' ? 'bg-green-500'
                  : status === 'proof_submitted' || status === 'approved' ? 'bg-terracotta'
                  : 'bg-stone/30'
                }`} />
                <span className="text-xs font-medium text-stone uppercase tracking-wide">
                  {statusLabel()}
                </span>
              </div>

              {photos.length > 0 && (
                <div className="mb-5">
                  <p className="text-xs font-medium text-stone mb-2 uppercase tracking-wide">
                    Photos ({photos.length})
                  </p>
                  <div className="grid grid-cols-2 gap-2">
                    {photos.map((photo, pi) => (
                      <Button
                        key={pi}
                        type="button"
                        onClick={() => onOpenLightbox(photos, pi)}
                        className="aspect-[4/3] rounded-sm overflow-hidden border border-border"
                      >
                        <img src={photo} alt={`Photo ${pi + 1}`} className="w-full h-full object-cover" />
                      </Button>
                    ))}
                  </div>
                </div>
              )}

              {update?.note && (
                <div className="mb-5 bg-cream rounded-sm px-4 py-3 border border-border">
                  <p className="text-[10px] font-medium text-stone uppercase tracking-wide mb-1">Contractor note</p>
                  <p className="text-sm text-ink leading-relaxed">"{update.note}"</p>
                </div>
              )}

              {milestone.description && (
                <div className="mb-5">
                  <p className="text-[10px] font-medium text-stone uppercase tracking-wide mb-1">Description</p>
                  <p className="text-sm text-ink leading-relaxed">{milestone.description}</p>
                </div>
              )}

              <div className="bg-cream rounded-sm px-4 py-3 border border-border mb-5">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-stone">Phase amount</span>
                  <span className="font-semibold text-ink">{amountEur}</span>
                </div>
                <div className="flex justify-between items-center text-sm mt-2">
                  <span className="text-stone">To</span>
                  <span className="font-medium text-ink">{contractorName}</span>
                </div>
                <div className="flex justify-between items-center text-sm mt-2">
                  <span className="text-stone">From</span>
                  <span className="font-medium text-ink">Your Leo escrow</span>
                </div>
              </div>

              {canRelease && (status === 'proof_submitted' || status === 'approved') && !showConfirm && (
                <div className="space-y-2">
                  <Button
                    type="button"
                    onClick={() => setShowConfirm(true)}
                    className="w-full flex items-center justify-center gap-2 py-4 rounded-sm text-white text-[15px] font-semibold active:scale-[0.98] transition-transform"
                    style={{ background: 'var(--color-teal)' }}
                  >
                    <Check size={15} strokeWidth={2.5} />
                    {t('ms_approve_release', { amount: amountEur })}
                  </Button>
                  <Button variant="ghost" fullWidth className="text-stone text-center" type="button"
                    onClick={navigateToChat}>{t('ms_not_happy', { name: contractorName })}</Button>
                </div>
              )}

              {!canRelease && (status === 'proof_submitted' || status === 'approved') && (
                <div className="py-3 px-4 rounded-sm bg-cream border border-border text-center">
                  <p className="text-sm text-stone">{t('ms_sheet_contractor_cannot')}</p>
                </div>
              )}

              {canRelease && (status === 'proof_submitted' || status === 'approved') && showConfirm && (
                <div ref={confirmRef} className="rounded-sm border border-amber-200 bg-amber-50/50 px-4 py-4">
                  <p className="text-sm font-medium text-ink mb-1">{t('ms_confirm_title')}</p>
                  <p className="text-xs text-stone mb-4 leading-relaxed">
                    {t('ms_confirm_body', { amount: amountEur, name: contractorName })}
                  </p>
                  {error && <p className="text-xs text-red-500 mb-3">{error}</p>}
                  <div className="flex gap-2">
                    <Button
                      type="button"
                      onClick={() => { setShowConfirm(false); setError(''); }}
                      className="flex-1 py-3 rounded-sm border border-border text-sm text-stone font-medium"
                    >
                      {t('ms_confirm_back')}
                    </Button>
                    <Button className="flex-1 disabled:opacity-60" type="button"
                      onClick={handleRelease}
                      disabled={loading}
                      style={{ background: 'var(--color-teal)' }}>{loading ? <Loader2 size={14} className="animate-spin" /> : <Check size={14} strokeWidth={2.5} />}
                      {loading ? t('ms_sending') : t('ms_confirm_release')}</Button>
                  </div>
                </div>
              )}

              {status === 'released' && (
                <div className="flex items-center gap-2 py-3 px-4 rounded-sm bg-green-50 border border-green-200">
                  <Check size={16} className="text-green-600" />
                  <p className="text-sm text-green-800 font-medium">{t('ms_released_label')}</p>
                </div>
              )}
            </div>
          </div>
        </Sheet>
  );
}
