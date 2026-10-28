"""Canonical tokenizer for FTS5 indexing and query expansion (D4).

``tokenize(text, *, stopwords=None, min_len=2)`` is **the** reference
implementation — both ``DomainIndex.add`` and ``expand_query`` MUST
flow through it. Steps, deterministic:

1. Lowercase (unicode-aware).
2. Accent-strip via :func:`core.text.strip_accents` (single source
   of truth — we do **not** reimplement NFKD normalisation).
3. Split on whitespace (caller may pre-split; punctuation stripped
   by callers via ``re.sub`` before reaching here if needed).
4. Drop stopwords and tokens shorter than ``min_len``.
5. Stem each survivor with :func:`._stemmer.stem_word`
   (Spanish Snowball).

Why the caller supplies stopwords instead of us defaulting to the
union: grammar stopwords (``SPANISH_GENERAL``) always apply, but
domain noise (``precio``, ``cype``) varies per index. The consumer
builds ``stopwords = SPANISH_GENERAL | ENGLISH_GENERAL | DOMAIN_FILLER``
once and passes it in — zero surprise.
"""
from __future__ import annotations

from typing import Iterable

from core.text import strip_accents

from ._stemmer import stem_word
from .stopwords import ENGLISH_GENERAL, SPANISH_GENERAL

__all__ = ["tokenize", "stem_word"]

_DEFAULT_STOPWORDS: frozenset[str] = SPANISH_GENERAL | ENGLISH_GENERAL


def tokenize(
    text: str,
    *,
    stopwords: Iterable[str] | None = None,
    min_len: int = 2,
) -> list[str]:
    """Normalise + stem + filter a free-text string.

    :param text: Raw user input; may contain accents, mixed case, mixed EN/ES.
    :param stopwords: Optional custom stopword pool. Defaults to
        ``SPANISH_GENERAL | ENGLISH_GENERAL`` (grammar-only).
    :param min_len: Tokens strictly shorter than this are dropped
        (matches SQLite FTS5's default behaviour for unigrams).
    :returns: Ordered list of stemmed tokens, duplicates preserved.
    """

    if stopwords is None:
        stop: frozenset[str] | set[str] = _DEFAULT_STOPWORDS
    elif isinstance(stopwords, (frozenset, set)):
        stop = stopwords
    else:
        stop = frozenset(stopwords)

    normalised = strip_accents(text.lower())
    words = normalised.split()
    out: list[str] = []
    for w in words:
        if len(w) < min_len:
            continue
        if w in stop:
            continue
        out.append(stem_word(w))
    return out
