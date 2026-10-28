import { Check, Eye, EyeOff } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { Button, ComposerActionStrip } from '@scope/ui';
import type { ChatUiStatus } from '../../hooks/useChat';
import type { DrawerState } from '../../lib/api';
import { clsx } from '../../lib/utils';

interface ActionBarProps {
  status: ChatUiStatus;
  previewOpen: boolean;
  onTogglePreview: () => void;
  previewLabelOpen: string;
  previewLabelClosed: string;
  confirmLabel: string;
  onConfirm: () => void;
  confirmDisabled: boolean;
  confirmed?: boolean;
  drawerState?: DrawerState | null;
  onDrawerAction?: (actionId: string) => void;
}

const ActionBar = ({
  status,
  previewOpen,
  onTogglePreview,
  confirmLabel,
  onConfirm,
  confirmDisabled,
  confirmed = false,
  drawerState,
  onDrawerAction,
}: ActionBarProps) => {
  const { t } = useTranslation();
  const statusLabel: Record<ChatUiStatus, string> = {
    'needs-info': t('status_needs_info'),
    workable: t('status_workable'),
    solid: t('status_solid'),
  };
  const isHighlight = drawerState?.accent === 'highlight';
  const dynamicStatus = drawerState?.status_text;
  const dynamicActionLabel = drawerState?.action_label;
  const dynamicActionId = drawerState?.action_id;

  const handleActionClick = () => {
    if (dynamicActionId && onDrawerAction) {
      onDrawerAction(dynamicActionId);
    } else {
      onConfirm();
    }
  };

  const effectiveActionLabel = dynamicActionLabel || confirmLabel;
  const showActionButton = !confirmed && effectiveActionLabel;

  return (
    <ComposerActionStrip highlight={isHighlight} elevated={previewOpen && !isHighlight}>
        {/* Status label — truncated to prevent overflow */}
        <span
          className={clsx(
            'flex-1 text-sm min-w-0 truncate transition-colors duration-300',
            confirmed && 'text-green font-semibold',
            !confirmed && dynamicStatus && isHighlight && 'text-terracotta font-semibold',
            !confirmed && dynamicStatus && !isHighlight && 'text-stone font-medium',
            !confirmed && !dynamicStatus && status === 'needs-info' && 'text-muted',
            !confirmed && !dynamicStatus && status === 'workable' && 'text-stone font-medium',
            !confirmed && !dynamicStatus && status === 'solid' && 'text-ink font-semibold',
          )}
        >
          {confirmed ? (
            <span className="inline-flex items-center gap-1.5">
              <Check size={14} className="text-green shrink-0" aria-hidden />
              {t('status_submitted')}
            </span>
          ) : (
            dynamicStatus || statusLabel[status]
          )}
        </span>

        {/* Preview toggle — eye icon: open eye when previewing, closed eye when not */}
        <Button variant="ghost" size="icon"
          type="button"
          onClick={onTogglePreview}
          className={clsx(
            'shrink-0 w-8 h-8 flex items-center justify-center rounded-sm transition-colors',
            previewOpen
              ? 'text-terracotta bg-terracotta-light hover:bg-terracotta-light/80'
              : 'text-stone hover:text-ink hover:bg-border/50',
          )}
          aria-label={previewOpen ? t('aria_close_preview') : t('aria_preview_brief')}
          aria-expanded={previewOpen}
        >
          {previewOpen ? <Eye size={18} /> : <EyeOff size={18} />}
        </Button>

        {showActionButton && (
          <Button
            type="button"
            disabled={!dynamicActionLabel && confirmDisabled}
            onClick={handleActionClick}
            className={clsx(
              'shrink-0 px-3 py-1.5 rounded-sm text-sm font-semibold transition-all duration-150 inline-flex items-center gap-1',
              'active:scale-95',
              !dynamicActionLabel && confirmDisabled
                ? 'bg-border text-muted cursor-not-allowed'
                : 'bg-terracotta text-white hover:bg-terracotta-dark shadow-sm hover:shadow',
            )}
          >
            <Check size={14} aria-hidden />
            {effectiveActionLabel}
          </Button>
        )}
    </ComposerActionStrip>
  );
};

export default ActionBar;
