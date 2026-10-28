import { useEffect, useRef } from 'react';
import { Camera, Image, FileText } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { clsx } from '../../lib/utils';
import { Button } from '@scope/ui';

interface AttachmentSheetProps {
  open: boolean;
  onClose: () => void;
  onTakePhoto: () => void;
  onChooseGallery: () => void;
  onChooseFile: () => void;
}

const AttachmentSheet = ({
  open,
  onClose,
  onTakePhoto,
  onChooseGallery,
  onChooseFile,
}: AttachmentSheetProps) => {
  const { t } = useTranslation();
  const sheetRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [open, onClose]);

  if (!open) return null;

  const options = [
    { label: t('attachment_take_photo'), icon: Camera, action: onTakePhoto },
    { label: t('attachment_photo_library'), icon: Image, action: onChooseGallery },
    { label: t('attachment_choose_file'), icon: FileText, action: onChooseFile },
  ];

  return (
    <div
      className="fixed inset-0 z-50 flex items-end justify-center"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label="Add attachment"
    >
      {/* Scrim */}
      <div className="absolute inset-0 bg-black/30 anim-fade-up" style={{ animationDuration: '.15s' }} />

      {/* Sheet */}
      <div
        ref={sheetRef}
        className="relative z-10 w-full max-w-md mx-3 mb-3 anim-slide-up"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="rounded-sm bg-card shadow-lg overflow-hidden">
          {options.map(({ label, icon: Icon, action }, i) => (
            <Button
              key={label}
              type="button"
              onClick={() => { action(); onClose(); }}
              className={clsx(
                'w-full flex items-center gap-4 px-5 py-4 text-[15px] font-medium text-ink hover:bg-cream-dark active:bg-cream-dark transition-colors',
                i > 0 && 'border-t border-border',
              )}
            >
              <Icon size={22} className="text-stone shrink-0" aria-hidden />
              {label}
            </Button>
          ))}
        </div>

        <Button size="lg" fullWidth className="mt-2 bg-card shadow-lg text-[15px] text-stone active:bg-cream-dark" type="button"
          onClick={onClose}>{t('cancel')}</Button>
      </div>
    </div>
  );
};

export default AttachmentSheet;
