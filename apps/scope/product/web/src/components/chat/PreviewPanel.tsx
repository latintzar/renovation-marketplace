import { useState, useEffect, type ReactNode } from 'react';
import type { PreviewState } from '../../hooks/useChat';
import { clsx } from '../../lib/utils';

/*
 * Leo Brand Vellum — uses the .brand-* CSS classes from
 * scope-app/public/brand-effects.css (single source of truth,
 * loaded as a static <link> that bypasses Vite/LightningCSS).
 *
 * Structure (matches brand-book.html exactly):
 *   .brand-overlay
 *     .brand-glass.brand-glass--vellum
 *     .brand-bleed.brand-bleed--strong
 *     .brand-grain-png
 *     .brand-grain-svg
 *
 * Content always goes behind the vellum so bold shapes ghost through.
 * In the empty state, `placeholderContent` (same component as children but
 * with sample data) provides shapes that match the real preview layout.
 */

const DEFAULT_BUILDING_LABELS = [
  'Updating your quote…',
  'Drafting line items…',
  'Checking market rates…',
];

/**
 * Brand Vellum overlay — identical DOM to brand-book.html.
 * Visual styles from /brand-effects.css (shared, not processed by Vite).
 */
const VellumOverlay = ({ pulse }: { pulse: boolean }) => (
  <div
    className={clsx('brand-overlay', pulse && 'leo-vellum-pulse')}
    aria-hidden
  >
    <div className="brand-glass brand-glass--vellum" />
    <div className="brand-bleed brand-bleed--strong" />
    <div className="brand-grain-png" />
    <div className="brand-grain-svg" />
  </div>
);

interface PreviewPanelProps {
  previewState: PreviewState;
  children: ReactNode;
  /** Shown behind vellum in empty state — should be the same preview component with sample data */
  placeholderContent?: ReactNode;
  className?: string;
  mobile?: boolean;
  /** Inline mode for gallery / standalone display — no responsive hiding, no slide-up */
  inline?: boolean;
  open?: boolean;
  overlayLabel?: string;
  emptyLabel?: string;
  /** Rotating shimmer labels while Hermes is working (i18n from page) */
  thinkingLabels?: string[];
}

const PreviewPanel = ({
  previewState,
  children,
  placeholderContent,
  className,
  mobile = false,
  inline = false,
  open = true,
  overlayLabel,
  emptyLabel = 'Check back here as your brief builds up',
  thinkingLabels = DEFAULT_BUILDING_LABELS,
}: PreviewPanelProps) => {
  const isBuilding = previewState === 'building';
  const isEmpty = previewState === 'empty';
  const isEditing = previewState === 'editing';

  const [labelIdx, setLabelIdx] = useState(0);
  useEffect(() => {
    if (!isBuilding && !isEditing) return;
    const id = setInterval(() => setLabelIdx((i) => (i + 1) % Math.max(thinkingLabels.length, 1)), 3200);
    return () => clearInterval(id);
  }, [isBuilding, isEditing, thinkingLabels.length]);

  const inner = (() => {
    // What content goes behind the vellum:
    //   - no real data  → sample/placeholder always (empty or building)
    //   - has real data → real canvas (editing or ready)
    const hasContent = !isEmpty && !isBuilding;
    const showVellum = isEmpty || isBuilding || isEditing;

    return (
      // overflow-hidden is intentionally omitted: it would clip the vellum's
      // backdrop-filter. .brand-overlay already has overflow:hidden internally.
      <div className="relative h-full flex flex-col bg-cream min-h-[160px] isolate">

        {/* Content layer — always rendered; vellum sits on top when active */}
        <div className={clsx('absolute inset-0', !hasContent && 'select-none overflow-hidden')}
          aria-hidden={!hasContent}>
          {hasContent ? children : (placeholderContent ?? children)}
        </div>

        {/* Vellum overlay — shown whenever we're not in a clean "ready" state */}
        {showVellum && <VellumOverlay pulse={isEditing} />}

        {/* Status pill — centre of the panel when vellum is active */}
        {showVellum && (
          <div className="absolute inset-0 z-10 flex items-center justify-center pointer-events-none">
            {isEmpty ? (
              // Static: no data, not thinking
              <span className="leo-glass-pill select-none">
                {emptyLabel}
              </span>
            ) : (
              // Active: building (no data yet) or editing (updating existing data)
              <span className="leo-glass-pill select-none">
                <span className="leo-glass-pill-dot" />
                <span className="leo-shimmer-label">
                  {overlayLabel ?? thinkingLabels[labelIdx % thinkingLabels.length]}
                </span>
              </span>
            )}
          </div>
        )}
      </div>
    );
  })();

  if (inline) {
    return (
      <div className={clsx('flex flex-col h-full bg-cream', className)}>
        {inner}
      </div>
    );
  }

  if (mobile) {
    return (
      <div
        className={clsx(
          'md:hidden absolute inset-0 z-10 bg-cream overflow-y-auto transition-transform duration-300 ease-[cubic-bezier(0.4,0,0.2,1)]',
          open ? 'translate-y-0' : 'translate-y-full pointer-events-none',
          className,
        )}
      >
        <div className="h-full">{inner}</div>
      </div>
    );
  }

  return (
    <div
      className={clsx(
        'hidden md:flex md:flex-col min-h-0 h-full bg-cream border-l border-border',
        className,
      )}
    >
      {inner}
    </div>
  );
};

export default PreviewPanel;
