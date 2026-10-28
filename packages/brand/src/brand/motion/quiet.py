"""Quiet — the default Leo motion style.

A full motion recipe: durations, eases, springs, entrances, staggers,
and scroll physics. Themes reference by name (``MOTION = "quiet"``)
so tuning the feel later doesn't require touching themes.

Emitted as CSS variables via :meth:`MotionStyle.to_css` and as
framer-motion-compatible dicts via :meth:`MotionStyle.to_ts`.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict


@dataclass(frozen=True)
class Durations:
    """Millisecond durations for transitions."""

    instant: int = 80
    fast: int = 120
    medium: int = 240
    slow: int = 400
    languid: int = 640


@dataclass(frozen=True)
class Eases:
    """Named cubic-bezier / timing function strings."""

    out_quart: str = "cubic-bezier(0.165, 0.84, 0.44, 1)"
    in_out_cubic: str = "cubic-bezier(0.645, 0.045, 0.355, 1)"
    spring_subtle: str = "cubic-bezier(0.34, 1.56, 0.64, 1)"
    linear: str = "linear"


@dataclass(frozen=True)
class Springs:
    """framer-motion spring presets — dicts suitable for the ``transition`` prop."""

    subtle: Dict[str, Any] = field(
        default_factory=lambda: {"type": "spring", "stiffness": 260, "damping": 30}
    )
    default: Dict[str, Any] = field(
        default_factory=lambda: {"type": "spring", "stiffness": 180, "damping": 22}
    )
    bouncy: Dict[str, Any] = field(
        default_factory=lambda: {"type": "spring", "stiffness": 120, "damping": 10}
    )
    snappy: Dict[str, Any] = field(
        default_factory=lambda: {"type": "spring", "stiffness": 400, "damping": 40}
    )


@dataclass(frozen=True)
class Entrances:
    """Named ``initial`` / ``animate`` pairs, framer-motion shape."""

    fade: Dict[str, Any] = field(
        default_factory=lambda: {
            "initial": {"opacity": 0},
            "animate": {"opacity": 1},
        }
    )
    slide_up: Dict[str, Any] = field(
        default_factory=lambda: {
            "initial": {"opacity": 0, "y": 8},
            "animate": {"opacity": 1, "y": 0},
        }
    )
    slide_right: Dict[str, Any] = field(
        default_factory=lambda: {
            "initial": {"opacity": 0, "x": -8},
            "animate": {"opacity": 1, "x": 0},
        }
    )
    blur_in: Dict[str, Any] = field(
        default_factory=lambda: {
            "initial": {"opacity": 0, "filter": "blur(2px)"},
            "animate": {"opacity": 1, "filter": "blur(0px)"},
        }
    )
    scale_in: Dict[str, Any] = field(
        default_factory=lambda: {
            "initial": {"opacity": 0, "scale": 0.98},
            "animate": {"opacity": 1, "scale": 1},
        }
    )


@dataclass(frozen=True)
class Staggers:
    """Millisecond inter-child delay for staggered reveals."""

    tight: int = 40
    default: int = 80
    generous: int = 160


@dataclass(frozen=True)
class Scroll:
    """Scroll-linked motion physics.

    ``parallax_*`` are multipliers applied to the scroll delta — smaller
    = slower. ``reveal_threshold`` is the fraction of the element that
    must be visible before an entrance fires.
    """

    parallax_slow: float = 0.3
    parallax_default: float = 0.5
    parallax_fast: float = 0.8
    reveal_threshold: float = 0.15


@dataclass(frozen=True)
class MotionStyle:
    """Immutable bundle of a full motion recipe."""

    name: str
    durations: Durations
    eases: Eases
    springs: Springs
    entrances: Entrances
    staggers: Staggers
    scroll: Scroll

    def to_css(self) -> str:
        """Emit CSS variables under ``:root``.

        Consumers: Tailwind, raw CSS, any component that reads
        ``var(--motion-fast)`` / ``var(--ease-out-quart)``.
        """
        lines: list[str] = [":root {"]
        for fld in ("instant", "fast", "medium", "slow", "languid"):
            lines.append(f"  --motion-{fld}: {getattr(self.durations, fld)}ms;")
        lines.append(f"  --ease-out-quart: {self.eases.out_quart};")
        lines.append(f"  --ease-in-out-cubic: {self.eases.in_out_cubic};")
        lines.append(f"  --ease-spring-subtle: {self.eases.spring_subtle};")
        lines.append(f"  --ease-linear: {self.eases.linear};")
        for fld in ("tight", "default", "generous"):
            lines.append(f"  --stagger-{fld}: {getattr(self.staggers, fld)}ms;")
        lines.append(f"  --parallax-slow: {self.scroll.parallax_slow};")
        lines.append(f"  --parallax-default: {self.scroll.parallax_default};")
        lines.append(f"  --parallax-fast: {self.scroll.parallax_fast};")
        lines.append(f"  --reveal-threshold: {self.scroll.reveal_threshold};")
        lines.append("}")
        lines.append("")
        lines.append("/* Respect prefers-reduced-motion — collapse all durations. */")
        lines.append("@media (prefers-reduced-motion: reduce) {")
        lines.append("  :root {")
        lines.append("    --motion-instant: 0ms;")
        lines.append("    --motion-fast: 0ms;")
        lines.append("    --motion-medium: 0ms;")
        lines.append("    --motion-slow: 0ms;")
        lines.append("    --motion-languid: 0ms;")
        lines.append("  }")
        lines.append("}")
        return "\n".join(lines)

    def to_ts(self) -> str:
        """Emit a TypeScript export object — framer-motion-consumable.

        Returns the full module body including ``export const MOTION_<NAME>``.
        """
        payload = {
            "name": self.name,
            "durations": asdict(self.durations),
            "eases": asdict(self.eases),
            "springs": asdict(self.springs),
            "entrances": asdict(self.entrances),
            "staggers": asdict(self.staggers),
            "scroll": asdict(self.scroll),
        }
        serialized = json.dumps(payload, indent=2)
        const_name = f"MOTION_{self.name.upper()}"
        return (
            f"/* Auto-generated from brand.motion.{self.name} — do not edit. */\n"
            f"export const {const_name} = {serialized} as const;\n"
            f"export type MotionStyle = typeof {const_name};\n"
        )


QUIET: MotionStyle = MotionStyle(
    name="quiet",
    durations=Durations(),
    eases=Eases(),
    springs=Springs(),
    entrances=Entrances(),
    staggers=Staggers(),
    scroll=Scroll(),
)


__all__ = [
    "Durations",
    "Eases",
    "Springs",
    "Entrances",
    "Staggers",
    "Scroll",
    "MotionStyle",
    "QUIET",
]
