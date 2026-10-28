"""Private Spanish Snowball stemmer singleton.

Using PyStemmer once per process — thread-safe for readers,
`stemWord(w)` returns a fresh string. The public API is
:func:`fulltext.tokenizer.stem_word`; this module exists so both the
tokenizer and (historically) the CYPE index can share one instance
without duplicating the PyStemmer import cost.

Rationale (D10): PyStemmer is a **required** dependency, not optional.
An identity fallback survives as a defence-in-depth — if PyStemmer
somehow fails to import, recall degrades gracefully rather than
raising. The import guard logs at ``ERROR`` so CI catches it.
"""
from __future__ import annotations

import logging
from typing import Callable

logger = logging.getLogger(__name__)

__all__ = ["stem_word"]

_stem_word: Callable[[str], str]

try:
    import Stemmer as _PyStemmer  # type: ignore[import-untyped]

    _stemmer = _PyStemmer.Stemmer("spanish")

    def _stem_word_impl(w: str) -> str:
        return _stemmer.stemWord(w)

    _stem_word = _stem_word_impl
except ImportError:  # pragma: no cover
    logger.error("PyStemmer unavailable — recall will degrade silently.")

    def _identity(w: str) -> str:
        return w

    _stem_word = _identity


def stem_word(w: str) -> str:
    """Return the Spanish Snowball stem of a single word."""

    return _stem_word(w)
