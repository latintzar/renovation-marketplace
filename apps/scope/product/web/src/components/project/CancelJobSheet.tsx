/**
 * CancelJobSheet — Multi-step cancel flow (Uber One style).
 * Calls POST /v1/projects/:token/cancel (JWT-authenticated via apiFetch).
 */

import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { toast } from 'sonner';
import { API_BASE, apiFetch } from '../../lib/api';
import { eur } from '../../lib/utils';
import { Button , Sheet } from '@scope/ui';

interface CancelJobSheetProps {
  open: boolean;
  onClose: () => void;
  totalCents: number;
  contractorName: string;
  quoteToken: string;
  onCancelled: () => void;
  navigateToChat: () => void;
}

export function CancelJobSheet({
  open, onClose, totalCents, contractorName, quoteToken, onCancelled, navigateToChat,
}: CancelJobSheetProps) {
  const { t } = useTranslation();
  const [step, setStep] = useState<1 | 2 | 3>(1);
  const [cancelling, setCancelling] = useState(false);

  useEffect(() => { if (open) setStep(1); }, [open]);

  const handleCancel = async () => {
    setCancelling(true);
    const resp = await apiFetch(`${API_BASE}/v1/projects/${quoteToken}/cancel`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({}),
    });
    if (resp.ok) {
      toast.success(t('cancel_sheet_toast_success'));
      onCancelled();
      onClose();
    } else {
      const err = await resp.json().catch(() => ({}));
      toast.error(err.detail || t('cancel_sheet_toast_error'));
    }
    setCancelling(false);
  };

  return (
    <Sheet open={open} onClose={onClose}>
{step === 1 && (
            <div className="px-6 pt-2 pb-10">
              <h2 className="text-xl font-semibold text-ink font-display mb-2">{t('cancel_sheet_step1_subtitle')}</h2>
              <p className="text-sm text-stone leading-relaxed mb-6">
                {t('cancel_sheet_step1_refund', { amount: eur(totalCents) })}
              </p>
              <div className="bg-white border border-border rounded-sm px-4 py-4 mb-6 space-y-3">
                {[
                  { icon: '✓', text: t('cancel_sheet_step1_item_refund', { amount: eur(totalCents) }) },
                  { icon: '⏱', text: t('cancel_sheet_step1_item_timeline') },
                  { icon: '📄', text: t('cancel_sheet_step1_item_agreement') },
                ].map(({ icon, text }) => (
                  <div key={text} className="flex items-start gap-3 text-sm">
                    <span className="text-base">{icon}</span>
                    <span className="text-stone leading-relaxed">{text}</span>
                  </div>
                ))}
              </div>
              <Button
                type="button"
                onClick={() => setStep(2)}
                className="w-full py-3.5 rounded-sm border border-border text-stone text-sm font-medium hover:border-stone hover:text-ink transition-colors"
              >
                {t('cancel_sheet_step1_continue')}
              </Button>
              <Button variant="ghost" fullWidth className="text-stone" type="button" onClick={onClose}>{t('cancel_sheet_step1_back')}</Button>
            </div>
          )}

          {step === 2 && (
            <div className="px-6 pt-2 pb-10">
              <h2 className="text-xl font-semibold text-ink font-display mb-2">{t('cancel_sheet_step2_subtitle', { name: contractorName })}</h2>
              <p className="text-sm text-stone leading-relaxed mb-6">
                {t('cancel_sheet_step2_body', { name: contractorName })}
              </p>
              <Button
                type="button"
                onClick={() => { onClose(); navigateToChat(); }}
                className="w-full py-4 rounded-sm text-white text-[15px] font-semibold mb-4 active:scale-[0.98] transition-transform"
                style={{ background: 'var(--color-teal)' }}
              >
                {t('cancel_sheet_step2_chat', { name: contractorName })}
              </Button>
              <Button
                type="button"
                onClick={() => setStep(3)}
                className="w-full py-3 text-sm font-medium text-red-500 hover:text-red-700 transition-colors"
              >
                {t('cancel_sheet_step2_skip')}
              </Button>
            </div>
          )}

          {step === 3 && (
            <div className="px-6 pt-2 pb-10">
              <h2 className="text-xl font-semibold text-ink font-display mb-2">{t('cancel_sheet_step3_subtitle')}</h2>
              <p className="text-sm text-stone leading-relaxed mb-6">
                {t('cancel_sheet_step3_body', { amount: eur(totalCents) })}
              </p>
              <Button size="lg" fullWidth className="text-[15px] mb-3 active:scale-[0.98] transition-transform" type="button"
                onClick={onClose}
                style={{ background: 'var(--color-teal)' }}>{t('cancel_sheet_step3_back')}</Button>
              <Button fullWidth className="text-red-500 hover:text-red-700" type="button"
                onClick={handleCancel}
                disabled={cancelling}>{cancelling ? t('cancel_sheet_step3_cancelling') : t('cancel_sheet_step3_confirm')}</Button>
            </div>
          )}
        </Sheet>
  );
}
