"""Vellum — the canonical Leo translucency style.

A light cream film (rgba(250,248,244,.12)) with a 7px backdrop blur,
a subtle top-edge highlight, and a small drop shadow. Reads as
"paper over paper" rather than "glass over colour."

Source of truth for the ``.brand-glass--vellum`` CSS class — the
class in ``effects.css`` is a mirror of :data:`VELLUM.to_css(...)`.

Extending the catalog: drop a new recipe next to this file, register
it in :mod:`brand.translucency.__init__`, and emit the matching CSS
class in ``effects.css``. See ``DESIGN.md`` for the rules.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TranslucencyStyle:
    """Immutable bundle of the six translucency knobs.

    A theme references this by *name* (e.g. ``TRANSLUCENCY = "vellum"``)
    — the recipe stays encapsulated so tuning the knobs later doesn't
    require touching themes.
    """

    name: str
    backdrop_blur: str
    backdrop_saturate: float
    background: str
    border: str
    inset_highlight: str
    drop_shadow: str

    def to_css(self, selector: str) -> str:
        """Emit the full CSS block for *selector*.

        Example::

            VELLUM.to_css(".brand-glass--vellum")

        Produces a ``backdrop-filter`` (both prefixed and unprefixed),
        background, border, and combined box-shadow (drop shadow +
        inset highlight).
        """
        blur = self.backdrop_blur
        if self.backdrop_saturate != 1.0:
            blur = f"{blur} saturate({self.backdrop_saturate})"
        return (
            f"{selector} {{\n"
            f"  -webkit-backdrop-filter: {blur};\n"
            f"  backdrop-filter: {blur};\n"
            f"  background: {self.background};\n"
            f"  border: {self.border};\n"
            f"  box-shadow: {self.drop_shadow}, {self.inset_highlight};\n"
            f"}}"
        )


VELLUM: TranslucencyStyle = TranslucencyStyle(
    name="vellum",
    backdrop_blur="blur(7px)",
    backdrop_saturate=1.0,
    background="rgba(250, 248, 244, 0.12)",
    border="1px solid rgba(255, 255, 255, 0.35)",
    inset_highlight="inset 0 1px 0 rgba(255, 255, 255, 0.45)",
    drop_shadow="0 2px 8px rgba(0, 0, 0, 0.05)",
)


__all__ = ["TranslucencyStyle", "VELLUM"]
