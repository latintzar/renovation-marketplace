"""Smoke tests for ``brand.tokens`` — confirm the canonical source parses
and holds the invariants the rest of the pipeline relies on.
"""

from __future__ import annotations

import re

import pytest

from brand import tokens


_HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
_PX = re.compile(r"^\d+(?:\.\d+)?px$")
_PX_ZERO_OR_PCT = re.compile(r"^(0|9999px|\d+(?:\.\d+)?(?:px|%))$")


def test_colors_nonempty_and_hex_or_rgba() -> None:
    assert tokens.COLORS, "COLORS must not be empty"
    for name, value in tokens.COLORS.items():
        assert isinstance(value, str), f"{name} must be str, got {type(value).__name__}"
        assert _HEX.match(value) or value.startswith("rgba("), (
            f"{name} = {value!r} is neither a #RRGGBB hex nor an rgba() literal"
        )


def test_radius_monotonic_and_px_suffix() -> None:
    expected = ["xs", "sm", "md", "lg", "xl", "pill"]
    assert list(tokens.RADIUS.keys())[: len(expected)] == expected, (
        "RADIUS order drifted; semantic ordering matters for Tailwind"
    )

    def _radius_to_px(v: str) -> float:
        if v.endswith("px"):
            return float(v.removesuffix("px"))
        raise AssertionError(f"unexpected radius syntax: {v!r}")

    numeric = [_radius_to_px(tokens.RADIUS[k]) for k in expected[:-1]]
    assert numeric == sorted(numeric), (
        f"radius scale must be monotonic (xs < sm < md < lg < xl); got {numeric}"
    )
    assert tokens.RADIUS["pill"] == "999px", "pill matches old @scope/ui brand.ts RADIUS.pill"


def test_shadows_are_box_shadow_syntax() -> None:
    for name, value in tokens.SHADOWS.items():
        assert isinstance(value, str), f"{name} must be a CSS string"
        assert " " in value, f"{name} does not look like a box-shadow declaration"
        assert "rgba(" in value or "#" in value or value == "none", (
            f"{name} has no colour component: {value!r}"
        )


def test_fonts_keys() -> None:
    assert set(tokens.FONTS.keys()) >= {"display", "body", "serif", "sans"}


def test_favicon_svg_is_inline_svg() -> None:
    assert tokens.FAVICON_SVG.startswith("<svg")
    assert tokens.FAVICON_SVG.rstrip().endswith("</svg>")
    assert "Georgia" in tokens.FAVICON_SVG, (
        "favicon must use Georgia (not Playfair) — cannot load a Google Font in a "
        "data-URI favicon; see design.md D5"
    )


def test_fonts_url_is_google_fonts() -> None:
    assert tokens.FONTS_URL.startswith("https://fonts.googleapis.com/css2?")
    assert "Playfair+Display" in tokens.FONTS_URL
    assert "Source+Sans+3" in tokens.FONTS_URL


def test_brand_aggregate_references_subdicts() -> None:
    b = tokens.BRAND
    assert b["colors"] is tokens.COLORS
    assert b["radius"] is tokens.RADIUS
    assert b["shadows"] is tokens.SHADOWS
    assert b["fonts"] is tokens.FONTS
    assert b["logo"] is tokens.LOGO_URLS


def test_legacy_aliases_are_well_formed() -> None:
    """Legacy aliases preserve historical token names the landing pages still use.

    Each value is either:
      * a ``var(--X)`` redirection, OR
      * a raw CSS value (px, rgba, hex) when the old name was an alias for a literal.

    They are removed in the final shim-removal batch (design.md D8); until
    then the HTML codemod leans on them.
    """
    alias_value = re.compile(r"^(var\(--[a-z0-9\-]+\)|#[0-9A-Fa-f]{3,8}|\d+(?:\.\d+)?px|rgba\([^)]+\))$")
    for alias, value in tokens.LEGACY_CSS_ALIASES.items():
        assert alias_value.match(value), (
            f"legacy alias --{alias} has unsupported value {value!r} "
            "(expected var(--x) / #hex / Npx / rgba())"
        )
