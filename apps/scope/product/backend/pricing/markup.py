"""Market markup tables — CYPE cost-of-inputs → retail quote.

Per ``design.md`` §D10: CYPE gives "cost of materials + labour at Convenio
rates". Real contractor quotes include overhead + profit margin; the
empirical markup is ~1.4–2.4× depending on trade.

:data:`DEFAULT_MARKUP_BY_CHAPTER` holds per-CYPE-chapter brackets
(``min``, ``mid``, ``max``). The single-value estimate uses ``mid``;
the range shown to the LLM spans ``min..max``.

:func:`markup_for_chapter(chapter)` resolves a chapter path against the
table (exact → prefix → fallback). Operators override the table via
``pricing.configure(markup_by_chapter={...})``.

Also houses :func:`material_fraction_for_chapter` — the "~50% materials,
~50% labour" split historical to the package — soon tunable per trade
(plumbing is labour-heavy, tile is materials-heavy).
"""

from __future__ import annotations

from types import MappingProxyType
from typing import Final, Mapping

from . import config
from .errors import MarkupLookupError
from .types import MarkupEntry


DEFAULT_MARKUP_BY_CHAPTER: Final[Mapping[str, MarkupEntry]] = MappingProxyType({
    "Instalaciones/Fontaneria":    MarkupEntry(min=1.4, mid=1.7, max=2.3),
    "Instalaciones/Electricidad":  MarkupEntry(min=1.4, mid=1.7, max=2.2),
    "Instalaciones/Climatizacion": MarkupEntry(min=1.5, mid=1.8, max=2.4),
    "Revestimientos/Alicatados":   MarkupEntry(min=1.3, mid=1.5, max=2.0),
    "Demolicion":                  MarkupEntry(min=1.2, mid=1.4, max=1.8),
    "Particiones/Yeso":            MarkupEntry(min=1.3, mid=1.5, max=2.0),
    "Carpinteria":                 MarkupEntry(min=1.3, mid=1.6, max=2.1),
    "Albanileria":                 MarkupEntry(min=1.3, mid=1.5, max=2.0),
    "Pinturas":                    MarkupEntry(min=1.3, mid=1.5, max=2.0),
    "Cubiertas":                   MarkupEntry(min=1.4, mid=1.7, max=2.3),
})


FALLBACK_MARKUP: Final[MarkupEntry] = MarkupEntry(min=1.3, mid=1.6, max=2.2)


MATERIAL_FRACTION_BY_CHAPTER: Final[Mapping[str, float]] = MappingProxyType({
    "Instalaciones/Fontaneria":    0.40,  # labour-heavy
    "Instalaciones/Electricidad":  0.35,  # very labour-heavy
    "Instalaciones/Climatizacion": 0.55,  # equipment-heavy
    "Revestimientos/Alicatados":   0.60,  # tile materials are big
    "Demolicion":                  0.10,  # mostly labour + disposal
    "Pinturas":                    0.35,  # skill-priced
    "Particiones/Yeso":            0.45,
    "Cubiertas":                   0.55,
})


__all__ = [
    "DEFAULT_MARKUP_BY_CHAPTER",
    "FALLBACK_MARKUP",
    "MATERIAL_FRACTION_BY_CHAPTER",
    "markup_for_chapter",
    "material_fraction_for_chapter",
]


def markup_for_chapter(chapter: str) -> MarkupEntry:
    """Return the ``MarkupEntry`` for a CYPE chapter path.

    Resolution:

    1. Exact match in the override table (``pricing.configure(markup_by_chapter=...)``).
    2. Exact match in :data:`DEFAULT_MARKUP_BY_CHAPTER`.
    3. Prefix match against both tables (override first, defaults second).
    4. :data:`FALLBACK_MARKUP`.

    Empty/None chapter → :data:`FALLBACK_MARKUP` (no :class:`MarkupLookupError` here;
    fallback is the whole point — only the named "*_strict" variants raise).
    """

    if not chapter:
        return FALLBACK_MARKUP

    override = config.markup_by_chapter_override() or {}
    table = DEFAULT_MARKUP_BY_CHAPTER

    if chapter in override:
        return _coerce_entry(override[chapter])
    if chapter in table:
        return table[chapter]

    for key, value in override.items():
        if chapter.startswith(key):
            return _coerce_entry(value)
    for key, value in table.items():
        if chapter.startswith(key):
            return value

    return FALLBACK_MARKUP


def markup_for_chapter_strict(chapter: str) -> MarkupEntry:
    """Like :func:`markup_for_chapter` but raises on miss.

    Used by paths that want an explicit lookup failure (e.g. a contractor
    dashboard that flags "unknown chapter" to the ops team). Not wired
    inside ``estimate_cost`` — there we always want graceful fallback.
    """

    entry = markup_for_chapter(chapter)
    if entry is FALLBACK_MARKUP and chapter not in DEFAULT_MARKUP_BY_CHAPTER:
        raise MarkupLookupError(
            f"No markup entry for chapter {chapter!r}; override via configure()."
        )
    return entry


def material_fraction_for_chapter(chapter: str) -> float:
    """Return the ~material fraction of cost-of-inputs for a chapter.

    Default 0.50 if the chapter is not in the curated table. Tune to get
    smarter INE drift application — electrical is 0.35 (wages dominate),
    tile is 0.60 (boxed materials are a bigger share).
    """

    if not chapter:
        return 0.50

    if chapter in MATERIAL_FRACTION_BY_CHAPTER:
        return MATERIAL_FRACTION_BY_CHAPTER[chapter]

    for key, value in MATERIAL_FRACTION_BY_CHAPTER.items():
        if chapter.startswith(key):
            return value

    return 0.50


def _coerce_entry(value: object) -> MarkupEntry:
    """Accept ``(min, mid, max)`` tuples from user-provided overrides.

    Keeps ``configure(markup_by_chapter={"Demolicion": (1.1, 1.3, 1.7)})``
    ergonomic without forcing callers to import ``MarkupEntry``.
    """

    if isinstance(value, MarkupEntry):
        return value
    if isinstance(value, (tuple, list)) and len(value) == 3:
        lo, mid, hi = value
        return MarkupEntry(min=float(lo), mid=float(mid), max=float(hi))
    if isinstance(value, dict) and {"min", "mid", "max"} <= set(value):
        return MarkupEntry(
            min=float(value["min"]),
            mid=float(value["mid"]),
            max=float(value["max"]),
        )
    raise MarkupLookupError(
        f"Cannot coerce {value!r} to MarkupEntry; "
        "expected MarkupEntry, tuple(min, mid, max), or dict."
    )
