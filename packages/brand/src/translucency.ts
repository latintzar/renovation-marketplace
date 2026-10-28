/**
 * Translucency — glass recipes, named.
 *
 * Mirrors `packages/brand/src/brand/translucency/` for TypeScript consumers.
 * Today: one canonical style, `vellum`. See
 * `packages/brand/src/brand/translucency/DESIGN.md` for the catalog rules.
 *
 * Python is the source of truth — keep the numbers in sync with
 * `translucency/vellum.py`. `brand.build` does not currently codegen this
 * file because the catalog is tiny; promote to codegen if it grows.
 */

export interface TranslucencyStyle {
  name: string;
  backdropBlur: string;
  backdropSaturate: number;
  background: string;
  border: string;
  insetHighlight: string;
  dropShadow: string;
}

export const VELLUM: TranslucencyStyle = {
  name: 'vellum',
  backdropBlur: 'blur(7px)',
  backdropSaturate: 1.0,
  background: 'rgba(250, 248, 244, 0.12)',
  border: '1px solid rgba(255, 255, 255, 0.35)',
  insetHighlight: 'inset 0 1px 0 rgba(255, 255, 255, 0.45)',
  dropShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
};

export const TRANSLUCENCY_STYLES = {
  vellum: VELLUM,
} as const;

export type TranslucencyName = keyof typeof TRANSLUCENCY_STYLES;

export function translucencyCss(style: TranslucencyStyle, selector: string): string {
  const blur =
    style.backdropSaturate === 1
      ? style.backdropBlur
      : `${style.backdropBlur} saturate(${style.backdropSaturate})`;
  return [
    `${selector} {`,
    `  -webkit-backdrop-filter: ${blur};`,
    `  backdrop-filter: ${blur};`,
    `  background: ${style.background};`,
    `  border: ${style.border};`,
    `  box-shadow: ${style.dropShadow}, ${style.insetHighlight};`,
    `}`,
  ].join('\n');
}
