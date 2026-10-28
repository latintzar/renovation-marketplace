"""Spanish construction-product catalog lookup.

Searches ``products.db`` (Leroy Merlin + manufacturer) via FTS5. The DB
is ~78 MB and EXTERNAL (not bundled per ``design.md`` §D3 — too big for
a wheel). Callers must configure the path via ``pricing.configure(products_db=...)``
or the ``LEO_PRICING_PRODUCTS_DB`` env var.

Public API:

- :func:`lookup_product(query, category="", max_results=8)` — returns a
  :class:`ProductList` (wraps formatted LLM text plus structured items).
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import List, Optional

from core.text import strip_accents

from . import config
from .errors import IndexNotFoundError, QueryEmptyError
from .types import Product, ProductList

logger = logging.getLogger(__name__)

__all__ = [
    "lookup_product",
    "close_connection",
]


_conn: Optional[sqlite3.Connection] = None
_conn_path: Optional[Path] = None


def _get_conn() -> sqlite3.Connection:
    global _conn, _conn_path

    path = config.products_db_path()
    if path is None or not path.exists():
        raise IndexNotFoundError(
            f"Product index not found at {path!r}; "
            "pass pricing.configure(products_db=...) or set LEO_PRICING_PRODUCTS_DB. "
            "78 MB DB is external (not bundled in wheel)."
        )

    if _conn is not None and _conn_path == path:
        return _conn

    close_connection()

    _conn = sqlite3.connect(str(path), check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn_path = path
    logger.info("Product index opened: %s", path)
    return _conn


def close_connection() -> None:
    global _conn, _conn_path
    if _conn is not None:
        try:
            _conn.close()
        except sqlite3.Error:
            pass
        _conn = None
        _conn_path = None


def _build_fts_query(words: List[str]) -> str:
    stripped_words = [strip_accents(w) for w in words]
    return " OR ".join(set(words + stripped_words))


def _row_to_product(row: sqlite3.Row) -> Product:
    price = row["price"]
    price_f: Optional[float]
    try:
        price_f = float(price) if price is not None else None
    except (TypeError, ValueError):
        price_f = None

    return Product(
        name=row["name"] or "",
        brand=row["brand"] or "",
        category=row["category_main"] or "",
        sku=row["sku"] or "",
        url=row["url"] or "",
        price_eur=price_f,
        currency="EUR",
        source=row["source"] or "",
    )


def _format_products(products: List[Product], query: str) -> str:
    source_label = {"leroy_merlin": "Leroy Merlin", "manufacturer": "manufacturer"}

    lines = [f"Construction products matching '{query}':"]
    for p in products:
        headline = f"{p.brand} — {p.name}" if p.brand else p.name
        line = f"- {headline}"

        if p.price_eur is not None:
            symbol = "€" if p.currency == "EUR" else p.currency
            line += f" | {symbol}{p.price_eur:.2f}"
        else:
            line += " | price not indexed"

        if p.sku:
            src = source_label.get(p.source, p.source)
            line += f" | SKU {p.sku} ({src})"

        if p.category:
            line += f" | [{p.category}]"

        lines.append(line)

    lines.append(
        f"\n({len(products)} results from "
        f"{len(set(p.source for p in products if p.source))} source(s). "
        "Prices at Leroy Merlin are not indexed yet — "
        "use lookup_price for labour cost ranges.)"
    )
    return "\n".join(lines)


def lookup_product(
    query: str,
    *,
    category: str = "",
    max_results: int = 8,
) -> ProductList:
    """Search the Spanish construction product catalog.

    Raises:
        :class:`QueryEmptyError` — empty ``query`` or insufficiently-
            specific (no tokens longer than 2 chars).
        :class:`IndexNotFoundError` — products DB not configured.
    """

    if not query or not query.strip():
        raise QueryEmptyError("lookup_product called with empty query")

    conn = _get_conn()
    cur = conn.cursor()

    words = [w for w in query.split() if len(w.strip()) > 2]
    if not words:
        raise QueryEmptyError(
            f"Query too short (tokens must be >2 chars): '{query}'"
        )

    fts_query = _build_fts_query(words)

    try:
        rowids = cur.execute(
            "SELECT rowid FROM products_fts WHERE products_fts MATCH ? "
            "ORDER BY rank LIMIT ?",
            (fts_query, max_results * 2),
        ).fetchall()
    except sqlite3.OperationalError as exc:
        logger.error("FTS5 query error: %s | query: %s", exc, fts_query)
        return ProductList(
            query=query,
            category=category,
            items=[],
            sources_used=[],
            text=f"Search error for '{query}': {exc}",
        )

    if not rowids:
        return ProductList(
            query=query,
            category=category,
            items=[],
            sources_used=[],
            text=f"No products found matching '{query}' "
                 "in the Spanish construction catalog.",
        )

    products: List[Product] = []
    for (rid,) in rowids:
        row = cur.execute(
            "SELECT name, brand, category_main, price, currency, sku, "
            "source, url FROM products WHERE rowid=?",
            (rid,),
        ).fetchone()
        if row:
            products.append(_row_to_product(row))

    if category:
        cat_norm = strip_accents(category.lower())
        filtered = [
            p for p in products
            if cat_norm in strip_accents(p.category.lower())
        ]
        if filtered:
            products = filtered

    products = products[:max_results]

    if not products:
        return ProductList(
            query=query,
            category=category,
            items=[],
            sources_used=[],
            text=f"No products found matching '{query}'.",
        )

    text = _format_products(products, query)
    sources_used = sorted({p.source for p in products if p.source})

    return ProductList(
        query=query,
        category=category,
        items=products,
        sources_used=sources_used,
        text=text,
    )
