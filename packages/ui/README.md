# Design System — `@scope/ui`

Leo's shared component package. Consumed by `apps/web` and (eventually) `apps/mobile`.

**Import with:** `import { GlassFrame, GlassPill, BriefCanvas, ProfileCanvas, QuoteCanvas } from '@scope/ui'`

---

## Design System Hierarchy

```
tokens (theme.css)
  └── primitives (Button, Input, Textarea, Sheet, Badge, Surface)
        └── brand effects (brand-effects.css — loaded globally, not in this package)
              └── compounds (GlassFrame, GlassPill, GlassCard, LeoLogo)
                    └── Leo Documents (BriefCanvas, ProfileCanvas, QuoteCanvas)
                          └── page shells (ChatShell, PreviewPanel — in apps/web, not here)
                                └── pages (OnboardHomeowner, OnboardPro — in apps/web)
```

Each layer only knows about the layer below it. Pages compose shells. Shells wrap documents. Documents use compounds. Compounds use primitives. Primitives consume tokens.

---

## Primitives

The building blocks every page and component composes from. Never bypass these with raw HTML elements.

| Primitive | Import | Variants / Props |
|-----------|--------|-----------------|
| `Button` | `import { Button } from '@scope/ui'` | primary, secondary, terracotta, ghost, danger. Sizes: sm, md, lg, icon. `fullWidth`, `loading`, `icon`. |
| `Input` | `import { Input } from '@scope/ui'` | Standard input with `label`, `error`, `icon`. |
| `Textarea` | `import { Textarea } from '@scope/ui'` | Standard textarea with `label`, `error`. |
| `Sheet` | `import { Sheet } from '@scope/ui'` | Bottom sheet: `open`, `onClose`, `title`, `footer`. Replaces raw Vaul Drawer. |
| `Badge` | `import { Badge } from '@scope/ui'` | pill, status (with dot), outline. Colors: terracotta, teal, ink, amber, green, red, muted. |
| `Surface` | `import { Surface } from '@scope/ui'` | flat, lifted, raised. General card/container. `rounded`, `padding`. |

Source: `packages/ui/src/primitives/`. Enforcement: `afterFileEdit` hook warns on raw elements, `preCommit` blocks new ones.

---

## What's in this package

| Export | File | What it is |
|--------|------|-----------|
| `GlassFrame` | `src/GlassFrame.tsx` | Browser chrome mockup (dots + URL bar + body). Light or dark variant. |
| `GlassPill` | `src/GlassPill.tsx` | Glassmorphic status pill with breathing terra dot. "Updating…" / "Thinking…" state. |
| `VoiceNoteBubble` | `src/VoiceNoteBubble.tsx` | Voice note playback bubble with waveform and transcript |
| `VoiceInputBar` | `src/VoiceInputBar.tsx` | Standalone voice input bar with waveform visualizer and recording state |
| `ComposerActionStrip` | `src/ComposerActionStrip.tsx` | Action strip for composer (photo, document, voice attach buttons) |
| `MapAreaCard` | `src/MapAreaCard.tsx` | Map area display with terra ring and privacy footer |
| `MilestoneList` | `src/MilestoneList.tsx` | Escrow milestone phases with gradient background support |
| `ApplePayButton` | `src/PayButtons.tsx` | Apple Pay button (pill and full button variants) |
| `GooglePayButton` | `src/PayButtons.tsx` | Google Pay button (pill and full button variants) |
| `AppleWalletButton` | `src/AppleWalletButton.tsx` | Apple Wallet "Add to Wallet" button with official branding |
| `GoogleWalletButton` | `src/GoogleWalletButton.tsx` | Google Wallet "Add to Wallet" button with official branding |
| `MaterialsCard` | `src/MaterialsCard.tsx` | Materials payment card with Apple Pay/Google Pay integration |
| `LeoBubble` | `src/ChatBubbles.tsx` | Leo's chat response bubble (markdown rendering) |
| `UserBubble` | `src/ChatBubbles.tsx` | User's chat message bubble (terra styling) |
| `PlatformLogo` | `src/PlatformLogo.tsx` | Platform logos (Habitissimo, Houzz, CronoShare, Hogami) with inline and card variants |
| `BriefCanvas` | `src/BriefCanvas.tsx` | Leo Document: job brief (homeowner's job description) |
| `ProfileCanvas` | `src/ProfileCanvas.tsx` | Leo Document: tradesperson profile (identity + reviews + portfolio) |
| `QuoteCanvas` | `src/QuoteCanvas.tsx` | Leo Document: scope of work (line items, payment schedule, terms) |
| `ChangeOrderCanvas` | `src/ChangeOrderCanvas.tsx` | Leo Document: change order (variation with photos and fair market range) |
| `BRAND` | `src/brand.ts` | Brand constants: `BRAND_COLORS`, `BRAND_RADIUS`, `BRAND_LOGO`, `BRAND_FAVICON_SVG`, `BRAND_FONTS_URL` |
| Canvas types | `src/types.ts` | `BriefUpdate`, `ProfileUpdate`, `QuoteUpdate`, `ChangeOrderUpdate`, `ChangeOrderLineItem`, etc. — re-exported by `apps/web/src/lib/api.ts` |

---

## Theme Tokens

Defined once in `src/theme.css` (Tailwind `@theme`) and `src/brand.ts` (TS constants). Never duplicated — open those files for current values. Visual reference: `scope-app/public/design/brand-book.html`.

Typography: **Playfair Display** (display/headings) · **Source Sans 3** (body)

---

## Brand Effects (not in this package — loaded globally)

Brand effects live in `scope-app/public/brand-effects.css`. They must be loaded as a `<link>` tag, not processed by Vite (LightningCSS strips unprefixed `backdrop-filter`).

| Effect | CSS class | Use case |
|--------|-----------|----------|
| Vellum overlay | `.brand-glass--vellum` | Canonical Leo glass — 7px blur, cream tint, inset highlight. Used for every translucent surface in Leo. Recipe at `packages/brand/src/brand/translucency/vellum.py`; narrative at `packages/brand/src/brand/translucency/DESIGN.md`. |
| Glass pill | `.leo-glass-pill` + `.leo-glass-pill-dot` | "Updating…" indicator (React wrapper: `GlassPill`) |
| Shimmer label | `.leo-shimmer-label` | "Thinking…" text with terra grain sweep |

Visual reference: `scope-app/public/design/brand-book.html` (static, CSS-only effects)

---

## GlassFrame

Browser chrome mockup. Renders identically in React (this package) and static HTML (`leo-glass-frame.css`).

```tsx
// Light (on cream/white backgrounds)
<GlassFrame url="leo.casa/brief/LCS-4821">
  <BriefCanvas b={brief} />
</GlassFrame>

// Dark (on dark/charcoal backgrounds)
<GlassFrame dark url="leo.casa/scope/hwc-2026">
  <QuoteCanvas scope={scope} />
</GlassFrame>
```

Dots are always **terra / amber / teal** — baked into `leo-glass-frame.css` via `nth-child`. Never override inline.

Static HTML pattern (for landing pages):
```html
<link rel="stylesheet" href="/leo-glass-frame.css">
<div class="glass-frame glass-frame--dark">
  <div class="glass-frame-bar">
    <div class="glass-frame-dots"><span></span><span></span><span></span></div>
    <div class="glass-frame-url">
      <span class="glass-frame-url-text">leo.casa/your-path</span>
    </div>
  </div>
  <div class="glass-frame-body"><!-- content --></div>
</div>
```

---

## GlassPill

```tsx
<GlassPill>Updating brief…</GlassPill>         // with breathing dot (default)
<GlassPill dot={false}>Brief ready</GlassPill>  // status only, no dot
```

---

## Leo Documents

The three canvas components are Leo's product output. They render identically in:
- Chat preview (`PreviewPanel` in `apps/web`)
- Inbox overlay (`JobInbox` in `apps/web`)
- Standalone URL (`/canvas/:token` in `apps/web`)
- Inside a `GlassFrame` (marketing / diagrams)

```tsx
import { BriefCanvas, ProfileCanvas, QuoteCanvas } from '@scope/ui';
import type { BriefUpdate, ProfileUpdate, QuoteUpdate } from '@scope/ui';

<BriefCanvas b={brief} photos={[]} />   // b: BriefUpdate | null
<ProfileCanvas p={profile} />           // p: ProfileUpdate | null
<QuoteCanvas scope={scope} />           // scope: QuoteUpdate | null
```

Pass `null` to render the empty/placeholder state.

---

## Visual Reference

The canonical reference for all components is the **Component Library** at `/app/dev/library` (`apps/web/src/pages/ComponentLibrary.tsx`). Open it before building anything UI-related.

The brand book (`scope-app/public/design/brand-book.html`) covers CSS-only effects (vellum, gradients) that don't need the dev server. When they differ, ComponentLibrary wins.

---

## File Structure

```
packages/ui/
  src/
    index.ts              Package entry — all exports
    brand.ts              Brand constants (BRAND_COLORS, BRAND_RADIUS, BRAND_LOGO, etc.)
    types.ts              Canvas data types (BriefUpdate, ProfileUpdate, QuoteUpdate, ChangeOrderUpdate, etc.)
    theme.css             CSS custom properties (@theme for Tailwind)
    primitives/           Mandatory building blocks — never bypass
      index.ts            Barrel export
      Button.tsx          5 variants × 4 sizes, loading, icon slots
      Input.tsx           Input + Textarea with label, error, icon
      Sheet.tsx           Bottom sheet (wraps Vaul Drawer)
      Badge.tsx           Status/pill/outline badges
      Surface.tsx         Card/container (flat, lifted, raised)
    locales/              Locale data (if any — reserved for i18n)
    GlassFrame.tsx        Browser chrome mockup
    GlassPill.tsx         Glassmorphic status pill
    VoiceNoteBubble.tsx   Voice note playback bubble
    VoiceInputBar.tsx     Standalone voice input bar with waveform and recording state
    ComposerActionStrip.tsx Action strip for composer (attach photo/doc/voice)
    MapAreaCard.tsx       Map area display with terra ring
    MilestoneList.tsx     Escrow milestone phases
    PayButtons.tsx        Apple Pay + Google Pay buttons
    AppleWalletButton.tsx Apple Wallet "Add to Wallet" button
    GoogleWalletButton.tsx Google Wallet "Add to Wallet" button
    MaterialsCard.tsx     Materials payment card
    ChatBubbles.tsx       User + Leo chat message bubbles
    PlatformLogo.tsx      Platform logos (Habitissimo, Houzz, CronoShare, Hogami)
    BriefCanvas.tsx       Brief document template
    ProfileCanvas.tsx     Profile document template
    QuoteCanvas.tsx       Scope document template
    ChangeOrderCanvas.tsx Change order document template
  package.json            @scope/ui
  tsconfig.json
```

---

## Adding a new shared component

1. Check ComponentLibrary first — it probably exists
2. Build in `packages/ui/src/` if it needs to work in mobile too; `apps/web/src/components/` if app-only
3. Export from `src/index.ts`
4. Add a section to `ComponentLibrary.tsx` with real data
5. If it has a static HTML counterpart, keep the CSS class pattern in `leo-glass-frame.css` or `brand-effects.css` in sync
