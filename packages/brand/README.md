# `@scope/brand` — Leo brand system

Single source of truth for Leo's visual identity — design tokens (colours,
radii, shadows, typography), theme overrides, canonical CSS effects, the
WebGL fluid-gradient runtime, and the canonical brand SVG logos. Dual-
language: a Python package (`brand`) is canonical; the TS package
(`@scope/brand`) and every CSS/JS/SVG mirror are auto-generated or copied
from it by `python -m brand.build`.

Plan reference: `.cursor/plans/phase_5_capability_extraction_a7f8b3c4.plan.md` §Wave 9  
Design intent: `internal/refactor/packages/brand/design.md`  
Capability manifest: `internal/refactor/packages/brand/capability-manifest.md`

## What this package owns

Everything brand-level that a sibling app might want to reuse unchanged:

- **Design tokens** — colours, radii, shadows, fonts (`tokens.py`).
- **Theme overrides** — `THEMES` dict in `tokens.py`; build emits
  `[data-theme="<name>"] { ... }` blocks in `vars.css` and `tokens.css`.
- **Effects CSS** — `effects.css` owns vellum / glass / grain / shimmer /
  `.leo-chat-*` / landing-hero classes.
- **Fluid-gradient runtime** — `fluid-gradient.js` is the WebGL runtime
  used by landing heroes, story cards, and the design-system page.
- **Logo SVGs** — `assets/leo-charcoal.svg`, `leo-cream.svg`,
  `leo-L-charcoal.svg`, `leo-L-cream.svg`.

A new app that imports `@scope/brand` + `@scope/ui` gets the full visual
vocabulary with zero copy-paste from `apps/scope/product/public/`.

## The dataflow

```
src/brand/tokens.py           ← HAND-EDITED, canonical (code + themes)
src/brand/effects.css         ← HAND-EDITED, canonical (vellum / glass / shimmer)
src/brand/fluid-gradient.js   ← HAND-EDITED, canonical (WebGL runtime)
src/brand/assets/*.svg        ← HAND-EDITED, canonical (logo paths)
        │
        ▼  python -m brand.build
┌───────┼───────────┬───────────┬────────────────┐
▼       ▼           ▼           ▼                ▼
tokens.json   tokens.ts    tokens.css     vars.css           apps/<app>/public/*
 (raw)        (TS export)  (@theme + dt) (:root + dt)        (byte-identical mirrors)
```

| file | hand-edited? | read by |
|---|---|---|
| `src/brand/tokens.py` | ✅ yes | `brand.build`, Python callers (`from brand import COLORS, THEMES`) |
| `src/brand/effects.css` | ✅ yes | Vite apps (`@import '@scope/brand/effects.css'`) + mirrored to `apps/*/public/brand-effects.css` |
| `src/brand/fluid-gradient.js` | ✅ yes | `<FluidGradient>` in `@scope/ui` + mirrored to `apps/*/public/fluid-gradient-v4.js` |
| `src/brand/assets/leo-*.svg` | ✅ yes | React `<img>` + mirrored to `apps/*/public/brand/leo-*.svg` |
| `src/brand/generated/tokens.json` | ❌ no | TS consumers that want the raw map |
| `src/brand/generated/tokens.ts` | ❌ no | `@scope/brand` TS surface |
| `src/brand/generated/tokens.css` | ❌ no | Tailwind `@theme` + `[data-theme]` (via `@scope/ui`) |
| `src/brand/generated/vars.css` | ❌ no | Landing pages (`:root` + `[data-theme]`) |
| `apps/<app>/public/*` | ❌ no (auto-synced) | Landing pages + nginx — byte-identical copies |

Every hand-edit of a canonical file must be followed by `python -m brand.build`;
CI rejects pull requests where the committed artefacts drift from the canonical
source (`scripts/checks/brand_drift.sh`).

## Python usage

```python
from brand import COLORS, RADIUS, SHADOWS, FONTS, THEMES
from brand import FAVICON_SVG, FONTS_URL, LOGO_URLS, BRAND

COLORS["ink"]             # '#1C1917'
RADIUS["md"]              # '8px'
SHADOWS["card"]           # '0 4px 16px rgba(0,0,0,.08)'
THEMES["dark"]["colors"]["ink"]   # '#FAF8F4'
```

Submodule access:

```python
from brand.tokens import SCRIM_TOKENS, LEGACY_CSS_ALIASES, UTILITY_CLASSES_CSS
from brand.build import main as rebuild_artefacts
```

## TypeScript usage

```ts
import {
  BRAND, BRAND_COLORS, BRAND_RADIUS, BRAND_SHADOWS,
  BRAND_FONTS, BRAND_THEMES, BRAND_LOGO,
  BRAND_FAVICON_SVG, BRAND_FONTS_URL,
} from '@scope/brand';

BRAND_COLORS.ink           // '#1C1917'
BRAND_THEMES.dark.colors.ink  // '#FAF8F4'
```

The `@scope/ui` package re-exports the same constants via
`packages/ui/src/brand.ts` (a migration shim) so historical callers
writing `import { BRAND_COLORS } from '@scope/ui'` keep working until the
final shim-removal batch.

CSS imports:

```ts
// @scope/ui's entrypoint already does this; listed here for completeness:
import '@scope/brand/tokens.css';       // Tailwind @theme block + [data-theme] overrides
import '@scope/brand/vars.css';         // :root { --ink: ... } + [data-theme] overrides
import '@scope/brand/effects.css';      // .brand-glass, .leo-chat-leo, vellum, shimmer
```

## Multi-theming (`data-theme`)

Themes are overrides declared in `tokens.py`'s `THEMES` dict:

```python
THEMES = {
    "dark": {
        "colors": {"ink": "#FAF8F4", "card": "#252220", ...},
    },
}
```

`brand.build` emits a `[data-theme="dark"] { ... }` block in both
`vars.css` and `tokens.css`. Flip themes at runtime with:

```html
<html data-theme="dark">
```

Zero JavaScript, zero rebuild. The scoping selector is flexible — apply
it to a subtree (`<div data-theme="dark">`) to theme a single pane while
the rest of the page stays default.

Adding a new theme: append an entry to `THEMES`, run `python -m brand.build`,
commit. No other changes.

## Rebuilding after a canonical edit

```bash
cd packages/brand/src
python3 -m brand.build          # regenerates generated/ + syncs public/ copies
python3 -m brand.build --check  # CI mode — exits 1 on drift, 0 if clean
python3 -m brand.build --no-sync  # regenerate generated/ only (rare)
```

The drift check covers both the `generated/` artefacts AND the synced
public copies in `apps/<app>/public/`. `scripts/checks/brand_drift.sh`
wires it into the Phase-4 CI pipeline (gate 9).

## Public mirrors (build-step copies)

`brand.build` maintains byte-identical mirrors in each registered app's
`public/` directory so landing pages keep resolving `/brand-effects.css`,
`/fluid-gradient-v4.js`, `/brand/leo-*.svg`, and `/brand-vars.css` without
an HTML codemod:

| canonical | public mirror |
|---|---|
| `src/brand/effects.css` | `apps/scope/product/public/brand-effects.css` |
| `src/brand/fluid-gradient.js` | `apps/scope/product/public/fluid-gradient-v4.js` |
| `src/brand/assets/leo-*.svg` | `apps/scope/product/public/brand/leo-*.svg` |
| `src/brand/generated/vars.css` | `apps/scope/product/public/brand-vars.css` |

Adding another app (`leo-stock`, `apps/experiments/<x>/`, ...) is a one-line
entry in `PUBLIC_SYNC_TARGETS` inside `build.py`. `scripts/bootstrap_app.py`
writes the entry automatically.

## Layout

```
packages/brand/
├── pyproject.toml                   # Python package: name = "brand"
├── package.json                     # TS package: name = "@scope/brand"
├── tsconfig.json                    # extends @scope/tsconfig/react.json
├── index.ts                         # TS re-exports (public surface)
├── README.md                        # this file
├── src/
│   └── brand/
│       ├── __init__.py              # curated Python re-exports
│       ├── tokens.py                # HAND-EDITED canonical source (+ THEMES)
│       ├── build.py                 # codegen + public/ sync + drift gate
│       ├── effects.css              # HAND-EDITED canonical CSS effects
│       ├── fluid-gradient.js        # HAND-EDITED canonical WebGL runtime
│       ├── assets/
│       │   ├── leo-charcoal.svg     # HAND-EDITED canonical logo
│       │   ├── leo-cream.svg
│       │   ├── leo-L-charcoal.svg
│       │   └── leo-L-cream.svg
│       └── generated/               # AUTO-GENERATED — do not hand-edit
│           ├── __init__.py
│           ├── tokens.json
│           ├── tokens.ts
│           ├── tokens.css           # @theme + [data-theme] blocks
│           └── vars.css             # :root + [data-theme] blocks
└── tests/
    ├── test_tokens.py
    └── test_build.py
```

Not yet shipped (queued for follow-up waves — see plan):

* `src/brand/palette.py` — darken/lighten/mix/contrast helpers.
* `src/brand/typography.py` — font-family builders.
* `src/brand/generators/` — Node + WebGL gradient asset generator
  (moved in Wave 9 from `scripts/ops/web/gradient-gen/`).
* `src/logo/{LeoLogo,LeoInitial}.tsx` — React components for the logo.

The `<FluidGradient>` React wrapper itself lives in `@scope/ui` (compound
component) because it mounts in React, but the underlying WebGL runtime
(`fluid-gradient.js`) lives here because it's framework-agnostic.
