# Motion — movement recipes, named

> Motion is quiet, not showy. Every movement must be earned.

## What motion is in Leo

Leo's product is about trust. Movement that draws attention to itself
breaks trust. So the defaults are short, ease-out, and subtle — things
move because they had to, not to impress.

A **motion style** is a complete recipe: durations, ease curves,
springs, entrance patterns, stagger delays, and scroll physics. Themes
pick a style **by name** (e.g. `MOTION = "quiet"`). The recipe stays
encapsulated so tuning the feel later doesn't require touching themes.

## The catalog today

### `quiet` — the default

- **Durations**: instant 80ms, fast 120ms, medium 240ms, slow 400ms,
  languid 640ms. Most transitions should land in `fast` or `medium`.
- **Eases**: out-quart for almost everything (things come to rest),
  in-out-cubic for cross-fades, a gentle spring for hover lifts.
- **Springs** (framer-motion): four presets — `subtle`, `default`,
  `bouncy`, `snappy`. Default to `default`; use `bouncy` for drag
  releases only.
- **Entrances**: fade, slide-up (8px), slide-right (8px), blur-in
  (2→0px), scale-in (0.98→1). All combine with a fade.
- **Staggers**: tight 40ms, default 80ms, generous 160ms. Lists of
  cards = default; prose reveals = generous.
- **Scroll**: parallax factors (slow/default/fast) for layered depth;
  reveal threshold 15% for scroll-triggered entrances.

All values emitted as CSS variables (`--motion-fast`, `--ease-out-quart`,
etc.) by `brand.build`; also exposed as framer-motion-compatible dicts
via `to_ts()`.

## Accessibility

`prefers-reduced-motion: reduce` overrides **all** motion recipes to a
near-zero duration with instant fade. A theme cannot override that — it
lives at the brand root, not the theme level.

## Adding a motion style

Drop `packages/brand/src/brand/motion/<name>.py` with a
`MotionStyle` named constant, register it in
[`__init__.py`](__init__.py)'s `STYLES` dict, reference from a theme
via `MOTION = "<name>"`. Rebuild is automatic.

Good candidates for future recipes:
- `languid` — twice the duration, softer curves, for contemplative apps.
- `snappy` — half the duration, tighter springs, for power-user tools.

Don't fork over one knob. Recipes capture a *feel*, not a parameter
tweak.

## Python usage

```python
from brand.motion import get as get_motion

quiet = get_motion("quiet")
print(quiet.durations.fast)     # 120 (ms)
print(quiet.eases.out_quart)    # "cubic-bezier(0.165, 0.84, 0.44, 1)"
print(quiet.to_css())           # :root { --motion-fast: 120ms; ... }
```
