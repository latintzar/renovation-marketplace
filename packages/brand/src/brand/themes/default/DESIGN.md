# `default` — the quiet-trust Leo voice

> Cream paper, ink text, terracotta when it matters.

## Mood

Leo in its natural state. A contractor's notebook on a kitchen counter.
Morning light. The product is present but unshowy; it earned its spot
on the counter by being useful, not by begging for attention.

## Why this is the default

- **It's the tested voice.** Every leo.casa page, every scope surface,
  every marketing asset so far sits in this palette. We know it works.
- **It's the least opinionated.** Deviations from cream + ink + terracotta
  are additive — a new theme adds warmth (warm-drift) or inverts for
  low-light (dark) but doesn't invent a new primary voice.
- **It pairs cleanly with pencil illustrations.** The cream background
  makes black line-art feel hand-drawn rather than stark.

## The seven slots

| Slot | Value |
|---|---|
| Narrative | this file |
| Palette | `tokens.py` defaults (no `THEMES` entry — it *is* the default) |
| Gradient stops | [`gradients.py`](gradients.py) |
| Illustration voice | [`illustration_style.py`](illustration_style.py) |
| Translucency | `vellum` |
| Motion | `quiet` |
| Typography | `default` |

## When to reach for another theme

- **Late-hours product surface** → `dark`.
- **Reflective / story / blog tone where cream should feel golden** →
  `warm-drift`.

Everything else stays here.
