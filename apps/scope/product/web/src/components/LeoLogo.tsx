/**
 * LeoLogo — SVG wordmark + monogram from fonttools-converted Playfair Display SemiBold paths.
 * No font dependency at render time. No FOUT. Perfectly scalable.
 *
 * Sources (scope-app/public/brand/):
 *   leo-charcoal.svg    — "Leo" wordmark, #1C1917, use on cream/light backgrounds
 *   leo-cream.svg       — "Leo" wordmark, #FAF8F4, use on charcoal/dark backgrounds
 *   leo-L-charcoal.svg  — "L" monogram,  #1C1917, use on cream/light backgrounds
 *   leo-L-cream.svg     — "L" monogram,  #FAF8F4, use on charcoal/dark backgrounds
 *
 * Regenerate: python3 scope-app/public/brand/generate-logo.py
 */

interface LeoLogoProps {
  /** 'charcoal' on light bg (default), 'cream' on dark bg */
  variant?: 'charcoal' | 'cream';
  /** 'wordmark' (default) = "Leo" | 'monogram' = "L" only */
  mark?: 'wordmark' | 'monogram';
  /** Height in px — width scales proportionally */
  height?: number;
  className?: string;
}

export function LeoLogo({ variant = 'charcoal', mark = 'wordmark', height = 20, className }: LeoLogoProps) {
  // BASE_URL-relative so the logo resolves at /app/ (leo.casa), /scope/app/
  // (vendored under Atelier) and the Vite dev server alike. Assets live in the
  // SPA publicDir (web/public/brand) so they bundle with the app.
  const base = import.meta.env.BASE_URL;
  const file = mark === 'monogram'
    ? `${base}brand/leo-L-${variant}.svg`
    : `${base}brand/leo-${variant}.svg`;

  // wordmark viewBox ratio ≈ 2.084 | monogram (L) ≈ 0.791
  const ratio = mark === 'monogram' ? 0.791 : 2.084;
  const width = Math.round(height * ratio);

  return (
    <img
      src={file}
      alt="Leo"
      width={width}
      height={height}
      className={className}
      draggable={false}
    />
  );
}
