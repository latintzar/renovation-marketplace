/**
 * GradientScreen — Full-screen gradient background with noise texture.
 *
 * Used as the base for auth gates, login screens, and hero sections
 * across both the homeowner and contractor flows.
 *
 * Presets:
 *   homeowner — warm terra/orange palette (#f5e6d8 base)
 *   contractor — dark charcoal/terra palette (#141210 base)
 *   custom     — pass your own `style` prop
 *
 * Usage:
 *   <GradientScreen preset="homeowner">
 *     <p>Content over gradient</p>
 *   </GradientScreen>
 */

import type { CSSProperties, ReactNode } from 'react';

type GradientPreset = 'homeowner' | 'contractor';

const PRESETS: Record<GradientPreset, CSSProperties> = {
  homeowner: {
    backgroundColor: '#f5e6d8',
    backgroundImage: [
      'radial-gradient(ellipse 120% 90% at 30% 25%, #DA654D 0%, transparent 55%)',
      'radial-gradient(ellipse 100% 80% at 80% 65%, #e8a88e 0%, transparent 50%)',
      'radial-gradient(ellipse 90% 110% at 55% 90%, #c45c45 0%, transparent 50%)',
      'radial-gradient(ellipse 80% 70% at 15% 75%, #FAF8F4 0%, transparent 45%)',
      'linear-gradient(160deg, #FAF8F4, #f0dcc8 40%, #f5e6d8 100%)',
    ].join(', '),
    backgroundSize: '200% 200%, 180% 180%, 200% 200%, 160% 160%, 100% 100%',
    backgroundPosition: '40% 30%, 60% 70%, 50% 50%, 30% 60%, 0% 0%',
  },
  contractor: {
    backgroundColor: '#141210',
    backgroundImage: [
      'radial-gradient(ellipse 120% 80% at 25% 20%, #292524 0%, transparent 60%)',
      'radial-gradient(ellipse 100% 90% at 75% 70%, #DA654D 0%, transparent 55%)',
      'radial-gradient(ellipse 80% 100% at 50% 100%, #a0463a 0%, transparent 50%)',
      'radial-gradient(ellipse 90% 70% at 10% 80%, #1c1917 0%, transparent 50%)',
      'linear-gradient(160deg, #0f0e0c, #141210 40%, #1c1917 100%)',
    ].join(', '),
    backgroundSize: '200% 200%, 180% 180%, 200% 200%, 160% 160%, 100% 100%',
    backgroundPosition: '40% 30%, 60% 70%, 50% 50%, 30% 60%, 0% 0%',
  },
};

interface GradientScreenProps {
  children: ReactNode;
  preset?: GradientPreset;
  /** Override gradient entirely with custom inline styles */
  style?: CSSProperties;
  className?: string;
  /** Whether to show the noise texture overlay (default: true) */
  noise?: boolean;
}

export function GradientScreen({
  children,
  preset = 'homeowner',
  style,
  className = '',
  noise = true,
}: GradientScreenProps) {
  const backgroundStyle: CSSProperties = style ?? PRESETS[preset];

  return (
    <div
      className={`flex flex-col h-dvh overflow-hidden relative ${className}`}
      style={backgroundStyle}
    >
      {noise && (
        <div
          className="absolute inset-0 pointer-events-none"
          aria-hidden="true"
          style={{
            opacity: 0.45,
            mixBlendMode: 'overlay',
            backgroundImage: "url(\"data:image/svg+xml,%3Csvg viewBox='0 0 256 256' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E\")",
            backgroundSize: '200px 200px',
          }}
        />
      )}
      <div className="relative z-[1] flex flex-col flex-1">
        {children}
      </div>
    </div>
  );
}

/** Pre-composed gradient theme objects for direct use in inline `style` props. */
export const GRADIENT_THEMES = PRESETS;
