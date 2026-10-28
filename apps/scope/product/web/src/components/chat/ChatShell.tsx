import { useEffect, useRef, useState, useCallback, type ReactNode } from 'react';
import { Check, X, MessageCircle, Clock } from 'lucide-react';
import type { Message } from '../../types';
import type { ChatUiStatus, PreviewState } from '../../hooks/useChat';
import type { DrawerState } from '../../lib/api';
import type { ComposingType } from './ChatInput';
import { clsx } from '../../lib/utils';
import ChatMessages from './ChatMessages';
import ChatInput from './ChatInput';
import ActionBar from './ActionBar';
import PreviewPanel from './PreviewPanel';
import { Button } from '@scope/ui';

interface ChatShellProps {
  title: string;
  /** Optional element rendered left of the title in the header row (e.g. back button) */
  headerLeft?: ReactNode;
  /** Optional element rendered right-aligned in the header row (e.g. language toggle) */
  headerRight?: ReactNode;
  messages: Message[];
  isThinking: boolean;
  status: ChatUiStatus;
  previewState: PreviewState;
  previewContent: ReactNode;
  /** Shown behind vellum in empty state — same component as previewContent but with sample data */
  placeholderContent?: ReactNode;
  customDrawerContent?: ReactNode;
  onSendText: (text: string, photoFiles?: File[]) => void;
  onSendVoice: (blob: Blob, duration: number, waveform: number[], photoFiles?: File[]) => void;
  onConfirm: () => void;
  confirmLabel: string;
  previewLabelClosed?: string;
  previewLabelOpen?: string;
  confirmed?: boolean;
  drawerState?: DrawerState | null;
  onDrawerAction?: (actionId: string) => void;
  onComposingChange?: (composing: boolean, type: ComposingType) => void;
  /** Glass pill label for the empty preview state */
  emptyPreviewLabel?: string;
  /** Rotating labels inside the glass pill while the quote is updating */
  previewThinkingLabels?: string[];
  /** Rendered immediately after the first message — used for inline action chips (e.g. language switch) */
  afterFirstMessageSlot?: ReactNode;
  /** Contained mode: render inside parent instead of fixed fullscreen. Skips body scroll lock. */
  contained?: boolean;
  /** Start with the preview panel open — used in edit mode to show the profile immediately */
  initialPreviewOpen?: boolean;
  /** Controls which confirmation modal is shown — 'job' (default) or 'profile' */
  confirmMode?: 'job' | 'profile';
  /** Increment to programmatically close the mobile preview panel (e.g. after saving inline edits) */
  closePreviewCount?: number;
}

/** Post-submit confirmation modal — adapts to job post vs. profile save */
const SubmitConfirmModal = ({
  mode,
  onDismiss,
}: {
  mode: 'job' | 'profile';
  onDismiss: () => void;
}) => {
  const isProfile = mode === 'profile';

  return (
  <div
    className="fixed inset-0 z-50 flex items-end justify-center bg-ink/50 backdrop-blur-sm animate-in fade-in duration-300"
    onClick={onDismiss}
  >
    <div
      className="w-full max-w-lg bg-cream rounded-t-3xl shadow-2xl animate-in slide-in-from-bottom duration-400 overflow-hidden"
      onClick={(e) => e.stopPropagation()}
    >
      {/* Success strip */}
      <div className="bg-green h-1.5 w-full" />

      <div className="px-6 pt-6 pb-8">
        {/* Icon + heading */}
        <div className="flex flex-col items-center text-center mb-6">
          <div className="w-16 h-16 rounded-full bg-green/10 flex items-center justify-center mb-4 relative">
            <Check size={32} className="text-green" strokeWidth={2.5} />
            {/* Subtle pulse ring */}
            <span className="absolute inset-0 rounded-full bg-green/20 animate-ping" style={{ animationDuration: '1.4s', animationIterationCount: 2 }} />
          </div>
          <h2 className="font-display text-2xl font-semibold text-ink mb-2">
            {isProfile ? 'Profile saved!' : 'Job posted!'}
          </h2>
          <p className="text-stone text-[15px] leading-relaxed max-w-sm">
            {isProfile
              ? 'Your profile is live. Homeowners in your area can now find and contact you.'
              : 'Your brief has been submitted. Tradespeople in your area will review it and reach out if they\'re a good match.'}
          </p>
        </div>

        {/* WhatsApp callout */}
        <div className="flex items-start gap-3 bg-[#E8F8F2] rounded-sm px-4 py-3.5 mb-6">
          <MessageCircle size={20} className="text-[#25D366] shrink-0 mt-0.5" fill="#25D366" />
          <div>
            <p className="text-sm font-semibold text-ink mb-0.5">Expect a message on WhatsApp</p>
            <p className="text-xs text-stone leading-relaxed">
              {isProfile
                ? "We'll confirm your profile and send job leads directly to your WhatsApp."
                : "We'll send you updates, quotes, and contractor responses directly to your WhatsApp. Keep an eye out."}
            </p>
          </div>
        </div>

        {/* What happens next */}
        <div className="space-y-2.5 mb-6">
          {(isProfile
            ? [
                { icon: Clock, text: 'Homeowners typically reach out within a few hours' },
                { icon: Check, text: "You'll review each job before committing" },
              ]
            : [
                { icon: Clock, text: 'Tradespeople typically respond within a few hours' },
                { icon: Check, text: "You'll get to review each contractor before choosing" },
              ]
          ).map(({ icon: Icon, text }, i) => (
            <div key={i} className="flex items-center gap-2.5 text-sm text-stone">
              <span className="w-5 h-5 rounded-full bg-border flex items-center justify-center shrink-0">
                <Icon size={11} className="text-stone" />
              </span>
              {text}
            </div>
          ))}
        </div>

        <Button size="lg" fullWidth className="py-3.5 active:scale-[0.98] duration-150" type="button"
          onClick={onDismiss}>Done</Button>
      </div>
    </div>
  </div>
  );
};

const FullscreenOverlay = ({
  drawerState,
  content,
  onAction,
  onDismiss,
}: {
  drawerState: DrawerState;
  content: ReactNode;
  onAction: () => void;
  onDismiss: () => void;
}) => {
  const isHighlight = drawerState.accent === 'highlight';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-sm animate-in fade-in duration-300"
      onClick={onDismiss}
    >
      <div
        className={clsx(
          'relative w-[90vw] max-w-md max-h-[80vh] overflow-y-auto rounded-sm bg-cream shadow-2xl',
          'border-2 animate-in zoom-in-95 duration-300',
          isHighlight ? 'border-terracotta' : 'border-border',
        )}
        onClick={(e) => e.stopPropagation()}
      >
        <Button variant="secondary" className="absolute top-3 right-3 p-1.5 rounded-full text-muted" type="button"
          onClick={onDismiss}
          aria-label="Dismiss"><X size={18} /></Button>

        {drawerState.status_text && (
          <div
            className={clsx(
              'px-6 pt-5 pb-0 text-xs font-semibold uppercase tracking-wide',
              isHighlight ? 'text-terracotta' : 'text-stone',
            )}
          >
            {drawerState.status_text}
          </div>
        )}

        <div className="px-6 pt-4 pb-2">
          {content}
        </div>

        {drawerState.action_label && (
          <div className="px-6 pt-2 pb-6">
            <Button
              type="button"
              onClick={onAction}
              className={clsx(
                'w-full py-3 rounded-sm text-base font-semibold transition-colors inline-flex items-center justify-center gap-2',
                isHighlight
                  ? 'bg-terracotta text-white hover:bg-terracotta-dark'
                  : 'bg-terracotta text-white hover:bg-terracotta-dark',
              )}
            >
              <Check size={18} aria-hidden />
              {drawerState.action_label}
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

const BannerOverlay = ({
  drawerState,
  content,
  onAction,
  onDismiss,
}: {
  drawerState: DrawerState;
  content: ReactNode;
  onAction: () => void;
  onDismiss: () => void;
}) => {
  const isHighlight = drawerState.accent === 'highlight';

  return (
    <div className="absolute inset-x-0 top-0 z-30 p-3 animate-in slide-in-from-top duration-300">
      <div
        className={clsx(
          'rounded-sm bg-cream shadow-lg border overflow-hidden',
          isHighlight
            ? 'border-terracotta shadow-[0_4px_16px_rgba(193,98,61,0.2)]'
            : 'border-border',
        )}
      >
        <div className="flex items-start gap-3 p-4">
          <div className="flex-1 min-w-0">
            {drawerState.status_text && (
              <p
                className={clsx(
                  'text-xs font-semibold uppercase tracking-wide mb-1',
                  isHighlight ? 'text-terracotta' : 'text-stone',
                )}
              >
                {drawerState.status_text}
              </p>
            )}
            <div className="text-sm">{content}</div>
          </div>
          <Button variant="secondary" className="shrink-0 p-1 rounded-full text-muted" type="button"
            onClick={onDismiss}
            aria-label="Dismiss"><X size={16} /></Button>
        </div>
        {drawerState.action_label && (
          <div className="px-4 pb-3">
            <Button variant="terracotta" fullWidth type="button"
              onClick={onAction}><Check size={14} aria-hidden />
              {drawerState.action_label}</Button>
          </div>
        )}
      </div>
    </div>
  );
};

const ChatShell = ({
  title,
  headerLeft,
  headerRight,
  messages,
  isThinking,
  status,
  previewState,
  previewContent,
  placeholderContent,
  customDrawerContent,
  onSendText,
  onSendVoice,
  onConfirm,
  confirmLabel,
  previewLabelClosed = 'Preview',
  previewLabelOpen = 'Close preview',
  confirmed = false,
  drawerState,
  onDrawerAction,
  onComposingChange,
  emptyPreviewLabel,
  previewThinkingLabels,
  afterFirstMessageSlot,
  contained = false,
  initialPreviewOpen = false,
  confirmMode = 'job',
  closePreviewCount = 0,
}: ChatShellProps) => {
  const [previewOpen, setPreviewOpen] = useState(initialPreviewOpen);

  // Close preview whenever closePreviewCount increments (e.g. after saving inline edits)
  const prevCloseCountRef = useRef(closePreviewCount);
  useEffect(() => {
    if (closePreviewCount !== prevCloseCountRef.current) {
      prevCloseCountRef.current = closePreviewCount;
      setPreviewOpen(false);
    }
  }, [closePreviewCount]);
  const [overlayDismissed, setOverlayDismissed] = useState(false);
  const [submitModalDismissed, setSubmitModalDismissed] = useState(false);
  const [bottomPad, setBottomPad] = useState(180);
  const bottomRef = useRef<HTMLDivElement>(null);
  const prevAutoOpenRef = useRef(false);
  const prevDisplayRef = useRef<string | undefined>(undefined);
  const prevConfirmedRef = useRef(false);

  const measureBottom = useCallback(() => {
    const el = bottomRef.current;
    if (!el) return;
    setBottomPad(Math.ceil(el.getBoundingClientRect().height) + 24);
  }, []);

  useEffect(() => {
    const el = bottomRef.current;
    if (!el) return;
    measureBottom();
    const ro = new ResizeObserver(measureBottom);
    ro.observe(el);
    return () => ro.disconnect();
  }, [measureBottom]);

  useEffect(() => {
    if (contained) return;
    const html = document.documentElement;
    const body = document.body;
    const savedHtml = html.style.cssText;
    const savedBody = body.style.cssText;
    body.style.position = 'fixed';
    body.style.width = '100%';
    body.style.overflow = 'hidden';
    html.style.overflow = 'hidden';
    return () => {
      html.style.cssText = savedHtml;
      body.style.cssText = savedBody;
    };
  }, [contained]);

  // Auto-open drawer when Hermes requests it
  useEffect(() => {
    if (drawerState?.auto_open && !prevAutoOpenRef.current) {
      setPreviewOpen(true);
    }
    prevAutoOpenRef.current = !!drawerState?.auto_open;
  }, [drawerState?.auto_open]);

  // Preview only opens when Hermes explicitly sets auto_open via set_drawer.
  // We intentionally do NOT auto-open on previewState === 'ready' —
  // the agent controls when the first draft is ready to show.

  // Reset dismissed state when display mode changes (new overlay request from Hermes)
  useEffect(() => {
    if (drawerState?.display !== prevDisplayRef.current) {
      setOverlayDismissed(false);
    }
    prevDisplayRef.current = drawerState?.display;
  }, [drawerState?.display]);

  // Show submit confirmation modal when confirmed transitions false → true
  useEffect(() => {
    if (confirmed && !prevConfirmedRef.current) {
      setSubmitModalDismissed(false);
    }
    prevConfirmedRef.current = confirmed;
  }, [confirmed]);

  const confirmDisabled = status === 'needs-info';
  const panelContent = customDrawerContent ?? previewContent;

  const displayMode = drawerState?.display || 'inline';
  const showOverlay = !overlayDismissed && drawerState && displayMode !== 'inline';
  const showSubmitModal = confirmed && !submitModalDismissed;

  const handleOverlayAction = () => {
    if (drawerState?.action_id && onDrawerAction) {
      onDrawerAction(drawerState.action_id);
    } else {
      onConfirm();
    }
    setOverlayDismissed(true);
  };

  const handleOverlayDismiss = () => {
    setOverlayDismissed(true);
  };

  return (
    <div
      className="flex flex-col overflow-hidden bg-cream md:flex-row"
      style={contained
        ? { position: 'relative', width: '100%', height: '100%' }
        : { position: 'fixed', inset: 0, zIndex: 10 }
      }
    >
      <section className="flex flex-col flex-1 min-h-0 min-w-0 md:w-1/3 md:max-w-md md:border-r border-border">
        <header
          className="shrink-0 px-4 pb-3 border-b border-border bg-cream/95 backdrop-blur-sm relative z-20"
          style={{ paddingTop: 'max(1rem, env(safe-area-inset-top, 1rem))' }}
        >
          <div className="grid items-center h-9" style={{ gridTemplateColumns: '1fr auto 1fr' }}>
            <div className="flex items-center">{headerLeft ?? <span />}</div>
            <h1 className="font-display text-base font-semibold text-ink text-center">{title}</h1>
            <div className="flex items-center justify-end">{headerRight ?? <span />}</div>
          </div>
        </header>

        {/* Content zone — messages fill this; controls overlay the bottom */}
        <div className="flex-1 min-h-0 relative overflow-hidden">
          <ChatMessages messages={messages} isThinking={isThinking} bottomPadding={bottomPad} afterFirstMessageSlot={afterFirstMessageSlot} />

          <PreviewPanel previewState={previewState} mobile open={previewOpen} placeholderContent={placeholderContent} emptyLabel={emptyPreviewLabel} thinkingLabels={previewThinkingLabels}>
            {panelContent}
          </PreviewPanel>

          {showOverlay && displayMode === 'banner' && (
            <BannerOverlay
              drawerState={drawerState}
              content={panelContent}
              onAction={handleOverlayAction}
              onDismiss={handleOverlayDismiss}
            />
          )}

          {/* Bottom controls — overlays the chat so messages scroll behind */}
          <div ref={bottomRef} className="absolute inset-x-0 bottom-0 z-20 pointer-events-none">
            <div
              className="absolute inset-0 pointer-events-none"
              style={{
                background: 'linear-gradient(to bottom, transparent, rgba(250,248,244,0.85) 36%, rgba(250,248,244,0.98))',
              }}
            />
            <div className="relative pointer-events-auto">
              <ActionBar
                status={status}
                previewOpen={previewOpen}
                onTogglePreview={() => setPreviewOpen((o) => !o)}
                previewLabelOpen={previewLabelOpen}
                previewLabelClosed={previewLabelClosed}
                confirmLabel={confirmLabel}
                onConfirm={onConfirm}
                confirmDisabled={confirmDisabled}
                confirmed={confirmed}
                drawerState={drawerState}
                onDrawerAction={onDrawerAction}
              />

              <ChatInput
                onSendText={onSendText}
                onSendVoice={onSendVoice}
                onComposingChange={onComposingChange}
              />
            </div>
          </div>
        </div>
      </section>

      <PreviewPanel previewState={previewState} className="flex-1" placeholderContent={placeholderContent} emptyLabel={emptyPreviewLabel} thinkingLabels={previewThinkingLabels}>
        {panelContent}
      </PreviewPanel>

      {showOverlay && displayMode === 'fullscreen' && (
        <FullscreenOverlay
          drawerState={drawerState}
          content={panelContent}
          onAction={handleOverlayAction}
          onDismiss={handleOverlayDismiss}
        />
      )}

      {showSubmitModal && (
        <SubmitConfirmModal mode={confirmMode} onDismiss={() => setSubmitModalDismissed(true)} />
      )}
    </div>
  );
};

export default ChatShell;
