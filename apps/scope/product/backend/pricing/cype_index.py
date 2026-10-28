"""CYPE index query API — FTS5 lookup over the bundled CYPE DB.

Shipped as ``apps/scope/product/backend/pricing/data/cype_prices.db`` (9 MB,
2,151 rows — moved here in Phase 5 Wave 4). The scraper that built the
index was removed April 2026; the build path was archived in Phase 6
W18 to ``internal/refactor/archive/scripts-phase4-5/build_cype_index.py``.
Only the query path lives here.

Public API:

- :func:`search_cype(query, ...)` — BM25-ranked FTS5 search with
  OR-joined partial matches, prefix matching, and optional filters.

Uses ``fulltext.tokenize`` for Spanish normalisation (single source of
truth; eliminates the two duplicate tokenizers that used to live in
``price_engine.py`` and ``cype_index.py``).
"""

from __future__ import annotations

import json
import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from . import config
from .errors import IndexNotFoundError, QueryEmptyError
from .stopwords import CYPE_FILLERS
from .types import CypeItem

logger = logging.getLogger(__name__)

__all__ = [
    "search_cype",
    "close_connection",
]


_conn: Optional[sqlite3.Connection] = None
_conn_path: Optional[Path] = None


def _get_conn() -> sqlite3.Connection:
    """Open (or reuse) the process-lifetime CYPE connection.

    Connection is read-only in practice; ``check_same_thread=False``
    matches the existing ``product_lookup.py`` pattern. Re-opened if
    :func:`pricing.configure` is called with a new ``cype_db`` path.
    """

    global _conn, _conn_path

    path = config.cype_db_path()
    if path is None or not path.exists():
        raise IndexNotFoundError(
            f"CYPE index not found at {path!r}; "
            "bundled DB missing or LEO_PRICING_CYPE_DB env var points nowhere."
        )

    if _conn is not None and _conn_path == path:
        return _conn

    if _conn is not None:
        try:
            _conn.close()
        except sqlite3.Error:
            pass

    _conn = sqlite3.connect(str(path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn_path = path
    logger.info("CYPE index opened: %s", path)
    return _conn


def close_connection() -> None:
    """Close the CYPE connection. Safe to call when no connection is open."""

    global _conn, _conn_path
    if _conn is not None:
        try:
            _conn.close()
        except sqlite3.Error:
            pass
        _conn = None
        _conn_path = None


def _normalize_query(query: str) -> str:
    """Normalize query to match the CYPE FTS5 index content.

    The bundled ``cype_prices.db`` stores **accent-stripped,
    lowercased, stopword-filtered** tokens *without* stemming (the
    scraper snapshot predates the Spanish-stemmer rollout). We mirror
    that normalisation here so FTS5 MATCH hits the stored form.

    When :mod:`fulltext` is unavailable we fall back to a plain
    accent+lowercase+stopword filter — same post-condition.
    """

    from core.text import strip_accents

    try:
        from fulltext import SPANISH_GENERAL

        stop = SPANISH_GENERAL | CYPE_FILLERS
    except ImportError:
        stop = CYPE_FILLERS

    tokens = [
        t for t in strip_accents(query).lower().split()
        if len(t) > 2 and t not in stop
    ]
    return " ".join(tokens)


def _build_fts_query(query_norm: str, original: str) -> str:
    """Build an FTS5 MATCH expression.

    Multi-token queries become OR-joined phrase queries (each token in
    its own quoted phrase). Single-token queries are quoted verbatim.
    Empty normalisations fall back to the lowercase original.
    """

    fts_tokens = query_norm.split()
    if len(fts_tokens) > 1:
        return " OR ".join(f'"{t}"' for t in fts_tokens)
    if fts_tokens:
        return f'"{fts_tokens[0]}"'
    return original.lower()


def search_cype(
    query: str,
    *,
    unit_filter: Optional[str] = None,
    chapter_filter: Optional[str] = None,
    max_price: Optional[float] = None,
    min_price: Optional[float] = None,
    limit: int = 10,
) -> List[CypeItem]:
    """Search the CYPE FTS5 index, returning typed :class:`CypeItem` list.

    See ``design.md`` §D17 for caching guidance — ``timed_cache`` is
    applied at the ``estimate_cost`` orchestrator level (key includes
    all modifier/unit/quantity fields) so direct ``search_cype`` callers
    remain cache-free.

    Raises:
        :class:`QueryEmptyError` — empty ``query``.
        :class:`IndexNotFoundError` — CYPE DB is missing from disk.
    """

    if not query or not query.strip():
        raise QueryEmptyError("search_cype called with empty query")

    conn = _get_conn()

    query_norm = _normalize_query(query)
    if not query_norm:
        query_norm = query.lower()

    fts_query = _build_fts_query(query_norm, query)

    where_parts: List[str] = []
    params: List[object] = [fts_query]

    if unit_filter:
        where_parts.append("i.unit = ?")
        params.append(unit_filter)
    if chapter_filter:
        where_parts.append("i.chapter LIKE ?")
        params.append(f"%{chapter_filter}%")
    if max_price is not None:
        where_parts.append("i.total_price <= ?")
        params.append(max_price)
    if min_price is not None:
        where_parts.append("i.total_price >= ?")
        params.append(min_price)

    where_clause = ""
    if where_parts:
        where_clause = "AND " + " AND ".join(where_parts)

    sql = f"""
        SELECT
            i.id, i.code, i.title, i.description, i.unit, i.total_price,
            i.chapter, i.typology, i.url, i.materials_json, i.labour_json,
            rank AS bm25_score
        FROM cype_fts
        JOIN cype_items i ON cype_fts.item_id = i.id
        WHERE cype_fts MATCH ?
        {where_clause}
        ORDER BY rank
        LIMIT ?
    """
    params.append(limit)

    try:
        rows = conn.execute(sql, params).fetchall()
    except sqlite3.OperationalError as exc:
        logger.warning(
            "FTS5 query error for %r: %s — falling back to LIKE", query, exc,
        )
        rows = _fallback_search(
            conn, query,
            unit_filter=unit_filter,
            chapter_filter=chapter_filter,
            min_price=min_price,
            max_price=max_price,
            limit=limit,
        )

    return [_row_to_item(row) for row in rows]


def _fallback_search(
    conn: sqlite3.Connection,
    query: str,
    *,
    unit_filter: Optional[str],
    chapter_filter: Optional[str],
    min_price: Optional[float],
    max_price: Optional[float],
    limit: int,
) -> list[sqlite3.Row]:
    """LIKE-based fallback when the FTS5 expression can't parse.

    Rare — FTS5 parse errors happen when callers pass punctuation that
    the tokenizer doesn't strip. Preserves graceful degradation.
    """

    where_parts: List[str] = ["(title LIKE ? OR description LIKE ?)"]
    params: List[object] = [f"%{query}%", f"%{query}%"]

    if unit_filter:
        where_parts.append("unit = ?")
        params.append(unit_filter)
    if chapter_filter:
        where_parts.append("chapter LIKE ?")
        params.append(f"%{chapter_filter}%")
    if max_price is not None:
        where_parts.append("total_price <= ?")
        params.append(max_price)
    if min_price is not None:
        where_parts.append("total_price >= ?")
        params.append(min_price)

    sql = f"""
        SELECT
            id, code, title, description, unit, total_price, chapter,
            typology, url, materials_json, labour_json,
            0 AS bm25_score
        FROM cype_items
        WHERE {' AND '.join(where_parts)}
        LIMIT ?
    """
    params.append(limit)
    return conn.execute(sql, params).fetchall()


def _row_to_item(row: sqlite3.Row) -> CypeItem:
    return CypeItem(
        id=row["id"],
        code=row["code"] or "",
        title=row["title"] or "",
        description=(row["description"] or "")[:300],
        unit=row["unit"] or "",
        total_price=row["total_price"],
        chapter=row["chapter"] or "",
        typology=(row["typology"] or "unknown"),  # type: ignore[arg-type]
        url=row["url"] or "",
        materials=_parse_json(row["materials_json"]),
        labour=_parse_json(row["labour_json"]),
        bm25_score=float(row["bm25_score"] or 0),
    )


def _parse_json(raw: Optional[str]) -> list:
    if not raw:
        return []
    try:
        data = json.loads(raw)
        return data if isinstance(data, list) else []
    except (TypeError, ValueError):
        return []
