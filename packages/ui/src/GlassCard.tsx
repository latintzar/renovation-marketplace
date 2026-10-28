/**
 * GlassCard — Frosted glass card used over gradient backgrounds.
 *
 * The canonical "glassmorphic panel" from Leo's brand system.
 * Used in:
 *   - Auth gate screens (wrong account, wrong role, login prompt)
 *   - Summary cards over hero gradients
 *   - Notification panels
 *
 * Matches the `brand-effects.css` vellum/glass style:
 *   background: rgba(255,255,255,0.1), backdrop-blur(12px)
 *
 * Usage:
 *   <GlassCard>
 *     <p className="text-sm text-cream">You're connected as a contractor</p>
 *   </GlassCard>
 *
 *   <GlassCard variant="light">
 *     Content on lighter gradient
 *   </GlassCard>
 */

import type { ReactNode, CSSProperties } from 'react';

type GlassVariant = 'dark' | 'light';

interface GlassCardProps {
  children: ReactNode;
  variant?: GlassVariant;
  className?: string;
  style?: CSSProperties;
  /** Padding preset: 'sm' (12px), 'md' (16px default), 'lg' (24px) */
  padding?: 'sm' | 'md' | 'lg';
}

const PADDING_CLASSES: Record<NonNullable<GlassCardProps['padding']>, string> = {
  sm: 'px-3 py-3',
  md: 'px-4 py-4',
  lg: 'px-6 py-5',
};

const VARIANT_STYLES: Record<GlassVariant, CSSProperties> = {
  dark: { background: 'rgba(255,255,255,0.1)', backdropFilter: 'blur(12px)', WebkitBackdropFilter: 'blur(12px)' },
  light: { background: 'rgba(255,255,255,0.65)', backdropFilter: 'blur(10px)', WebkitBackdropFilter: 'blur(10px)' },
};

export function GlassCard({
  children,
  variant = 'dark',
  className = '',
  style,
  padding = 'md',
}: GlassCardProps) {
  return (
    <div
      className={`rounded-sm ${PADDING_CLASSES[padding]} ${className}`}
      style={{ ...VARIANT_STYLES[variant], ...style }}
    >
      {children}
    </div>
  );
}
