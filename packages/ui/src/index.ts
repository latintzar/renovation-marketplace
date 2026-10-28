// ── Brand constants ───────────────────────────────────────────────────────
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
} from './brand';

// ── Primitives (mandatory building blocks — never bypass with raw HTML) ───
export { Button, type ButtonProps, type ButtonVariant, type ButtonSize } from './primitives';
export { Input, Textarea, type InputProps, type TextareaProps } from './primitives';
export { Sheet, type SheetProps } from './primitives';
export { Badge, type BadgeProps, type BadgeColor } from './primitives';
export { Surface, type SurfaceProps, type SurfaceVariant, type SurfaceRounded, type SurfacePadding } from './primitives';

// ── Production components (used in app routes) ─────────────────────────────
export { ComposerActionStrip, type ComposerActionStripProps } from './ComposerActionStrip';
export { GlassCard } from './GlassCard';
export { GradientScreen, GRADIENT_THEMES } from './GradientScreen';
export { FluidGradient, type FluidGradientProps } from './FluidGradient';
export { FullScreenStep, type FullScreenStepProps } from './FullScreenStep';
export { ShopMap, type ShopMapPoint, type ShopMapProps } from './ShopMap';
export { ThemeProvider, useTheme, type ThemeName, type ThemeProviderProps } from './ThemeProvider';
export { VoiceNoteBubble } from './VoiceNoteBubble';
export { LeoBubble, UserBubble } from './ChatBubbles';
export { default as BriefCanvas } from './BriefCanvas';
export { default as ProfileCanvas } from './ProfileCanvas';
export { default as QuoteCanvas } from './QuoteCanvas';
export { ChangeOrderCanvas } from './ChangeOrderCanvas';
export { StatusBadge, type ScopeStatus } from './StatusBadge';
export type {
  BriefUpdate,
  ProfileUpdate,
  ProfileSource,
  ProfileProject,
  ProfileReview,
  SocialMention,
  QuoteUpdate,
  QuoteLineItem,
  QuoteContingencyDraft,
  ChangeOrderUpdate,
  ChangeOrderLineItem,
} from './types';

// ── Showcase-only components (used only in ComponentLibrary.tsx dev gallery) ──
// These are NOT used in production routes. Kept for multi-app parity purposes.
export { GlassFrame } from './GlassFrame';
export { GlassPill } from './GlassPill';
export { MapAreaCard } from './MapAreaCard';
export { MilestoneList } from './MilestoneList';
export { ApplePayButton, GooglePayButton } from './PayButtons';
export { PlatformLogo, type PlatformLogoProps } from './PlatformLogo';
export { MaterialsCard } from './MaterialsCard';
export { AppleWalletButton } from './AppleWalletButton';
export { GoogleWalletButton } from './GoogleWalletButton';
