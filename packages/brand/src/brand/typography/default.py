"""Default — the canonical Leo typography recipe.

Re-exports the fonts declared in :data:`brand.tokens.FONTS` into a
theme-consumable shape. Themes inherit by declaring
``TYPOGRAPHY = "default"``; overrides ship as new sibling files and
register in :mod:`brand.typography.__init__`.
"""

from __future__ import annotations

from dataclasses import dataclass

from brand.tokens import FONTS, FONTS_URL


@dataclass(frozen=True)
class TypographyStyle:
    """Immutable bundle of font-family strings + the stylesheet URL.

    Fields match the shape of :data:`brand.tokens.FONTS` so ``to_css``
    can round-trip into the generated CSS variables.
    """

    name: str
    display: str
    heading: str
    body: str
    serif: str
    sans: str
    url: str

    def to_css(self) -> str:
        """Emit CSS custom properties for the font families."""
        return (
            ":root {\n"
            f"  --font-display: {self.display};\n"
            f"  --font-heading: {self.heading};\n"
            f"  --font-body: {self.body};\n"
            f"  --font-serif: {self.serif};\n"
            f"  --font-sans: {self.sans};\n"
            "}"
        )


DEFAULT: TypographyStyle = TypographyStyle(
    name="default",
    display=FONTS["display"],
    heading=FONTS["heading"],
    body=FONTS["body"],
    serif=FONTS["serif"],
    sans=FONTS["sans"],
    url=FONTS_URL,
)


__all__ = ["TypographyStyle", "DEFAULT"]
