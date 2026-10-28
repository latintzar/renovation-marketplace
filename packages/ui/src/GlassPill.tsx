import type { ReactNode } from 'react';

/**
 * GlassPill — glassmorphic status indicator with a breathing terra dot.
 *
 * Shown during Leo's "thinking" / "updating" states over the canvas.
 * Style from brand-effects.css (leo-glass-pill, leo-glass-pill-dot).
 *
 * Usage:
 *   <GlassPill>Updating brief…</GlassPill>
 *   <GlassPill dot={false}>Ready</GlassPill>
 */
interface GlassPillProps {
  children: ReactNode;
  dot?: boolean;
  className?: string;
}

export function GlassPill({ children, dot = true, className }: GlassPillProps) {
  return (
    <span className={['leo-glass-pill', className].filter(Boolean).join(' ')}>
      {dot && <span className="leo-glass-pill-dot" />}
      {children}
    </span>
  );
}
