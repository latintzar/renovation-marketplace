/**
 * ProfileActionDrawer — Bottom bar on claimed profile canvases.
 * Shows Edit and "Looks good" (approve) actions for the contractor.
 */

import { useNavigate } from 'react-router-dom';
import { Pencil, Check } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button } from '@scope/ui';

interface ProfileActionDrawerProps {
  contractorId: string;
  onSubmit: () => void;
}

export function ProfileActionDrawer({ contractorId, onSubmit }: ProfileActionDrawerProps) {
  const { t } = useTranslation();
  const navigate = useNavigate();

  const handleEdit = () => {
    try {
      const discrepancyRaw = localStorage.getItem(`phone_discrepancy_${contractorId}`);
      const discrepancy = discrepancyRaw ? JSON.parse(discrepancyRaw) : null;
      sessionStorage.setItem('leo_handoff', JSON.stringify({
        edit: true,
        contractorId,
        ...(discrepancy ? { phone_discrepancy: discrepancy } : {}),
      }));
    } catch {
      // sessionStorage unavailable
    }
    navigate(`/onboard/pro?edit=1&contractorId=${encodeURIComponent(contractorId)}`);
  };

  return (
    <div className="shrink-0 border-t border-border bg-cream/95 backdrop-blur-sm px-4 pt-3 pb-safe">
      <div className="max-w-lg mx-auto flex items-center gap-3">
        <Button variant="secondary" className="flex-1 text-stone hover:border-terracotta hover:text-terracotta active:scale-[0.98] duration-150" type="button"
          onClick={handleEdit}><Pencil size={15} />
          {t('canvas_want_to_edit')}</Button>

        <Button className="flex-[2] bg-green shadow-sm active:scale-[0.98] duration-150" type="button"
          onClick={onSubmit}><Check size={15} strokeWidth={2.5} />
          {t('canvas_looks_good')}</Button>
      </div>
      <p className="text-center text-xs text-muted mt-2 pb-1">
        {t('canvas_update_anytime')}
      </p>
    </div>
  );
}
