# Leo brand — the design narrative

> Read me before you touch pixels. The tokens in `src/brand/tokens.py` are
> the hard contract; this document is the voice behind them.

## What the Leo brand is

Leo is a quiet product. It sits beside a contractor in their van or a
homeowner on their sofa; it never shouts over the work being done. Every
visual decision ladders up to that: **trust earned through restraint**.

Translated to surface:

- **Cream paper, not white screen.** `--cream` (`#FAF8F4`) is the default
  canvas. It's softer than `#fff` and signals a handmade artefact.
- **Ink that feels drawn, not printed.** `--ink` (`#1C1917`) carries
  warmth — never pure black.
- **Terracotta accent, not brand red.** `--terracotta` (`#DA654D`) is the
  single hot colour. Used sparingly. If you find yourself reaching for
  another saturated hue, don't — layer depth or motion instead.
- **Vellum translucency.** Glass is always vellum — a light cream film
  with a 7px blur. Other blur strengths have been retired. See
  [`translucency/DESIGN.md`](src/brand/translucency/DESIGN.md).
- **Black pencil illustrations.** Every generated illustration is black
  line-art on transparent. No colour fills. See
  [`illustrations/DESIGN.md`](src/brand/illustrations/DESIGN.md).

## What a theme is

A **theme** is a full aesthetic bundle — not just a palette. Every theme
in [`src/brand/themes/<name>/`](src/brand/themes/) ships seven slots:

| Slot | Required | Form | Default value |
|---|---|---|---|
| Narrative | yes | `DESIGN.md` | hand-written per theme |
| Palette | yes | entry in `tokens.py`'s `THEMES` dict | — |
| Gradient stops | yes | `gradients.py` | — |
| Illustration voice | yes | `illustration_style.py` (pencil parameters) | — |
| Translucency | yes | `__init__.py`: `TRANSLUCENCY = "<name>"` | `"vellum"` |
| Motion | yes | `__init__.py`: `MOTION = "<name>"` | `"quiet"` |
| Typography | yes | `__init__.py`: `TYPOGRAPHY = "<name>"` | `"default"` |
| Curated assets | optional | `assets/` folder | empty |

Three of those (translucency, motion, typography) are **named picks from
a brand-wide catalog** — one line each. A theme inherits the defaults by
declaring the same name. An app swaps themes at runtime with `<html
data-theme="<name>">`; zero rebuild, zero JS.

Themes shipped today: `default` (the quiet-trust look), `dark` (same
voice, late-hours palette), `warm-drift` (a warmer second voice —
placeholder name, rename once it's proven).

## What a theme is **not**

These are banned from themes. If you feel a theme needs one, the fix is
to widen the token system, not fork below it.

- **Component forks.** Themes never ship their own `Button`, `Input`,
  `Sheet`. Primitives in `@scope/ui` are single-source; themes change
  how they *feel* through tokens alone.
- **Layouts.** Grid, spacing-at-the-page-scale, routing-shape — those
  are app concerns.
- **Copy voice / tone.** Product writing lives at the project level.
- **Data.** Obvious, but worth stating.

## The named-style catalogs

Three brand-wide catalogs live next to `tokens.py`:

- [`src/brand/translucency/`](src/brand/translucency/) — glass recipes.
  Today: **`vellum`** is the canonical one (and currently the only one).
  Vellum is blur(7px) + cream tint + subtle inset highlight. A theme
  picks a name; it doesn't tune the knobs.
- [`src/brand/motion/`](src/brand/motion/) — motion feel. Today:
  **`quiet`** (the default) — short durations, gentle ease curves,
  subtle springs. A theme can pick a more languid or snappier recipe by
  name once those exist.
- [`src/brand/typography/`](src/brand/typography/) — font choices.
  Today: **`default`** re-exports the fonts declared in `tokens.py`.
  Adding a new typography recipe (serif-display, monochrome, etc.)
  doesn't require touching `tokens.py`.

## Illustrations are part of the brand

Illustrations — not stock photos — are the default imagery. Every
illustration is **bold hand-drawn marker line-art** — solid black
outlines, one flat spot-colour fill, on a transparent background
(Top Cuvée / modern food-and-drink register). Two output lanes, both
raster-derived:

1. **Raster** (default) — `llm.generate_image` (via the LiteLLM proxy)
   produces a PNG on white paper; a Pillow post-processor converts
   white to transparent, preserving both ink strokes and the accent
   fill.
2. **Vector** — the raster output is flattened and traced by
   `vtracer` into a scalable SVG. Binary trace loses the accent
   colour; use raster when colour matters.

Callers pass the scene and the active theme; the generator picks up
style parameters (line weight, accent color, vocabulary) from the
theme's `illustration_style.py`. Full reference:
[`illustrations/DESIGN.md`](src/brand/illustrations/DESIGN.md).

## The mark is alive — it blinks

A Leo product's mark is **never a dead logo**. It is a live avatar that **blinks** — the
brand's liveness signal — present wherever the product introduces itself (nav, onboarding,
favicon). This is a RULE, not a flourish. Render it through the canonical **`BrandFace`
primitive** (`@scope/ui`), which blinks by construction on the shared `motion` clock. Do
**not** ship a static image of the mark, and do **not** hand-wire a blink per page — if you
find yourself writing blink code outside the primitive, stop and promote it into the
primitive instead. Each product supplies its own open/closed frames; the blink is shared.
(First instance: Rocoto's line-art chili face.)

## The onboarding / auth shell

Every product's sign-in + onboarding uses ONE shell — a full-viewport airy page, never a
cramped bordered card:

- The product mark (`BrandFace`, blinking) + wordmark at the **absolute top-left**.
- **Sign-out top-right**, shown only when there is a live session.
- A **larger blinking mark centered**, then the action heading, a subtitle, then the content
  (form / steps), vertically + horizontally centered.
- A **legal footer** pinned at the bottom: `Términos · Privacidad · © <year> <Product>`.

This is a shared layout, themed per product **through tokens alone** — never redrawn raw.
Historical reference: the Rocoto onboarding gate lived in
`5b8567b02a46ca86e0c1e49a35feb5490b58ae6d:apps/rocoto/product/landing-react`.
Rocoto now owns its kit in [Rocoto-Labs/rocoto](https://github.com/Rocoto-Labs/rocoto/tree/main/app).

## How agents should use this document

1. **Every session starts here.** The `load-shared-registry.sh`
   sessionStart hook emits a **BRAND DESIGN INDEX** that points at this
   file, each theme's `DESIGN.md`, and the three catalog `DESIGN.md`s.
2. **Before touching any pixel** — colour, class name, component,
   illustration — check which theme is active and read that theme's
   `DESIGN.md`. If your change would violate the seven-slot schema (or
   the banned list above), stop and ask.
3. **When adding a theme** — one folder in `themes/<name>/` with the
   required four files + one entry in `tokens.py`'s `THEMES`. The hook
   auto-discovers it.
4. **When adding a named style** — drop a new recipe into
   `translucency/`, `motion/`, or `typography/`. No other changes
   needed.

## The rules, compressed

- Every theme ships seven slots, three of which are one-word picks.
- Vellum is the canonical translucency. Don't invent new glass until
  there's a real reason.
- Every illustration is bold hand-drawn marker, one flat spot-colour fill, transparent.
- Components never fork per theme — expand the token system instead.
- The product mark is a **live blinking avatar** (`BrandFace`), never a static logo or a
  per-page blink. Writing blink code outside the primitive is a smell — promote it.
- Sign-in / onboarding uses the ONE shared full-page **auth shell**, themed by tokens only.
- This file is prose on purpose. The hard constraints live in
  `tokens.py`, the lint gates, and the tests. Narrative explains why
  those constraints exist.

## Pointers

- Tokens (hard contract): [`src/brand/tokens.py`](src/brand/tokens.py)
- Theme catalog: [`src/brand/themes/DESIGN.md`](src/brand/themes/DESIGN.md)
- Translucency catalog: [`src/brand/translucency/DESIGN.md`](src/brand/translucency/DESIGN.md)
- Motion catalog: [`src/brand/motion/DESIGN.md`](src/brand/motion/DESIGN.md)
- Typography catalog: [`src/brand/typography/DESIGN.md`](src/brand/typography/DESIGN.md)
- Illustrations: [`src/brand/illustrations/DESIGN.md`](src/brand/illustrations/DESIGN.md)
- Package README (dataflow + build): [`README.md`](README.md)
