# brand/examples — tiny CLI demos of each brand capability

One script per capability. Each one is small (20–60 lines), CLI-driven,
and writes output to `packages/brand/scratch/` by default. Use them
whenever you want to *see* what the brand package can do — no committing
required.

## Conventions

- Every script is a standalone file: `python3 packages/brand/examples/<name>.py` (run from repo root).
- Default output path is under `packages/brand/scratch/`.
- No script commits anything. All outputs are gitignored.
- Scripts read theme names live from `brand.themes` and style names
  live from `brand.translucency` / `brand.motion` / `brand.typography` —
  when you add a new theme or named style, the CLI surfaces it
  automatically.

## Available demos

| Script | What it shows |
|--------|---------------|
| `illustrate.py` | Theme-aware pencil illustration (SVG lane or raster lane). Needs a running LiteLLM proxy (see `apps/scope/product/backend/litellm-config.yaml`). |

## Adding a new demo

1. Create `packages/brand/examples/<name>.py`.
2. Keep it small. If it grows past ~80 lines, it's probably a
   capability and belongs in `packages/brand/src/brand/` instead.
3. Default `--out` into `packages/brand/scratch/`.
4. Add a row to the table above.
