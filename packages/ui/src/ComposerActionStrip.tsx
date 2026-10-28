import type { ReactNode } from 'react';

/**
 * Chrome for the horizontal action rail **directly above** the chat composer
 * (mic / text input). Matches the shell historically inlined in
 * `apps/web/src/components/chat/ActionBar.tsx` — extracted so Electron / internal
 * tools can mirror the same CSS in plain HTML (`composer-action-strip.css`).
 */
export interface ComposerActionStripProps {
  children: ReactNode;
  /** Terracotta border + glow (Scope chat drawer highlight). */
  highlight?: boolean;
  /** Subtle lift when preview drawer is open (non-highlight). */
  elevated?: boolean;
  className?: string;
  innerClassName?: string;
}

function cx(...parts: (string | false | undefined | null)[]) {
  return parts.filter(Boolean).join(' ');
}

export function ComposerActionStrip({
  children,
  highlight = false,
  elevated = false,
  innerClassName,
  className,
}: ComposerActionStripProps) {
  return (
    <div className={cx('shrink-0 px-3 pt-2 pb-0 relative z-20', className)}>
      <div
        className={cx(
          'flex items-center gap-2 px-3 py-2 rounded-sm border bg-cream transition-all duration-300',
          highlight
            ? 'border-terracotta shadow-[0_-2px_8px_rgba(193,98,61,0.15)]'
            : 'border-border',
          elevated && !highlight && 'shadow-[0_-2px_4px_rgba(0,0,0,0.04)]',
          innerClassName,
        )}
      >
        {children}
      </div>
    </div>
  );
}
