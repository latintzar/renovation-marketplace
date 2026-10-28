# Typography — font recipes, named

> One style today (`default`). A theme rarely overrides it.

## What typography is in Leo

The Leo type system is intentionally small. Most product surfaces don't
need more than two families — a display/heading serif and a body sans.
This catalog exists not because themes *should* swap fonts often, but so
that when one does (a print-style theme, a monochrome-brutalist theme),
the swap is one line in the theme, not a surgery in `tokens.py`.

## The catalog today

### `default` — the Leo standard

- **Serif / display / heading**: Playfair Display — warm, slightly
  editorial, reads as "considered" not "showy."
- **Sans / body**: Source Sans 3 — utilitarian, high x-height, legible
  at small sizes.
- **URL**: the combined Google Fonts `<link>` shared across all apps.

Values come straight from [`tokens.py`](../tokens.py)'s `FONTS` dict —
this module is the bridge between the hard-contract `FONTS` and the
theme-level slot. When a theme says `TYPOGRAPHY = "default"`, it's
inheriting whatever `tokens.py` declares.

## Adding a typography style

1. Drop a new file: `packages/brand/src/brand/typography/<name>.py`.
   Declare a `TypographyStyle` named constant.
2. Register in [`__init__.py`](__init__.py)'s `STYLES` dict.
3. Add the matching Google-Fonts URL fragment.
4. Reference from a theme: `TYPOGRAPHY = "<name>"`.

Typical reasons to add one:
- **Print-style** — stronger serif presence (heavier heading weight, a
  didone for display).
- **Monochrome-brutalist** — a single mono family for everything.
- **Accessibility-first** — Atkinson Hyperlegible across all levels.

Don't fork for a one-glyph tweak. If you just want a different weight
or size, that's a token change, not a new typography style.

## Python usage

```python
from brand.typography import get

default = get("default")
print(default.display)   # "'Playfair Display', Georgia, serif"
print(default.url)       # Google Fonts link
```
