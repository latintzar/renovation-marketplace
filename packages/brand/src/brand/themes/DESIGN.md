# Themes — seven-slot aesthetic bundles

> Full aesthetic voices. Seven slots each. One folder per theme.

## What a theme is

A theme is a **complete aesthetic bundle** for one surface voice — not
just a palette. Seven slots, documented below. Three of those slots
(translucency, motion, typography) are one-word picks from the
brand-wide catalogs next door, so a theme is mostly narrative + a
palette + some gradient choices.

See the top-level [`packages/brand/DESIGN.md`](../../../DESIGN.md) for
the wider context and the banned-from-themes list.

## The seven slots

| # | Slot | Where |
|---|---|---|
| 1 | Narrative | `<theme>/DESIGN.md` — prose describing the mood |
| 2 | Palette | entry in `tokens.py`'s `THEMES` dict — `colors` overrides |
| 3 | Gradient stops | `<theme>/gradients.py` — list of named palettes + overrides |
| 4 | Illustration voice | `<theme>/illustration_style.py` — pencil parameters |
| 5 | Translucency | `<theme>/__init__.py`: `TRANSLUCENCY = "<name>"` |
| 6 | Motion | `<theme>/__init__.py`: `MOTION = "<name>"` |
| 7 | Typography | `<theme>/__init__.py`: `TYPOGRAPHY = "<name>"` |

Named picks for 5/6/7 reference the catalogs in
`../translucency/`, `../motion/`, `../typography/` — a theme inherits
defaults by naming the same recipe.

## Themes today

- **`default`** — the quiet-trust Leo voice. Cream paper, ink text,
  terracotta accent, pencil illustrations, vellum glass, quiet motion.
  Every other theme starts here and diverges by exception.
- **`dark`** — same voice in a late-hours palette. Ink becomes cream,
  cream becomes ink. Gradients and illustrations stay tuned for low
  light. Translucency, motion, typography: unchanged.
- **`warm-drift`** — a warmer second voice (placeholder name). More
  amber, softer edges, slower default motion. Intended for
  reflection/story surfaces where the cream-paper feel should read as
  "evening golden hour" rather than "morning paper." Still the same
  pencil illustrations.

## Graduation path — adding a theme

1. **Copy `default/` to `themes/<new-name>/`.** Cheapest starting point.
2. **Write `<new-name>/DESIGN.md`.** One paragraph on mood + what
   distinguishes this theme from its sibling. If you can't articulate
   it, it's not a theme — it's a tweak.
3. **Add the palette.** One entry in `tokens.py`'s `THEMES` dict with
   only the colour keys that differ from default.
4. **Pick gradients.** Reuse `fluid-gradient.js` palette names where
   possible; add overrides only for clear reasons.
5. **Pick illustration voice.** Copy `illustration_style.py`, change
   line weight / accent / vocabulary to match the mood.
6. **Pick translucency / motion / typography.** One-word each in
   `__init__.py`.
7. **Rebuild.** `python -m brand.build` emits the `[data-theme]`
   overrides; the sessionStart hook auto-discovers the new folder.

## What themes never own

- **Component forks.** Themes never ship their own `Button`, `Input`,
  `Sheet`. Tokens handle the variation.
- **Layout decisions.** Grid, page-level spacing — app level.
- **Copy voice / product tone.** Project level.
- **Data.** Obvious, but worth stating.

If you find yourself wanting one of those per-theme, the token system
needs to expand — don't fork below it.

## Python usage

```python
import importlib

theme = importlib.import_module("brand.themes.default")
print(theme.TRANSLUCENCY)   # "vellum"
print(theme.MOTION)         # "quiet"
print(theme.TYPOGRAPHY)     # "default"
print(theme.GRADIENTS)      # ("brendan", "terraCharcoal")
```

Runtime theming is still CSS-only: `<html data-theme="dark">`. This
Python surface is for build-time tools (the brand-book page, the
warm-drift playground, docs generators) that need to read the active
bundle programmatically.
