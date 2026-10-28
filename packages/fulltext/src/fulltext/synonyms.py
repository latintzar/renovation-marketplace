"""Cross-language (EN ↔ ES) synonym expansion (D6).

``EN_ES_SYNONYMS`` is canonical and read-only. A reverse index
``_ES_EN_REVERSE`` is built eagerly at import time — callers don't
pay per-query cost. Extensions live beside their consumer (e.g.
``pricing.synonyms`` layers construction-specific terms).

``expand_query`` emits an FTS5 expression in the shape
``(s_1a OR s_1b OR ...) AND (s_2a OR s_2b OR ...)``:
concepts are ANDed (every concept word must match a document),
synonyms for a concept are ORed. This mirrors human intuition:
"bathroom renovation" should match docs mentioning reforma of a
baño, not docs about any bathroom plus any renovation.

Multi-word phrases (``"air conditioning"``) are matched first and
consume their tokens so they aren't re-expanded as single words.
"""
from __future__ import annotations

from typing import Final

from core.text import strip_accents

from ._stemmer import stem_word
from .stopwords import ENGLISH_GENERAL, SPANISH_GENERAL

__all__ = ["expand_query", "EN_ES_SYNONYMS"]

_STOPWORDS: Final[frozenset[str]] = SPANISH_GENERAL | ENGLISH_GENERAL

EN_ES_SYNONYMS: Final[dict[str, tuple[str, ...]]] = {
    "plumber": ("fontanero", "fontaneria"),
    "plumbing": ("fontaneria",),
    "electrician": ("electricista", "electricidad"),
    "electrical": ("electrica", "electricidad"),
    "painter": ("pintor", "pintura"),
    "painting": ("pintar", "pintura"),
    "bathroom": ("bano",),
    "kitchen": ("cocina",),
    "bedroom": ("dormitorio", "habitacion"),
    "floor": ("suelo", "pavimento"),
    "flooring": ("suelo", "pavimento", "tarima", "parquet"),
    "tile": ("azulejo", "baldosa", "alicatar"),
    "tiling": ("alicatar", "alicatado", "azulejo"),
    "roof": ("tejado", "cubierta"),
    "roofing": ("tejado", "cubierta"),
    "window": ("ventana",),
    "door": ("puerta",),
    "renovation": ("reforma", "reformar"),
    "remodel": ("reforma", "reformar"),
    "remodeling": ("reforma", "reformar"),
    "construction": ("construccion", "obra"),
    "demolition": ("demolicion", "derribar"),
    "insulation": ("aislamiento",),
    "heating": ("calefaccion", "caldera"),
    "boiler": ("caldera",),
    "air conditioning": ("aire acondicionado",),
    "ac": ("aire acondicionado",),
    "solar": ("solar", "fotovoltaica", "placas solares"),
    "solar panels": ("placas solares",),
    "pool": ("piscina",),
    "swimming pool": ("piscina",),
    "garden": ("jardin",),
    "landscaping": ("jardineria", "paisajismo"),
    "fence": ("valla", "cercado"),
    "wall": ("pared", "muro", "tabique"),
    "partition": ("tabique",),
    "drywall": ("pladur", "tabique"),
    "plaster": ("yeso", "enlucir", "enlucido"),
    "concrete": ("hormigon",),
    "foundation": ("cimentacion",),
    "architect": ("arquitecto",),
    "carpenter": ("carpintero", "carpinteria"),
    "carpentry": ("carpinteria", "carpintero"),
    "locksmith": ("cerrajero",),
    "glass": ("cristal", "vidrio", "cristalero"),
    "garage": ("garaje",),
    "elevator": ("ascensor",),
    "lift": ("ascensor",),
    "staircase": ("escalera",),
    "basement": ("sotano",),
    "attic": ("buhardilla", "atico"),
    "terrace": ("terraza",),
    "balcony": ("balcon",),
    "pergola": ("pergola",),
    "awning": ("toldo",),
    "blinds": ("persiana",),
    "curtain": ("cortina",),
    "waterproofing": ("impermeabilizar", "impermeabilizacion"),
    "drainage": ("desague", "drenaje"),
    "sewer": ("alcantarillado", "saneamiento"),
    "water": ("agua",),
    "gas": ("gas",),
    "permit": ("licencia", "permiso"),
    "moving": ("mudanza",),
    "cleaning": ("limpieza",),
    "pest control": ("fumigacion", "control plagas"),
    "alarm": ("alarma",),
    "security": ("seguridad",),
    "furniture": ("mueble", "muebles"),
    "kitchen furniture": ("muebles cocina",),
    "wardrobe": ("armario",),
    "closet": ("armario",),
    "countertop": ("encimera",),
    "sink": ("fregadero", "lavabo"),
    "toilet": ("inodoro", "water", "wc"),
    "shower": ("ducha",),
    "bathtub": ("banera",),
    "tap": ("grifo",),
    "faucet": ("grifo",),
    "pipe": ("tuberia",),
    "cable": ("cable", "cableado"),
    "wiring": ("cableado", "instalacion electrica"),
    "socket": ("enchufe",),
    "switch": ("interruptor",),
    "light": ("iluminacion", "lampara"),
    "cost": ("coste", "costo"),
    "price": ("precio",),
    "budget": ("presupuesto",),
    "cheap": ("barato", "economico"),
    "expensive": ("caro",),
    "install": ("instalar", "instalacion"),
    "repair": ("reparar", "reparacion"),
    "replace": ("sustituir", "cambiar"),
    "replacement": ("cambiar", "sustituir", "cambio"),
    "build": ("construir",),
    "remove": ("quitar", "retirar", "eliminar"),
    "house": ("casa", "vivienda"),
    "flat": ("piso",),
    "apartment": ("piso", "apartamento"),
}

_ES_EN_REVERSE: Final[dict[str, tuple[str, ...]]] = {}
_reverse_build: dict[str, list[str]] = {}
for _en, _es_list in EN_ES_SYNONYMS.items():
    for _es in _es_list:
        _reverse_build.setdefault(strip_accents(_es.lower()), []).append(_en)
for _k, _v in _reverse_build.items():
    _ES_EN_REVERSE[_k] = tuple(_v)
del _reverse_build


def _make_or_group(stems: list[str]) -> str:
    """Build an FTS5 OR group: single token or ``(a OR b OR c)``."""

    unique = list(dict.fromkeys(stems))
    if len(unique) == 1:
        return unique[0]
    return "(" + " OR ".join(unique) + ")"


def expand_query(raw_query: str) -> str:
    """Expand a raw user query into an FTS5 MATCH expression.

    Returns a string suitable for ``docs_fts MATCH ?``. Multi-word
    synonym keys (e.g. ``"air conditioning"``) are detected and
    consumed before single-word expansion runs.

    Fallback: if no concept words survive filtering, the raw query's
    stemmed non-stopword tokens are ORed. As a last resort the raw
    query is returned verbatim — FTS5 will either match or produce
    an empty result set (never a 500).
    """

    normalised = strip_accents(raw_query.lower())
    words = normalised.split()
    if not words:
        return raw_query

    or_groups: list[str] = []
    consumed: set[int] = set()

    for phrase, translations in EN_ES_SYNONYMS.items():
        phrase_norm = strip_accents(phrase.lower())
        phrase_words = phrase_norm.split()
        if len(phrase_words) < 2:
            continue
        for i in range(len(words) - len(phrase_words) + 1):
            if any(i + j in consumed for j in range(len(phrase_words))):
                continue
            if words[i : i + len(phrase_words)] != phrase_words:
                continue
            for j in range(len(phrase_words)):
                consumed.add(i + j)
            all_forms = [phrase_norm, *(strip_accents(t) for t in translations)]
            stems = list(
                dict.fromkeys(
                    stem_word(w)
                    for form in all_forms
                    for w in form.split()
                    if w not in _STOPWORDS and len(w) > 1
                )
            )
            if stems:
                or_groups.append(_make_or_group(stems))

    for i, w in enumerate(words):
        if i in consumed:
            continue
        if w in _STOPWORDS or len(w) <= 1:
            continue

        all_forms: list[str] = [w]
        for syn in EN_ES_SYNONYMS.get(w, ()):
            all_forms.append(strip_accents(syn))
        for en_word in _ES_EN_REVERSE.get(w, ()):
            all_forms.append(strip_accents(en_word))
            for syn in EN_ES_SYNONYMS.get(en_word, ()):
                all_forms.append(strip_accents(syn))

        stems = list(
            dict.fromkeys(
                stem_word(f)
                for f in all_forms
                if f not in _STOPWORDS and len(f) > 1
            )
        )
        if stems:
            or_groups.append(_make_or_group(stems))

    if not or_groups:
        fallback = [
            stem_word(w) for w in words if w not in _STOPWORDS and len(w) > 1
        ]
        return " OR ".join(fallback) if fallback else raw_query

    return " AND ".join(or_groups)
