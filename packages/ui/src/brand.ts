/**
 * Migration shim — brand tokens moved to `@scope/brand` (Phase 4 Wave 2).
 *
 * This file is kept temporarily so existing `import { BRAND_COLORS } from '@scope/ui'`
 * callers keep working without edits. Each caller should migrate to the
 * canonical import:
 *
 *     import { BRAND_COLORS } from '@scope/brand';
 *
 * Deleted in the final shim-removal batch (plan §3.8, design.md D3).
 */
export {
  BRAND,
  BRAND_COLORS,
  BRAND_RADIUS,
  BRAND_SHADOWS,
  BRAND_FONTS,
  BRAND_THEMES,
  BRAND_LOGO,
  BRAND_FAVICON_SVG,
  BRAND_FONTS_URL,
} from '@scope/brand';
