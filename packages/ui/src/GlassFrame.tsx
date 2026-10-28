import type { ReactNode } from 'react';

/**
 * GlassFrame — Leo's browser-chrome mockup component.
 *
 * The single source of truth for the glass frame structure used across:
 *   - React app (import this component)
 *   - Static HTML (leo-glass-frame.css + matching HTML pattern)
 *
 * The dots are always terra / amber / teal — Leo brand colours.
 * Style comes from leo-glass-frame.css (loaded globally).
 *
 * Usage:
 *   <GlassFrame url="leo.casa/brief/LCS-4821">
 *     <BriefCanvas b={brief} />
 *   </GlassFrame>
 *
 *   <GlassFrame dark url="leo.casa/scope/hwc-2026">
 *     <QuoteCanvas scope={scope} />
 *   </GlassFrame>
 */
interface GlassFrameProps {
  url: string;
  dark?: boolean;
  children: ReactNode;
  className?: string;
}

export function GlassFrame({ url, dark = false, children, className }: GlassFrameProps) {
  return (
    <div className={['glass-frame', dark ? 'glass-frame--dark' : '', className].filter(Boolean).join(' ')}>
      <div className="glass-frame-bar">
        <div className="glass-frame-dots">
          <span />
          <span />
          <span />
        </div>
        <div className="glass-frame-url">
          <svg width="8" height="8" viewBox="0 0 24 24" style={{ fill: 'none', strokeWidth: 2.5, flexShrink: 0 }}>
            <rect x="3" y="11" width="18" height="11" rx="2" />
            <path d="M7 11V7a5 5 0 0110 0v4" />
          </svg>
          <span className="glass-frame-url-text">{url}</span>
        </div>
      </div>
      <div className="glass-frame-body">
        {children}
      </div>
    </div>
  );
}
