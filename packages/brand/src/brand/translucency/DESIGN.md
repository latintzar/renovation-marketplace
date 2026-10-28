# Translucency — glass recipes

> One catalog. One canonical style (`vellum`). Themes pick by name.

## What translucency is in Leo

Translucency is how Leo layers surfaces without breaking the cream-paper
illusion. It's the quiet-but-real visual language of "something is
floating over something else" — not a novelty, not a showcase.

A **translucency style** bundles six knobs:

| knob | purpose |
|---|---|
| `backdrop_blur` | how much of the content below shows through |
| `backdrop_saturate` | optional saturation boost (multiplier) |
| `background` | the thin tint that sits on top of the blur |
| `border` | edge definition |
| `inset_highlight` | the top-edge gleam that sells "pane of glass" |
| `drop_shadow` | depth below the surface |

A theme **picks one style by name**; it never tunes the individual knobs
inline. If a theme needs something different, add a new recipe to this
folder and reference it by name — the knobs stay encapsulated.

## The catalog today

### `vellum` — canonical

Vellum is *the* Leo glass. It's a light cream film (rgba(250,248,244,.12))
with a subtle 7px blur, a soft top-edge highlight, and a small drop
shadow. Designed to read as "paper-over-paper" rather than "glass over
colour."

```
backdrop_blur:       blur(7px)
backdrop_saturate:   1.0
background:          rgba(250, 248, 244, 0.12)
border:              1px solid rgba(255, 255, 255, 0.35)
inset_highlight:     inset 0 1px 0 rgba(255, 255, 255, 0.45)
drop_shadow:         0 2px 8px rgba(0, 0, 0, 0.05)
```

Emitted as the `.brand-glass--vellum` CSS class in `effects.css`. The
Python recipe in [`vellum.py`](vellum.py) is the source of truth; the
CSS class is a mirror.

### (No other styles yet)

Previously `effects.css` also shipped `.brand-glass--ghosted` (blur 12px)
and `.brand-glass--blur` (blur 28px). Those were deleted in this refactor
— they were parameter variations of vellum, not distinct styles. If a
future theme genuinely needs a heavier/lighter recipe, add it here with
a name that describes the feel (not just the blur strength).

## Adding a new style

1. Drop a new file: `packages/brand/src/brand/translucency/<name>.py`.
   Declare a `TranslucencyStyle` named constant (e.g. `MIST`).
2. Register it in [`__init__.py`](__init__.py)'s `STYLES` dict.
3. Emit the matching CSS class (`.brand-glass--<name>`) in `effects.css`.
4. Rerun `python -m brand.build`.
5. Reference it from any theme's `__init__.py` as `TRANSLUCENCY = "<name>"`.

No changes to `tokens.py` are needed.

## Python usage

```python
from brand.translucency import get as get_translucency

vellum = get_translucency("vellum")
print(vellum.to_css(".brand-glass--vellum"))
# .brand-glass--vellum { backdrop-filter: blur(7px); ... }
```

## Why Vellum is the only one

Three sibling glass variants sprawl faster than anyone wants to
maintain. One canonical style, used for every Leo surface that floats,
keeps the design system coherent and the agent's decisions trivial.
Scale up only on evidence.
