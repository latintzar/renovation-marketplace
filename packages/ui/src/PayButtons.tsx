import { Button } from './primitives';
/**
 * PayButton — Apple Pay and Google Pay standard buttons.
 *
 * Branding rules (non-negotiable per brand guidelines):
 * - Apple Pay: Apple logo + "Pay" in -apple-system (San Francisco). NO word "Apple".
 * - Google Pay: Google G logo (4-color) + "Pay" in Google Sans. NO word "Google".
 *
 * Two display variants:
 * - pill: solid black pill, small (used in milestone cards, inline lists)
 * - button: full-width 44px button (used in payment flows, materials card)
 *
 * React: import { PayButton } from '@scope/ui'
 * Static HTML: use .leo-pay-pill or .leo-pay-btn from brand-effects.css
 */

/* ─── SVGs ────────────────────────────────────────────── */

const AppleLogo = ({ size = 16, fill = 'currentColor' }: { size?: number; fill?: string }) => (
  <svg
    width={size}
    height={Math.round(size * 1.22)}
    viewBox="0 0 24 24"
    fill={fill}
    aria-hidden="true"
  >
    <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.8-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83" />
    <path d="M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
  </svg>
);

const GoogleGLogo = ({ size = 16 }: { size?: number }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" aria-hidden="true">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4" />
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05" />
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
  </svg>
);

/* ─── Shared pill/button shell ───────────────────────── */

const glassPillStyle: React.CSSProperties = {
  display: 'inline-flex',
  alignItems: 'center',
  gap: 5,
  padding: '7px 12px',
  background: '#000',
  border: 'none',
  borderRadius: 'var(--r-pill, 999px)',
  color: '#fff',
  cursor: 'default',
};

const glassBtnStyle: React.CSSProperties = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: 6,
  height: 44,
  width: '100%',
  background: '#000',
  border: 'none',
  borderRadius: 'var(--radius-md)',
  cursor: 'pointer',
};

/* ─── Apple Pay ─────────────────────────────────────── */

interface ApplePayProps {
  /** 'pill' = small solid black pill (default), 'button' = full-width 44px */
  variant?: 'pill' | 'button';
  onClick?: () => void;
}

/**
 * Apple Pay button.
 * Logo-only (no "Apple" text). "Pay" uses -apple-system (San Francisco) per Apple HIG.
 */
export function ApplePayButton({ variant = 'pill', onClick }: ApplePayProps) {
  const isPill = variant === 'pill';
  const shell = isPill ? glassPillStyle : glassBtnStyle;

  return (
    <Button
      type="button"
      style={shell}
      onClick={onClick}
      aria-label="Apple Pay"
    >
      <AppleLogo
        size={isPill ? 14 : 22}
        fill="#fff"
      />
      <span
        style={{
          fontFamily: '-apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text", "Helvetica Neue", Helvetica, Arial, sans-serif',
          fontWeight: 600,
          fontSize: isPill ? 11 : 15,
          color: '#fff',
          letterSpacing: '-0.01em',
          lineHeight: 1,
        }}
      >
        Pay
      </span>
    </Button>
  );
}

/* ─── Google Pay ────────────────────────────────────── */

interface GooglePayProps {
  /** 'pill' = small solid black pill (default), 'button' = full-width 44px */
  variant?: 'pill' | 'button';
  onClick?: () => void;
}

/**
 * Google Pay button.
 * Google G logo (4-color) + "Pay" in Google Sans. No "Google" text.
 * Google Sans loaded from fonts.gstatic.com (no extra font import needed in static pages
 * that already load brand fonts; React app imports via index.css or ComponentLibrary).
 */
export function GooglePayButton({ variant = 'pill', onClick }: GooglePayProps) {
  const isPill = variant === 'pill';
  const shell = isPill ? glassPillStyle : glassBtnStyle;

  return (
    <Button
      type="button"
      style={shell}
      onClick={onClick}
      aria-label="Google Pay"
    >
      <GoogleGLogo size={isPill ? 14 : 18} />
      <span
        style={{
          fontFamily: '"Google Sans", "Product Sans", "Roboto", sans-serif',
          fontWeight: 600,
          fontSize: isPill ? 11 : 15,
          color: '#fff',
          letterSpacing: '-0.01em',
          lineHeight: 1,
        }}
      >
        Pay
      </span>
    </Button>
  );
}
