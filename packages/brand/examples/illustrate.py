"""Generate a throwaway illustration via the brand generator.

Invoke from repo root::

    python3 packages/brand/examples/illustrate.py \\
        --theme warm_drift \\
        --scene "a panther"

Single-motif briefs only — "a panther", "a wine bottle", "the letter
B", "an arrow pointing right". The house style renders one motif per
image; combos are layout-time concerns.

Both lanes go through ``brand.illustrations.generate`` which talks to
the LiteLLM proxy. Make sure the proxy is up (see
``apps/scope/product/backend/litellm-config.yaml``) before running.

Outputs land under ``packages/brand/scratch/`` by default and are
gitignored — this script is for looking, not shipping.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from brand.illustrations import Lane, Quality, generate
from brand.themes import names as theme_names


def _default_out(theme: str, lane: Lane, slug: str) -> Path:
    ext = "svg" if lane == "vector" else "png"
    scratch = Path(__file__).resolve().parent.parent / "scratch"
    return scratch / f"{slug}-{theme}.{ext}"


def _slug(scene: str) -> str:
    cleaned = "".join(c if c.isalnum() or c in " -" else " " for c in scene.lower())
    words = cleaned.split()
    return "-".join(words[:4]) or "illustration"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--theme",
        default="warm_drift",
        choices=theme_names(),
        help="Theme (reserved — style is currently frozen across themes).",
    )
    parser.add_argument(
        "--scene",
        required=True,
        help="Single-motif brief — 'a panther', 'a wine bottle', 'the letter B'.",
    )
    parser.add_argument(
        "--lane",
        default="raster",
        choices=("raster", "vector"),
        help=(
            "raster (default) — PNG via Gemini 3 Pro Image (Nano Banana Pro). "
            "vector — same raster traced with vtracer into an SVG. "
            "2–4x slower."
        ),
    )
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="WxH passed to the upstream image-gen model.",
    )
    parser.add_argument(
        "--quality",
        default="medium",
        choices=("standard", "medium", "high"),
        help="standard → 1K, medium → 2K (default), high → 4K (Pro only).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output path. Defaults to packages/brand/scratch/<slug>-<theme>.<ext>.",
    )
    args = parser.parse_args()

    lane: Lane = args.lane
    out = args.out or _default_out(args.theme, lane, _slug(args.scene))
    out.parent.mkdir(parents=True, exist_ok=True)

    print(f"theme : {args.theme}")
    print(f"scene : {args.scene}")
    print(f"lane  : {lane}")
    print(f"size  : {args.size}")
    print(f"out   : {out}")
    print("generating...", flush=True)

    quality: Quality = args.quality
    data = generate(
        theme=args.theme,
        scene=args.scene,
        lane=lane,
        size=args.size,
        quality=quality,
    )
    out.write_bytes(data)
    print(f"wrote {out} ({len(data)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
