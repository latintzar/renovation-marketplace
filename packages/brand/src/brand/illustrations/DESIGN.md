# brand.illustrations — design

## Grand goal

Custom hand-drawn illustrations for Leo, generated on demand, usable as icons, site decoration, animation frames, and anywhere else a brand would hire an illustrator. One recognisable register across every surface.

## The register (one register, every theme)

Matisse drew this in thirty seconds with a black felt-tip marker. Child's freedom, painter's instinct for gesture. Not a kid's schema, not an illustrator's draftsmanship — naive but alive. The drawing captures the *essence* of the subject through pose, weight, and distortion. One motif per image.

Concretely:

- **One uniform stroke width**, edge-to-edge and across every drawing we ever make. A panther and a letter B in this register have identical line weight.
- **Committed wobbly lines** — one confident pass per contour, never re-traced. Overshoots, missed closures, bowed straights, bulging curves. A line that went "wrong" stays.
- **Black ink only, transparent background.** No colour, no grey, no shading. Theme accent colours apply at tint/composite time downstream, never at draw time. One master, every theme.
- **Matisse-naive abstraction for animals and people** — iconic silhouette + a few gesture marks. No anatomy. No observational sketching. A panther is a stalking arc + tail flick, not a correctly-proportioned cat.
- **Cool confident-casual vibe** — Babbo, Graza, Teenage Engineering register. Never cute, never twee, never generative-line-art polish.
- **One motif per image.** A single character OR object OR letter OR arrow OR mark. Compositions assembled at layout time.
- **1:1 square, motif fills 40–65%**, centred, fully visible, generous white margin.

The full register is frozen in [`prompts/raster_bold_marker.md`](prompts/raster_bold_marker.md). Register-of-record baseline atoms in [`baseline/`](baseline/).

## Architecture

Three layers, thin:

1. **Prompt** (`prompts/raster_bold_marker.md`) — two-block template: fixed STYLE + single `{scene}` slot. Style never parameterised.
2. **Providers** (`providers/`)
   - `litellm_raster.py` — Gemini 3 Pro Image / Nano Banana Pro via OpenRouter → PNG → `post/luminosity_alpha.py` (white → transparent, force RGB to black).
   - `litellm_raster_refs.py` — same model, multi-image chat endpoint, for character consistency (up to 5 reference images).
   - `vtracer_vector.py` — raster lane + vtracer binary trace → SVG.
3. **Dispatcher** (`generate.py`) — `generate()` / `generate_with_references()`. Accepts a `theme` name for API symmetry but the drawing is identical across themes; theme only resolves the accent colour for downstream tint.

## Style metadata

The only thing a theme varies about illustrations is `accent_color`, used by downstream tint/composite helpers. `brand.illustrations.style.IllustrationStyle` is a two-field dataclass (name + accent_color). Each theme's `illustration_style.py` exports a `DEFAULT` of this type.

## Why Gemini 3 Pro Image

- Good prompt adherence (critical — the register lives in the prompt).
- Native multi-image input for consistent-character work.
- 2K default, 4K available.

Routed through OpenRouter → LiteLLM proxy so we stay API-key-stable and don't talk to Google directly. See `apps/scope/product/backend/litellm-config.yaml`.

## Writing briefs

Briefs are a real style lever. Pair the noun with attitude — especially for animals and people.

Cool: `a panther prowling, half-lidded eyes, cool and relaxed`.
Not cool: `a panther`.

See `baseline/README.md` for the attitude vocabulary.

Rule: never two things in one brief. No "and", no "with". One motif per image.

## What we tried and discarded

- **Claude-writes-SVG lane** — LLM-invented SVG is visibly synthetic (too few paths, no hand character). Deleted. Always trace a raster instead.
- **Per-theme prompt variation** — theme-level `line_weight`, `grain_strength`, `mood_adjectives` knobs fought the frozen register and caused drift between subjects. Removed.
- **Style overlays** (`house`, `haring_cool`, `club`) — we had three registers for a while; the Matisse-naive register covers everything we actually need, so the overlay system was scrapped for simplicity.
- **"Three laws: ink only / no fine line / no text"** — earlier constraint that forbade letters and thin marker lines. Dropped in favour of the current register, which includes letters/arrows drawn in the same hand.

## Future

- Tint helper: black master → theme accent colour at composite time.
- Atom library: build out ~30 canonical atoms (core animals, objects, marks, letters) so apps can reach for pre-rendered assets instead of re-generating.
- Animation: single masters can be used as keyframes; tweening is a layer on top of this.
