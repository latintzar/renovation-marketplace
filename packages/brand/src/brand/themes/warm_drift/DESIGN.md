# `warm-drift` — evening golden hour

> Cream turns amber. Still Leo, but warmer.

## Mood

Leo when the sun is low. The cream paper turns to a warm wheat, the
terracotta accent picks up more orange, the edges soften. Intended for
surfaces where the cream-paper feeling should read as *reflective* or
*storytelling* rather than *morning utility* — think story cards, blog
posts, onboarding narratives, end-of-project summaries.

The pencil illustrations stay pencil. The motion is the same quiet
recipe. Translucency is vellum. Only the palette and the gradient mood
change. That is the point — `warm-drift` tests whether the seven-slot
schema is tight enough that a second voice needs *only two slot
changes*.

## Name

**Placeholder.** If it proves itself, we'll rename it to something less
literal. "drift" reads evocative but thin; "wheat", "golden", "dusk",
"holmes" (Sherlock, paper, warmth — yellow amber) are all on the
shortlist.

## The seven slots

| Slot | Value |
|---|---|
| Narrative | this file |
| Palette | `tokens.py` → `THEMES["warm_drift"]` (amber-tinted cream, warmer accents) |
| Gradient stops | [`gradients.py`](gradients.py) — brendan + amber emphasis |
| Illustration voice | [`illustration_style.py`](illustration_style.py) — amber accent |
| Translucency | `vellum` (unchanged) |
| Motion | `quiet` (unchanged — may graduate to `languid` once we have that recipe) |
| Typography | `default` (unchanged) |

## Why this exists at all

Two reasons:

1. **Schema pressure-test.** If adding a coherent second voice required
   touching typography, motion, translucency, components, layouts — the
   schema wasn't tight enough. Here, the only new work is the palette
   entry and the narrative. That's the north star.
2. **Real use case waiting.** Long-form story surfaces benefit from
   feeling warmer than the product surfaces. `warm-drift` gives them a
   one-line opt-in (`<html data-theme="warm-drift">`) without
   spinning up a separate sub-brand.
