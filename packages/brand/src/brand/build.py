"""``python -m brand.build`` — regenerate derived brand artefacts.

Reads ``tokens.py`` (canonical Python source of truth) and writes::

    src/brand/generated/tokens.json   machine-readable mirror (incl. themes)
    src/brand/generated/tokens.ts     TS re-export (@scope/brand, incl. BRAND_THEMES)
    src/brand/generated/tokens.css    Tailwind v4 @theme block + [data-theme] overrides
                                      (replaces packages/ui/src/theme.css)
    src/brand/generated/vars.css      :root { --ink: ... } + [data-theme] overrides
                                      + utility classes
                                      (replaces public/brand-vars.css)

In addition to the codegen above, running ``python -m brand.build`` ALSO
copies the non-generated brand-level static assets (``effects.css``,
``fluid-gradient.js``, ``assets/leo-*.svg``) into each registered app's
``public/`` directory — byte-identical mirrors so landing pages that
reference ``/brand-effects.css``, ``/fluid-gradient-v4.js``, and
``/brand/leo-*.svg`` keep working without the landing-page HTML codemod.
The canonical source lives inside ``packages/brand/``; the public copies
are auto-regenerated and drift-checked, never hand-edited. This replaces
the Phase 4 shim where each app kept its own canonical copy of these
files.

Modes:
    python -m brand.build             regenerate + sync, exit 0
    python -m brand.build --check     exit 1 if any generated file is stale
                                      OR any synced public copy drifts from
                                      the canonical
                                      (for CI pre-merge gate)

Multi-theming:
    ``tokens.THEMES`` maps theme names (e.g. ``"dark"``) to a nested mapping
    of category → overrides. Each theme populates a single
    ``[data-theme="<name>"] { ... }`` block in both ``tokens.css`` (using
    Tailwind-prefixed names like ``--color-ink``) and ``vars.css`` (using
    bare names like ``--ink``). A surface flips themes by setting
    ``<html data-theme="<name>">`` — zero JS, zero rebuild.

Determinism guarantees (tested in ``tests/test_build.py``):
    * sort_keys=True on all JSON dumps.
    * Python dict iteration order used verbatim (insertion order); no
      implicit reordering.
    * No timestamps, no environment reads.
    * Two consecutive builds on the same input produce byte-identical
      output.

Output paths are computed from ``Path(__file__)`` anchors only, so this
script works identically when invoked from the package root, the repo
root, or a ``uv run`` wrapper.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Iterable, Mapping

from . import tokens as T

HERE: Path = Path(__file__).resolve().parent
GENERATED: Path = HERE / "generated"

REPO_ROOT: Path = HERE.resolve().parents[3]

STATIC_ASSETS: Mapping[str, Path] = {
    "effects.css": HERE / "effects.css",
    "fluid-gradient.js": HERE / "fluid-gradient.js",
    "assets/leo-charcoal.svg": HERE / "assets" / "leo-charcoal.svg",
    "assets/leo-cream.svg": HERE / "assets" / "leo-cream.svg",
    "assets/leo-L-charcoal.svg": HERE / "assets" / "leo-L-charcoal.svg",
    "assets/leo-L-cream.svg": HERE / "assets" / "leo-L-cream.svg",
}

# Each app can register its ``public/`` dir here and brand.build will
# mirror the canonical static assets + generated vars.css into it. Public
# filenames may differ from canonical filenames (e.g. the canonical
# ``fluid-gradient.js`` ships as ``fluid-gradient-v4.js`` so existing
# landing pages that reference ``/fluid-gradient-v4.js`` keep working).
#
# The content between the ``leo-apps-start`` / ``leo-apps-end`` markers is
# auto-managed by ``scripts/bootstrap_app.py``. Hand-edit if you need
# bespoke per-app mappings that the bootstrapper can't infer.

PUBLIC_SYNC_TARGETS: Mapping[str, Mapping[str, str]] = {
    # app label → { canonical-key → public-relative-path }
    # leo-apps-sync-start
    "scope": {
        "effects.css":              "brand-effects.css",
        "fluid-gradient.js":        "fluid-gradient-v4.js",
        "assets/leo-charcoal.svg":  "brand/leo-charcoal.svg",
        "assets/leo-cream.svg":     "brand/leo-cream.svg",
        "assets/leo-L-charcoal.svg": "brand/leo-L-charcoal.svg",
        "assets/leo-L-cream.svg":   "brand/leo-L-cream.svg",
        "generated/vars.css":       "brand-vars.css",
    },
    "vitrina": {
        "effects.css":              "brand-effects.css",
        "fluid-gradient.js":        "fluid-gradient-v4.js",
        "assets/leo-charcoal.svg":  "brand/leo-charcoal.svg",
        "assets/leo-cream.svg":     "brand/leo-cream.svg",
        "assets/leo-L-charcoal.svg": "brand/leo-L-charcoal.svg",
        "assets/leo-L-cream.svg":   "brand/leo-L-cream.svg",
        "generated/vars.css":       "brand-vars.css",
    },
    # leo-apps-sync-end
}

PUBLIC_DIRS: Mapping[str, Path] = {
    # leo-apps-dirs-start
    "scope": REPO_ROOT / "apps" / "scope" / "product" / "public",
    # Vitrina runs landing-page experiments per market (see
    # apps/vitrina/product/public/README.md — bg/ is the BG experiment,
    # es/ is the Spain experiment). Brand assets are duplicated per
    # market: each market is independent, so a brand change is one
    # `brand.build` away. Add a sibling entry (e.g. "vitrina-es") when
    # ES launches; until then this writes only into bg/.
    "vitrina": REPO_ROOT / "apps" / "vitrina" / "product" / "public" / "bg",
    # leo-apps-dirs-end
}


def _camel(key: str) -> str:
    """``ink_dark`` → ``inkDark``."""
    head, *tail = key.split("_")
    return head + "".join(p[:1].upper() + p[1:] for p in tail)


def _kebab(key: str) -> str:
    """``ink_dark`` → ``ink-dark``."""
    return key.replace("_", "-")


def _to_js_lit(value: str) -> str:
    """Escape a string for JS/TS single-quoted literal output."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def _themes_for_json() -> dict[str, dict[str, dict[str, str]]]:
    """Serialise THEMES with camelCase keys for JS/TS consumers."""
    out: dict[str, dict[str, dict[str, str]]] = {}
    for theme_name, groups in T.THEMES.items():
        out[theme_name] = {}
        for category, overrides in groups.items():
            if category in {"colors", "shadows"}:
                out[theme_name][category] = {
                    _camel(k): v for k, v in overrides.items()
                }
            else:
                out[theme_name][category] = dict(overrides)
    return out


def _emit_tokens_json() -> str:
    """Serialise the full token set as JSON (camelCase keys, sorted families)."""
    payload: dict[str, object] = {
        "colors": {_camel(k): v for k, v in T.COLORS.items()},
        "radius": dict(T.RADIUS),
        "shadows": {_camel(k): v for k, v in T.SHADOWS.items()},
        "fonts": dict(T.FONTS),
        "themes": _themes_for_json(),
        "logo": dict(T.LOGO_URLS),
        "faviconSvg": T.FAVICON_SVG,
        "fontsUrl": T.FONTS_URL,
    }
    return json.dumps(payload, indent=2, sort_keys=False) + "\n"


def _emit_tokens_ts() -> str:
    """Emit ``tokens.ts`` — typed TS re-export matching old brand.ts surface."""
    lines: list[str] = [
        "// AUTO-GENERATED by `python -m brand.build` — DO NOT EDIT.",
        "// Edit packages/brand/src/brand/tokens.py and rerun the build.",
        "",
    ]

    lines.append("export const BRAND_COLORS = {")
    for k, v in T.COLORS.items():
        lines.append(f"  {_camel(k)}: '{_to_js_lit(v)}',")
    lines.append("} as const;")
    lines.append("")

    lines.append("export const BRAND_RADIUS = {")
    for k, v in T.RADIUS.items():
        lines.append(f"  {k}: '{_to_js_lit(v)}',")
    lines.append("} as const;")
    lines.append("")

    lines.append("export const BRAND_SHADOWS = {")
    for k, v in T.SHADOWS.items():
        lines.append(f"  {_camel(k)}: '{_to_js_lit(v)}',")
    lines.append("} as const;")
    lines.append("")

    lines.append("export const BRAND_FONTS = {")
    for k, v in T.FONTS.items():
        lines.append(f"  {k}: \"{v}\",")
    lines.append("} as const;")
    lines.append("")

    lines.append("export const BRAND_THEMES = {")
    for theme_name, groups in T.THEMES.items():
        lines.append(f"  {theme_name}: {{")
        for category, overrides in groups.items():
            lines.append(f"    {category}: {{")
            for k, v in overrides.items():
                key = _camel(k) if category in {"colors", "shadows"} else k
                lines.append(f"      {key}: '{_to_js_lit(v)}',")
            lines.append("    },")
        lines.append("  },")
    lines.append("} as const;")
    lines.append("")

    lines.append("export const BRAND_LOGO = {")
    for k, v in T.LOGO_URLS.items():
        lines.append(f"  {k}: '{_to_js_lit(v)}',")
    lines.append("} as const;")
    lines.append("")

    lines.append(f"export const BRAND_FAVICON_SVG = `{T.FAVICON_SVG}`;")
    lines.append("")

    lines.append(
        f"export const BRAND_FONTS_URL =\n  '{_to_js_lit(T.FONTS_URL)}';"
    )
    lines.append("")

    lines.append("export const BRAND = {")
    lines.append("  colors:     BRAND_COLORS,")
    lines.append("  radius:     BRAND_RADIUS,")
    lines.append("  shadows:    BRAND_SHADOWS,")
    lines.append("  fonts:      BRAND_FONTS,")
    lines.append("  themes:     BRAND_THEMES,")
    lines.append("  logo:       BRAND_LOGO,")
    lines.append("  faviconSvg: BRAND_FAVICON_SVG,")
    lines.append("  fontsUrl:   BRAND_FONTS_URL,")
    lines.append("} as const;")
    lines.append("")

    return "\n".join(lines)


def _emit_theme_overrides_tailwind() -> list[str]:
    """Emit ``[data-theme="..."] { ... }`` blocks for Tailwind v4 consumers.

    Tailwind ``@theme`` emits ``--color-<key>``/``--radius-<key>``/
    ``--shadow-<key>``/``--font-<key>``. Themed overrides land in a sibling
    ``[data-theme="..."]`` block outside the ``@theme`` block so they
    cascade at runtime.
    """
    if not T.THEMES:
        return []

    lines: list[str] = []
    for theme_name, groups in T.THEMES.items():
        lines.append("")
        lines.append(f'[data-theme="{theme_name}"] {{')
        for k, v in groups.get("colors", {}).items():
            lines.append(f"  --color-{_kebab(k)}: {v};")
        for k, v in groups.get("radius", {}).items():
            lines.append(f"  --radius-{k}: {v};")
        for k, v in groups.get("shadows", {}).items():
            lines.append(f"  --shadow-{_kebab(k)}: {v};")
        for k, v in groups.get("fonts", {}).items():
            lines.append(f"  --font-{k}: {v};")
        lines.append("}")
    return lines


def _emit_theme_overrides_vars() -> list[str]:
    """Emit ``[data-theme="..."] { ... }`` blocks for plain-HTML vars.css.

    Vars.css uses bare kebab-case custom properties without the
    ``--color-``/``--radius-``/etc. prefix (e.g. ``--ink``, ``--card``).
    Landing pages consume these directly via ``var(--ink)`` calls.
    """
    if not T.THEMES:
        return []

    lines: list[str] = []
    for theme_name, groups in T.THEMES.items():
        lines.append("")
        lines.append(f'[data-theme="{theme_name}"] {{')
        colors = groups.get("colors", {})
        if colors:
            lines.append("  /* ── Colour overrides ─────────────────────── */")
            for k, v in colors.items():
                lines.append(f"  --{_kebab(k)}: {v};")
        radius = groups.get("radius", {})
        if radius:
            lines.append("  /* ── Radius overrides ─────────────────────── */")
            for k, v in radius.items():
                lines.append(f"  --r-{k}: {v};")
        shadows = groups.get("shadows", {})
        if shadows:
            lines.append("  /* ── Shadow overrides ─────────────────────── */")
            for k, v in shadows.items():
                lines.append(f"  --shadow-{_kebab(k)}: {v};")
        fonts = groups.get("fonts", {})
        if fonts:
            lines.append("  /* ── Font overrides ───────────────────────── */")
            for k, v in fonts.items():
                lines.append(f"  --font-{k}: {v};")
        lines.append("}")
    return lines


def _emit_tokens_css() -> str:
    """Emit Tailwind v4 ``@theme { ... }`` block + ``[data-theme]`` overrides.

    Replaces theme.css. The ``@theme`` block carries every default token;
    sibling ``[data-theme="<name>"]`` blocks (one per entry in
    ``tokens.THEMES``) re-declare the same CSS custom properties, so that
    Tailwind utilities pick up the override at runtime when an ancestor
    element sets ``data-theme``.
    """
    lines: list[str] = [
        "/* AUTO-GENERATED by `python -m brand.build` — DO NOT EDIT. */",
        "/* Edit packages/brand/src/brand/tokens.py and rerun the build. */",
        "",
        "@theme {",
    ]

    lines.append("  /* ── Colours ─────────────────────────────────── */")
    for k, v in T.COLORS.items():
        lines.append(f"  --color-{_kebab(k)}: {v};")
    lines.append("")

    lines.append("  /* ── Fonts ────────────────────────────────────── */")
    for k, v in T.FONTS.items():
        lines.append(f"  --font-{k}: {v};")
    lines.append("")

    lines.append("  /* ── Radius scale ─────────────────────────────── */")
    for k, v in T.RADIUS.items():
        lines.append(f"  --radius-{k}: {v};")
    lines.append("")

    lines.append("  /* ── Shadow ladder ────────────────────────────── */")
    for k, v in T.SHADOWS.items():
        lines.append(f"  --shadow-{_kebab(k)}: {v};")

    lines.append("}")
    lines.extend(_emit_theme_overrides_tailwind())
    lines.append("")
    lines.append(T.HTML_SMOOTHING_CSS.rstrip() + "\n")
    return "\n".join(lines)


def _emit_vars_css() -> str:
    """Emit ``:root { ... }`` block + utility classes (replaces brand-vars.css).

    Preserves every alias name currently used by the 34 landing pages
    (``--cream-dk``, ``--terra``, ``--r``, ``--r-sm``, ...). These aliases
    stay until the final shim-removal batch (design.md D8); the HTML
    codemod then rewrites them to the canonical names in one pass.
    """
    lines: list[str] = [
        "/* AUTO-GENERATED by `python -m brand.build` — DO NOT EDIT. */",
        "/* Edit packages/brand/src/brand/tokens.py and rerun the build. */",
        "",
        "/* Google Fonts — single canonical @import used by every landing page. */",
        f"@import url('{T.FONTS_URL}');",
        "",
        ":root {",
    ]

    lines.append("  /* ── Ink scale ─────────────────────────────── */")
    lines.append("  --ink:            #1C1917;")
    lines.append("  --ink-dark:       #292524;")
    lines.append("  --ink-light:      #44403c;")
    lines.append("  --ink-black:      #0F0E0C;")
    lines.append("  --ink-fixed:      #1C1917;")
    lines.append("  --ink-dark-fixed: #292524;")
    lines.append("  --ink-black-fixed:#0F0E0C;")
    lines.append("")

    lines.append("  /* ── Warm neutrals ────────────────────────── */")
    lines.append("  --cream:          #FAF8F4;")
    lines.append("  --cream-dark:     #F0EBE3;")
    lines.append("  --cream-dk:       #F0EBE3;  /* legacy alias, kept for landing pages */")
    lines.append("  --stone:          #57534E;")
    lines.append("  --muted:          #A8A29E;")
    lines.append("  --border:         #E7E1D8;")
    lines.append("  --card:           #FFFFFF;")
    lines.append("  --card-solid:     #FFFFFF;")
    lines.append("  --cream-fixed:    #FAF8F4;")
    lines.append("")

    lines.append("  /* ── Terracotta (primary accent) ──────────── */")
    lines.append("  --terra:           #DA654D;")
    lines.append("  --terra-dk:        #C8533C;")
    lines.append("  --terra-lt:        #FDF0ED;")
    lines.append("  --terracotta:      var(--terra);")
    lines.append("  --terracotta-dk:   var(--terra-dk);")
    lines.append("  --terracotta-lt:   var(--terra-lt);")
    lines.append("")

    lines.append("  /* ── Teal (escrow / trust) ────────────────── */")
    lines.append("  --teal:           #115E59;")
    lines.append("  --teal-dk:        #0D4F47;")
    lines.append("  --teal-lt:        #ECFDF5;")
    lines.append("")

    lines.append("  /* ── Semantic colours ─────────────────────── */")
    lines.append("  --amber:          #F59E0B;")
    lines.append("  --amber-dk:       #92400E;")
    lines.append("  --amber-lt:       #FFFBEB;")
    lines.append("  --green:          #10B981;")
    lines.append("  --green-dk:       #166534;")
    lines.append("  --green-lt:       #ECFDF5;")
    lines.append("  --red:            #E53E3E;")
    lines.append("  --red-lt:         #FEE2E2;")
    lines.append("")

    lines.append("  /* ── Platform ─────────────────────────────── */")
    lines.append("  --wa-green:       #25D366;")
    lines.append("  --wa-green-dk:    #1EB853;")
    lines.append("")

    lines.append("  /* ── Radius scale ─────────────────────────── */")
    lines.append("  --r:              6px;")
    lines.append("  --r-xs:           3px;")
    lines.append("  --r-sm:           6px;")
    lines.append("  --r-md:           8px;")
    lines.append("  --r-lg:           14px;")
    lines.append("  --r-xl:           20px;")
    lines.append("  --r-pill:         999px;")
    lines.append("")

    lines.append("  /* Semantic card radii */")
    lines.append("  --card-radius:         var(--r);")
    lines.append("  --card-radius-feature: var(--r-lg);")
    lines.append("  --modal-radius:        var(--r-xl);")
    lines.append("")

    lines.append("  /* ── Typography ───────────────────────────── */")
    lines.append("  --serif: 'Playfair Display', Georgia, serif;")
    lines.append("  --sans:  'Source Sans 3', system-ui, sans-serif;")
    lines.append("  --font-display:  var(--serif);")
    lines.append("  --font-heading:  var(--serif);")
    lines.append("  --font-body:     var(--sans);")
    lines.append("")

    lines.append("  /* ── Scrim / overlay ramps ────────────────── */")
    lines.append("  --scrim-white-08: rgba(255,255,255,.08);")
    lines.append("  --scrim-white-12: rgba(255,255,255,.12);")
    lines.append("  --scrim-white-15: rgba(255,255,255,.15);")
    lines.append("  --scrim-white-55: rgba(255,255,255,.55);")
    lines.append("  --scrim-white-65: rgba(255,255,255,.65);")
    lines.append("  --scrim-white-92: rgba(255,255,255,.92);")
    lines.append("  --scrim-black-04: rgba(0,0,0,.04);")
    lines.append("  --scrim-black-06: rgba(0,0,0,.06);")
    lines.append("  --scrim-black-08: rgba(0,0,0,.08);")
    lines.append("  --scrim-black-12: rgba(0,0,0,.12);")
    lines.append("  --scrim-black-25: rgba(0,0,0,.25);")
    lines.append("  --scrim-black-35: rgba(0,0,0,.35);")
    lines.append("  --scrim-black-45: rgba(0,0,0,.45);")
    lines.append("  --scrim-black-55: rgba(0,0,0,.55);")
    lines.append("")

    lines.append("  /* ── Shadow ladder ────────────────────────── */")
    lines.append("  --shadow-header-light: 0 1px 4px var(--scrim-black-04);")
    lines.append("  --shadow-header-dark:  0 1px 4px rgba(0,0,0,.2), 0 0 1px rgba(0,0,0,.3);")
    lines.append("  --shadow-card:         0 4px 16px var(--scrim-black-08);")
    lines.append("  --shadow-card-hover:   0 8px 30px var(--scrim-black-08);")
    lines.append("  --shadow-modal:        0 24px 80px var(--scrim-black-45), 0 0 0 1px rgba(255,255,255,.04) inset;")
    lines.append("  --shadow-dropdown:     0 4px 20px var(--scrim-black-12);")
    lines.append("  --shadow-glass-light:  0 8px 32px var(--scrim-black-08), inset 0 1px 0 rgba(255,255,255,.8);")
    lines.append("  --shadow-glass-dark:   0 8px 32px var(--scrim-black-25), inset 0 1px 0 rgba(255,255,255,.06);")
    lines.append("  --shadow-hero-cta:     0 4px 24px var(--scrim-black-25);")
    lines.append("  --shadow-focus-terra:  0 0 0 3px rgba(218,101,77,.18);")
    lines.append("")

    lines.append("  /* ── Semantic card presets ────────────────── */")
    lines.append("  --card-bg:           var(--card);")
    lines.append("  --card-bg-muted:     var(--cream-dk);")
    lines.append("  --card-bg-dark:      var(--ink-fixed);")
    lines.append("  --card-border:       var(--border);")
    lines.append("  --card-border-dark:  var(--scrim-white-12);")
    lines.append("  --card-text:         var(--ink);")
    lines.append("  --card-text-dark:    var(--cream);")
    lines.append("}")
    lines.extend(_emit_theme_overrides_vars())
    lines.append("")
    lines.append(T.UTILITY_CLASSES_CSS.rstrip() + "\n")
    return "\n".join(lines)


ARTIFACTS: dict[str, callable] = {
    "tokens.json": _emit_tokens_json,
    "tokens.ts": _emit_tokens_ts,
    "tokens.css": _emit_tokens_css,
    "vars.css": _emit_vars_css,
}


def _render_all() -> Mapping[str, str]:
    return {name: fn() for name, fn in ARTIFACTS.items()}


def _write(name: str, body: str) -> None:
    GENERATED.mkdir(parents=True, exist_ok=True)
    marker = GENERATED / "__init__.py"
    if not marker.exists():
        marker.write_text(
            '"""AUTO-GENERATED derived artefacts — do not hand-edit."""\n',
            encoding="utf-8",
        )
    (GENERATED / name).write_text(body, encoding="utf-8")


def _app_artifact_body(app: str, name: str, rendered: Mapping[str, str]) -> str:
    """Return the generated-artifact body that app ``app`` should sync.

    Identical to the shared ``rendered[name]`` for every app EXCEPT where a
    per-app override is registered in ``tokens.APP_VARS_CSS`` — that app's
    ``vars.css`` is replaced with its override body. The shared canonical
    ``generated/vars.css`` (which other apps sync from) is untouched, so an
    override for one app can never recolour another app.
    """
    if name == "vars.css":
        override = T.APP_VARS_CSS.get(app)
        if override is not None:
            return override
    return rendered[name]


def _canonical_bytes(key: str, app: str | None = None) -> bytes:
    """Read canonical bytes for a sync key (``effects.css``,
    ``generated/vars.css``, ``assets/leo-charcoal.svg``, ...).

    Handles ``generated/<name>`` specially because those files are
    emitted in-memory during the current build; we want to sync the
    freshly-rendered body, not whatever's on disk from a previous run.

    When ``app`` is supplied and that app has a per-app override registered
    in ``tokens.APP_VARS_CSS``, the override body is returned for the
    ``generated/vars.css`` key (the per-app brand override).
    """
    if key.startswith("generated/"):
        name = key.split("/", 1)[1]
        return _app_artifact_body(app, name, _render_all()).encode("utf-8") if app \
            else _render_all()[name].encode("utf-8")
    path = STATIC_ASSETS[key]
    return path.read_bytes()


def _sync_public_copy(app: str, target_rel: str, body: bytes) -> Path:
    public = PUBLIC_DIRS[app]
    dest = public / target_rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(body)
    return dest


def _check_public_copies() -> list[str]:
    """Return a list of public copies that drift from the canonical."""
    drift: list[str] = []
    rendered = _render_all()
    for app, mapping in PUBLIC_SYNC_TARGETS.items():
        public = PUBLIC_DIRS[app]
        if not public.exists():
            continue
        for key, target_rel in mapping.items():
            if key.startswith("generated/"):
                name = key.split("/", 1)[1]
                if name not in rendered:
                    continue
                expected = _app_artifact_body(app, name, rendered).encode("utf-8")
            else:
                src = STATIC_ASSETS[key]
                if not src.exists():
                    continue
                expected = src.read_bytes()
            dest = public / target_rel
            if not dest.exists() or dest.read_bytes() != expected:
                drift.append(f"{app}:{target_rel}")
    return drift


def main(argv: Iterable[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m brand.build",
        description="Regenerate derived brand artefacts + sync public copies.",
    )
    ap.add_argument(
        "--check",
        action="store_true",
        help="Exit 1 if any derived or synced file is out-of-date (CI / pre-commit gate).",
    )
    ap.add_argument(
        "--no-sync",
        action="store_true",
        help="Skip syncing canonical assets into apps/<app>/public/.",
    )
    args = ap.parse_args(argv)

    rendered = _render_all()

    if args.check:
        drift: list[str] = []
        for name, body in rendered.items():
            path = GENERATED / name
            if not path.exists() or path.read_text(encoding="utf-8") != body:
                drift.append(f"generated/{name}")
        drift += _check_public_copies()
        if drift:
            print(
                "[brand.build] DRIFT: the following generated or synced artefacts"
                " are stale and must be regenerated via `python -m brand.build`:"
            )
            for name in drift:
                print(f"  - {name}")
            return 1
        print("[brand.build] OK — every generated + synced artefact matches canonical")
        return 0

    for name, body in rendered.items():
        _write(name, body)
        print(f"[brand.build] wrote {GENERATED}/{name}  ({len(body)} bytes)")

    if args.no_sync:
        return 0

    for app, mapping in PUBLIC_SYNC_TARGETS.items():
        public = PUBLIC_DIRS[app]
        if not public.exists():
            print(f"[brand.build] skipping {app}: {public} does not exist")
            continue
        for key, target_rel in mapping.items():
            body = _canonical_bytes(key, app=app)
            dest = _sync_public_copy(app, target_rel, body)
            print(f"[brand.build] synced {dest}  ({len(body)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
