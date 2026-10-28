"""Leo brand tokens — CANONICAL source of truth.

Hand-edit this file; every derived artefact is regenerated from it by
``python -m brand.build`` (tokens.json, tokens.ts, tokens.css, vars.css).

Three old sources of truth collapsed here (Phase 4 Wave 2, plan §3.8,
design.md D2):

    * ``packages/ui/src/brand.ts`` (TS constants — canvas, Mapbox paint,
      emails; pre-consolidation path was ``unmigrated/scope-app/packages/ui/src/brand.ts``).
    * ``packages/ui/src/theme.css`` (Tailwind ``@theme`` block;
      pre-consolidation path was ``unmigrated/scope-app/packages/ui/src/theme.css``).
    * ``apps/scope/product/public/brand-vars.css`` (landing-page ``:root`` tokens;
      pre-consolidation path was ``unmigrated/scope-app/public/brand-vars.css``).

All three are now derived from this file. Change any colour, radius,
shadow, or font string here and re-run ``python -m brand.build`` —
every consuming surface updates.

Naming conventions inside this file:
    * keys use snake_case Python identifiers (``cream_dark`` not
      ``cream-dk`` or ``creamDark``).
    * derived TS gets camelCase (``creamDark``); derived CSS gets
      kebab-case (``--cream-dark``).
    * the old drift-driven dual names (``--cream-dk`` /
      ``--terracotta``) are preserved as ``LEGACY_CSS_ALIASES`` for
      the migration window. They are removed in the final
      shim-removal batch.
"""

from __future__ import annotations

from typing import Final, Mapping

__all__ = [
    "COLORS",
    "RADIUS",
    "SHADOWS",
    "FONTS",
    "THEMES",
    "LOGO_URLS",
    "FAVICON_SVG",
    "FONTS_URL",
    "BRAND",
    "LEGACY_CSS_ALIASES",
    "CARD_SEMANTIC_ALIASES",
    "UTILITY_CLASSES_CSS",
    "HTML_SMOOTHING_CSS",
    "APP_VARS_CSS",
]


COLORS: Final[Mapping[str, str]] = {
    "ink": "#1C1917",
    "ink_dark": "#292524",
    "ink_light": "#44403c",
    "ink_black": "#0F0E0C",
    "ink_fixed": "#1C1917",
    "ink_dark_fixed": "#292524",
    "ink_black_fixed": "#0F0E0C",
    "cream": "#FAF8F4",
    "cream_dark": "#F0EBE3",
    "stone": "#57534E",
    "muted": "#A8A29E",
    "border": "#E7E1D8",
    "card": "#FFFFFF",
    "cream_fixed": "#FAF8F4",
    "terracotta": "#DA654D",
    "terracotta_light": "#FDF0ED",
    "terracotta_dark": "#C8533C",
    "teal": "#115E59",
    "teal_light": "#ECFDF5",
    "teal_dark": "#0D4F47",
    "amber": "#F59E0B",
    "amber_light": "#FFFBEB",
    "amber_dark": "#92400E",
    "green": "#10B981",
    "green_light": "#ECFDF5",
    "green_dark": "#166534",
    "red": "#E53E3E",
    "red_light": "#FEE2E2",
    "wa_green": "#25D366",
    "wa_green_dark": "#1EB853",
    # Chat user bubble — terracotta by default (Leo/Scope), overridden per
    # theme (e.g. vitrina_sky uses sky-light + ink text). The old
    # hardcoded `var(--terra, #DA654D)` on `.leo-chat-user` in
    # `effects.css` reads these now so every surface can reskin without
    # touching CSS.
    "user_bubble_bg":   "#DA654D",
    "user_bubble_text": "#FFFFFF",
}


RADIUS: Final[Mapping[str, str]] = {
    "xs": "3px",
    "sm": "6px",
    "md": "8px",
    "lg": "14px",
    "xl": "20px",
    "pill": "999px",
}


SHADOWS: Final[Mapping[str, str]] = {
    "header_light": "0 1px 4px rgba(0,0,0,.04)",
    "header_dark": "0 1px 4px rgba(0,0,0,.2), 0 0 1px rgba(0,0,0,.3)",
    "card": "0 4px 16px rgba(0,0,0,.08)",
    "card_hover": "0 8px 30px rgba(0,0,0,.08)",
    "modal": "0 24px 80px rgba(0,0,0,.45), 0 0 0 1px rgba(255,255,255,.04) inset",
    "dropdown": "0 4px 20px rgba(0,0,0,.12)",
    "glass_light": "0 8px 32px rgba(0,0,0,.08), inset 0 1px 0 rgba(255,255,255,.8)",
    "glass_dark": "0 8px 32px rgba(0,0,0,.25), inset 0 1px 0 rgba(255,255,255,.06)",
    "hero_cta": "0 4px 24px rgba(0,0,0,.25)",
    "focus_terra": "0 0 0 3px rgba(218,101,77,.18)",
}


FONTS: Final[Mapping[str, str]] = {
    "display": "'Playfair Display', Georgia, serif",
    "heading": "'Playfair Display', Georgia, serif",
    "body": "'Source Sans 3', system-ui, sans-serif",
    "serif": "'Playfair Display', Georgia, serif",
    "sans": "'Source Sans 3', system-ui, sans-serif",
}


# ── Theme overrides ─────────────────────────────────────────────────────────
#
# THEMES lets a surface flip its visual vocabulary by setting
# ``<html data-theme="<name>">`` — zero JS, zero rebuild. The build emits a
# ``[data-theme="<name>"] { ... }`` block alongside the default ``:root``
# block in both ``vars.css`` (landing pages / raw HTML) and ``tokens.css``
# (Tailwind v4 ``@theme`` consumers). Keys inside a theme match the
# snake_case keys of the categories above (``colors``, ``radius``,
# ``shadows``, ``fonts``); only overrides that differ from the default
# need listing.
#
# Pattern borrowed from Anthropic's Claude Design (April 2026). The
# mechanism is per-surface, so a single page can scope a theme to a subtree
# by nesting ``<div data-theme="dark">`` inside a light-themed root.
#
# Initial population: ``dark`` theme, tuned for the ink/cream duality.
# More themes (white-label, high-contrast, print) populate as apps demand
# them — see Phase 5 Wave 9.

THEMES: Final[Mapping[str, Mapping[str, Mapping[str, str]]]] = {
    "dark": {
        "colors": {
            "ink":        "#FAF8F4",
            "ink_dark":   "#F0EBE3",
            "ink_light":  "#D6CFC3",
            "ink_black":  "#FFFFFF",
            "cream":      "#1A1714",
            "cream_dark": "#0F0E0C",
            "stone":      "#D6CFC3",
            "muted":      "#78716C",
            "border":     "#3B3632",
            "card":       "#252220",
        },
    },
    # `warm_drift` — evening golden hour voice. Cream warms to wheat,
    # borders soften, terracotta picks up more amber. Narrative +
    # illustration voice + gradients live at
    # `brand/themes/warm_drift/`; this entry carries colours only.
    "warm_drift": {
        "colors": {
            "ink":             "#2A2520",
            "ink_dark":        "#3A3226",
            "ink_light":       "#5A4E42",
            "ink_black":       "#1A1510",
            "cream":           "#F7EFE0",
            "cream_dark":      "#EADFC8",
            "stone":           "#7A6A54",
            "muted":           "#B5A68A",
            "border":          "#DCCDAF",
            "card":            "#FCF6E9",
            "terracotta":      "#E07A4D",
            "terracotta_light": "#FDF1E5",
            "terracotta_dark": "#B45A34",
            "amber":           "#D99A2B",
            "amber_light":     "#FBF4DE",
            "amber_dark":      "#8F6512",
        },
    },
    # `vitrina_sky` — shopper surface voice. Baby sky blue is the room
    # background; Dijon honey-mustard is the single CTA colour; azure
    # carries links and focus rings; warm_drift terracotta held back as
    # a tertiary "fun toys" accent. Narrative + illustration voice +
    # gradients live at `brand/themes/vitrina_sky/`; this entry carries
    # colours only. Paired with gradient palette `blueWhite` (see
    # `brand/themes/vitrina_sky/gradients.py`).
    "vitrina_sky": {
        "colors": {
            # Ink (deep slate reads clearly on cloud-white)
            "ink":             "#1F2A3A",
            "ink_dark":        "#0F1826",
            "ink_light":       "#4A5468",
            "ink_black":       "#0A1120",
            # Cloud / paper surfaces — nudged a hair toward warm
            # limestone (2026-04 per Peter: "a little more towards
            # limestone, just a lil bit") so the base paper reads as
            # sunlit stone rather than cool cloud-white.  Card stays a
            # bright neutral so elevated surfaces still pop off the page.
            "cream":           "#F7F2E4",
            "cream_dark":      "#ECE1C8",
            "stone":           "#6B7892",
            "muted":           "#9AA7BD",
            "border":          "#E4DCC6",
            "card":            "#FCFBF6",
            # Primary accent: Dijon honey-mustard (CTAs, buy buttons,
            # pay highlights, selected states). This is the one colour
            # that says "act" in the shopper UI.
            "dijon":           "#D89B2E",
            "dijon_light":     "#F9E8C2",
            "dijon_dark":      "#8A6116",
            # Secondary accent: sky azure (links, focus rings, info chips)
            "sky":             "#3F7DD6",
            "sky_light":       "#CEE4FB",
            "sky_dark":        "#1F4B96",
            # Tertiary "fun toys" accent — borrowed from warm_drift.
            # Use sparingly: a star ingredient in a recipe, a special
            # shop badge. Never as a CTA.
            "terracotta":      "#E07A4D",
            "terracotta_light": "#FDF1E5",
            "terracotta_dark": "#B45A34",
            # User bubble overrides — sky-light surface + ink text for the
            # shopper voice. Leo/Scope keep terracotta via COLORS default.
            "user_bubble_bg":   "#CEE4FB",
            "user_bubble_text": "#1F2A3A",
        },
    },
}


LOGO_URLS: Final[Mapping[str, str]] = {
    "charcoal": "/brand/leo-charcoal.svg",
    "cream": "/brand/leo-cream.svg",
}


FAVICON_SVG: Final[str] = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32">\n'
    '  <rect width="32" height="32" rx="7" fill="#1C1917"/>\n'
    '  <text x="16" y="23" text-anchor="middle" font-family="Georgia,serif"'
    ' font-size="19" font-weight="700" fill="#FAF8F4">L</text>\n'
    "</svg>"
)


FONTS_URL: Final[str] = (
    "https://fonts.googleapis.com/css2?"
    "family=Playfair+Display:ital,wght@0,400;0,500;0,600;0,700;1,400;1,500"
    "&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400"
    "&family=Google+Sans:wght@400;500;600;700"
    "&display=swap"
)


BRAND: Final[Mapping[str, object]] = {
    "colors": COLORS,
    "radius": RADIUS,
    "shadows": SHADOWS,
    "fonts": FONTS,
    "themes": THEMES,
    "logo": LOGO_URLS,
    "faviconSvg": FAVICON_SVG,
    "fontsUrl": FONTS_URL,
}


LEGACY_CSS_ALIASES: Final[Mapping[str, str]] = {
    "cream-dk": "var(--cream-dark)",
    "terra": "var(--terracotta)",
    "terra-dk": "var(--terracotta-dark)",
    "terra-lt": "var(--terracotta-light)",
    "terracotta": "var(--terra)",
    "terracotta-dk": "var(--terra-dk)",
    "terracotta-lt": "var(--terra-lt)",
    "r": "6px",
    "r-sm": "6px",
    "r-xs": "3px",
    "r-md": "8px",
    "r-lg": "14px",
    "r-xl": "20px",
    "r-pill": "999px",
    "amber-dk": "var(--amber-dark)",
    "amber-lt": "var(--amber-light)",
    "green-dk": "var(--green-dark)",
    "green-lt": "var(--green-light)",
    "red-lt": "var(--red-light)",
    "teal-dk": "var(--teal-dark)",
    "teal-lt": "var(--teal-light)",
    "ink-dark-fixed": "#292524",
    "wa-green-dk": "var(--wa-green-dark)",
    "card-solid": "var(--card)",
    "card-bg": "var(--card)",
    "card-bg-muted": "var(--cream-dark)",
    "card-bg-dark": "var(--ink-fixed)",
    "card-border": "var(--border)",
    "card-border-dark": "rgba(255,255,255,.12)",
    "card-text": "var(--ink)",
    "card-text-dark": "var(--cream)",
    "card-radius": "6px",
    "card-radius-feature": "14px",
    "modal-radius": "20px",
}


CARD_SEMANTIC_ALIASES: Final[Mapping[str, str]] = {
    "card_bg": "var(--card)",
    "card_bg_muted": "var(--cream-dark)",
    "card_bg_dark": "var(--ink-fixed)",
    "card_border": "var(--border)",
    "card_border_dark": "var(--scrim-white-12)",
    "card_text": "var(--ink)",
    "card_text_dark": "var(--cream)",
    "card_solid": "#FFFFFF",
    "card_radius": "var(--r)",
    "card_radius_feature": "var(--r-lg)",
    "modal_radius": "var(--r-xl)",
}


SCRIM_TOKENS: Final[Mapping[str, str]] = {
    "white_08": "rgba(255,255,255,.08)",
    "white_12": "rgba(255,255,255,.12)",
    "white_15": "rgba(255,255,255,.15)",
    "white_55": "rgba(255,255,255,.55)",
    "white_65": "rgba(255,255,255,.65)",
    "white_92": "rgba(255,255,255,.92)",
    "black_04": "rgba(0,0,0,.04)",
    "black_06": "rgba(0,0,0,.06)",
    "black_08": "rgba(0,0,0,.08)",
    "black_12": "rgba(0,0,0,.12)",
    "black_25": "rgba(0,0,0,.25)",
    "black_35": "rgba(0,0,0,.35)",
    "black_45": "rgba(0,0,0,.45)",
    "black_55": "rgba(0,0,0,.55)",
}


UTILITY_CLASSES_CSS: Final[str] = """\
.card-title,
h3.card-title {
  margin: 0 0 6px;
  font-family: var(--serif);
  font-size: 17px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -.01em;
  line-height: 1.25;
}
.card-title-sm,
h3.card-title-sm {
  margin: 0 0 3px;
  font-family: var(--serif);
  font-size: 14px;
  font-weight: 600;
  color: var(--ink);
  line-height: 1.25;
}
.card-title-on-dark,
h3.card-title-on-dark {
  margin: 0 0 2px;
  font-family: var(--serif);
  font-size: 16px;
  font-weight: 600;
  color: #fff;
  line-height: 1.25;
}
.display-num {
  font-family: var(--serif);
  font-weight: 700;
  letter-spacing: -.02em;
  line-height: 1;
}
"""


HTML_SMOOTHING_CSS: Final[str] = """\
html {
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}
"""


# ── Per-app brand overrides ─────────────────────────────────────────────────
#
# The shared ``COLORS``/``FONTS``/``THEMES`` above are the Leo/Scope/Vitrina
# default identity. A single app can override its *generated* artefacts
# WITHOUT recolouring the shared defaults (and therefore without touching any
# other app) by registering an entry here, keyed by the app slug used in
# ``build.PUBLIC_SYNC_TARGETS`` / ``build.PUBLIC_DIRS``.
#
# Per-app overrides are applied only while syncing that app's public vars.css.
# Rocoto's former override moved with its source to Rocoto-Labs/site.
APP_VARS_CSS: Final[Mapping[str, str]] = {}
