# Baseline illustration atoms

These four PNGs are the register-of-record for the Leo house illustration style. Any future prompt change, model swap, or library addition should produce outputs that feel *by the same hand* as these.

| File              | Brief used                                                          |
| ----------------- | ------------------------------------------------------------------- |
| `panther.png`     | `a panther prowling, half-lidded eyes, cool and relaxed`            |
| `wine-bottle.png` | `a wine bottle`                                                     |
| `letter-b.png`    | `the letter B`                                                      |
| `arrow-right.png` | `an arrow pointing right`                                           |

Rendered via `packages/brand/examples/illustrate.py` against Gemini 3 Pro Image / Nano Banana Pro (through OpenRouter → LiteLLM). Prompt frozen at `packages/brand/src/brand/illustrations/prompts/raster_bold_marker.md`.

## Register, in one paragraph

Matisse drew this in thirty seconds with a black felt-tip marker — child's freedom, painter's instinct for gesture. Single uniform stroke width edge-to-edge AND across every drawing. Committed wobbly lines (one confident pass, never re-traced). Naive-but-alive abstraction: the *gesture* is the subject, not anatomy. One motif per image, 1:1 square, generous margin, black ink on transparent, no colour, no shading. Cool confident-casual vibe — Babbo / Graza / Teenage Engineering register, never cute, never twee.

## Writing cool briefs

The brief is a real style lever. Pair the noun with attitude:

- animals — "prowling", "half-lidded", "slouched", "mid-stretch", "strutting", "deadpan"
- people — "leaning back", "arms crossed", "mid-laugh", "unbothered"
- objects — plain noun usually enough; add a leaning adjective if you want weight
- letters / marks — plain noun; orientation if it matters ("arrow pointing right")

Never brief combos ("panther and bottle"). One motif per image; compositions are assembled at layout time.
