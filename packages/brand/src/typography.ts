/**
 * Typography — named font recipes.
 *
 * Mirrors `packages/brand/src/brand/typography/default.py`. The `default`
 * recipe re-exports the generated `BRAND_FONTS` / `BRAND_FONTS_URL` from
 * `tokens.ts`, so Python and TS stay perfectly aligned.
 */

import { BRAND_FONTS, BRAND_FONTS_URL } from './brand/generated/tokens';

export interface TypographyStyle {
  name: string;
  fonts: typeof BRAND_FONTS;
  fontsUrl: string;
}

export const DEFAULT_TYPOGRAPHY: TypographyStyle = {
  name: 'default',
  fonts: BRAND_FONTS,
  fontsUrl: BRAND_FONTS_URL,
};

export const TYPOGRAPHY_STYLES = {
  default: DEFAULT_TYPOGRAPHY,
} as const;

export type TypographyName = keyof typeof TYPOGRAPHY_STYLES;
