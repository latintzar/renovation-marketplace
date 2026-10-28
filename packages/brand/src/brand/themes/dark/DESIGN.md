# `dark` — late-hours Leo

> Same voice, ink inverted, evening light.

## Mood

The same product, read by lamplight. Ink becomes cream, cream becomes
near-black; the terracotta holds — it still marks the single hot note.
Not a "dark mode for the sake of dark mode" — it's tuned for contractors
reviewing tomorrow's work at 10pm and homeowners scanning a brief
before bed. The illustrations stay recognisably pencil, just on a dark
paper instead of cream.

## Why it exists as its own folder

The palette override has always lived in `tokens.py`'s `THEMES` dict
(kept there because the colour overrides are part of the hard
contract). Moving the *narrative* + *gradients* + *illustration voice*
into this folder lets themes own the non-colour dimensions without
scattering them.

## The seven slots

| Slot | Value |
|---|---|
| Narrative | this file |
| Palette | `tokens.py` → `THEMES["dark"]` (ink↔cream flip, soft border) |
| Gradient stops | [`gradients.py`](gradients.py) — terraCharcoal-leaning |
| Illustration voice | [`illustration_style.py`](illustration_style.py) — inverted |
| Translucency | `vellum` (unchanged — looks equally good on dark) |
| Motion | `quiet` (unchanged) |
| Typography | `default` (unchanged) |

## When to reach for another theme

- If you want a *different voice* (not just a dark repaint), use
  `warm-drift` or author a new theme. `dark` is strictly the inverted
  version of default.
