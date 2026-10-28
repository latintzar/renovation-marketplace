"""Blended Habitissimo + CronoShare market-price lookup.

Searches the bundled ``prices.db`` via :class:`fulltext.DomainIndex`
(FTS5 + BM25), with a dedicated ``city_prices`` lookup table for
city-specific queries.

Public API:

- :func:`lookup_market(query, city="", max_results=5)` — returns a
  :class:`MarketReport` (wraps the formatted LLM text plus structured
  fields). Replaces the legacy ``search_prices`` that returned a raw
  string.

Data sources (indexed into the same DomainIndex):

- ~1,300 Habitissimo categories (``habitissimo_prices.json``).
- ~800 CronoShare categories (``cronoshare_prices.json``).
- 816 city_prices rows covering 19 Spanish cities.

Gracefully handles missing ``prices.db`` — returns an :class:`IndexNotFoundError`
rather than crashing the caller.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional, Set, Tuple

from core.text import strip_accents

from . import config
from .errors import IndexNotFoundError, QueryEmptyError
from .types import MarketReport

logger = logging.getLogger(__name__)

__all__ = [
    "lookup_market",
    "close_connection",
]


_index = None  # type: ignore[var-annotated]
_index_path = None


_SOURCE_LABELS = {
    "habitissimo": "Habitissimo",
    "cronoshare": "CronoShare",
}


def _get_index():
    """Lazily open the prices DB as a :class:`fulltext.DomainIndex`.

    Raises :class:`IndexNotFoundError` if the DB isn't configured or
    doesn't exist on disk.
    """

    global _index, _index_path

    path = config.prices_db_path()
    if path is None or not path.exists():
        raise IndexNotFoundError(
            f"Prices DB not found at {path!r}; "
            "pass pricing.configure(prices_db=...) or set LEO_PRICING_PRICES_DB."
        )

    if _index is not None and _index_path == path:
        return _index

    close_connection()

    from fulltext import DomainIndex

    _index = DomainIndex("prices", db_path=str(path))
    _index_path = path
    logger.info("Prices DB opened: %s", path)
    return _index


def close_connection() -> None:
    """Drop the cached DomainIndex. Safe to call when no index is open."""

    global _index, _index_path
    _index = None
    _index_path = None


def _format_city_row(row: dict) -> str:
    """Format a ``city_prices`` row as LLM text."""

    source = _SOURCE_LABELS.get(row.get("source", ""), row.get("source", ""))
    title = row.get("title", row.get("slug", "Unknown"))
    city = row.get("city", "")
    prices = row.get("prices", [])

    line = f"**{title}** ({source})"
    if prices:
        line += f"\n  Prices in {city}: " + ", ".join(f"€{p}" for p in prices[:6])
    return line


def _format_fts_result(result, city_norm: str) -> str:
    meta = result.meta
    source = _SOURCE_LABELS.get(meta.get("source", ""), meta.get("source", ""))
    title = meta.get("title", meta.get("slug", "Unknown"))
    updated = meta.get("updated", "")
    url = meta.get("url", "")

    header = f"**{title}** ({source}"
    if updated:
        header += f", updated {updated}"
    header += ")"

    parts: List[str] = [header]
    if url:
        parts.append(url)

    price_range = meta.get("price_range") or {}
    if price_range:
        unit = price_range.get("unit", "")
        parts.append(
            f"Range: €{price_range.get('min', '?')} – €{price_range.get('max', '?')}"
            + (f" / {unit}" if unit and unit != "total" else "")
        )

    for table in meta.get("price_tables", [])[:2]:
        rows = table.get("rows", [])
        for row in rows[:8]:
            if len(row) >= 2:
                line = f"- {row[0]}: {row[1]}"
                if len(row) > 2 and row[2]:
                    line += f" ({row[2]})"
                parts.append(line)

    if city_norm:
        for cp in meta.get("city_prices", []):
            cp_city = strip_accents(cp.get("city", "").lower())
            if city_norm in cp_city or cp_city in city_norm:
                cp_prices = cp.get("prices_mentioned", [])
                if cp_prices:
                    parts.append(
                        f"Prices in {cp.get('city', '')}: "
                        + ", ".join(f"€{p}" for p in cp_prices[:5])
                    )

    facts = meta.get("facts") or {}
    fact_parts: List[str] = []
    if facts.get("total_requests"):
        fact_parts.append(f"{facts['total_requests']} requests")
    if facts.get("total_professionals"):
        fact_parts.append(f"{facts['total_professionals']} professionals")
    if facts.get("total_quotes"):
        fact_parts.append(f"{facts['total_quotes']} quotes")
    if fact_parts:
        parts.append(f"({', '.join(fact_parts)} on {source})")

    return "\n".join(parts)


def _dedupe_city_rows(city_rows: List[dict], limit: int) -> List[dict]:
    """Drop rows that share a price fingerprint (Habitissimo's recycled content)."""

    seen: Set[str] = set()
    deduped: List[dict] = []
    for row in city_rows:
        key = ",".join(sorted(str(p) for p in row.get("prices", [])))
        if key not in seen:
            seen.add(key)
            deduped.append(row)
        if len(deduped) >= limit:
            break
    return deduped


def _extract_structured(
    city_rows: List[dict],
    fts_results: list,
    city: str,
) -> Tuple[Optional[Tuple[float, float]], List[float], List[Dict]]:
    """Pull structured fields out of the same rows the text formatter uses."""

    city_prices: List[float] = []
    items: List[Dict] = []
    national_range: Optional[Tuple[float, float]] = None

    for row in city_rows:
        items.append(dict(row))
        for price in row.get("prices", []):
            try:
                city_prices.append(float(price))
            except (TypeError, ValueError):
                continue

    for fts in fts_results:
        meta = fts.meta
        items.append(dict(meta))
        pr = meta.get("price_range") or {}
        if pr and national_range is None:
            try:
                national_range = (float(pr.get("min")), float(pr.get("max")))
            except (TypeError, ValueError):
                continue

    return national_range, city_prices, items


def lookup_market(
    query: str,
    *,
    city: str = "",
    max_results: int = 5,
) -> MarketReport:
    """Search Habitissimo + CronoShare for market-price data.

    Returns a :class:`MarketReport` with the formatted LLM text (shape
    preserved from legacy ``search_prices``) plus structured fields for
    programmatic consumers.

    Raises:
        :class:`QueryEmptyError` — empty ``query``.
        :class:`IndexNotFoundError` — prices DB not configured.
    """

    if not query or not query.strip():
        raise QueryEmptyError("lookup_market called with empty query")

    idx = _get_index()

    city_norm = strip_accents(city.lower()) if city else ""

    header = f"Spanish market pricing for '{query}'"
    if city:
        header += f" in {city}"

    city_rows: List[dict] = []
    fts_results: list = []
    sources_used: Set[str] = set()
    text_parts: List[str] = []

    if city:
        rows = idx.search_city(city=city, query=query, limit=max_results * 2)
        city_rows = _dedupe_city_rows(rows, max_results)

        if city_rows:
            text_parts.extend(_format_city_row(r) for r in city_rows)
            sources_used.update(
                _SOURCE_LABELS.get(r.get("source", ""), "")
                for r in city_rows
                if r.get("source")
            )

    if not text_parts:
        results = idx.search(query, limit=max_results * 3, city=city)
        seen: Dict[str, int] = {}
        selected = []
        for result in results:
            if len(selected) >= max_results:
                break
            source = result.meta.get("source", "")
            count = seen.get(source, 0)
            if count < max_results - 1:
                selected.append(result)
                seen[source] = count + 1

        fts_results = selected
        text_parts.extend(_format_fts_result(r, city_norm) for r in selected)
        sources_used.update(
            _SOURCE_LABELS.get(r.meta.get("source", ""), "")
            for r in selected
            if r.meta.get("source")
        )

    if text_parts:
        source_str = ", ".join(sorted(s for s in sources_used if s))
        header += f" (sources: {source_str}):\n" if source_str else ":\n"
        text = header + "\n\n---\n\n".join(text_parts)
    else:
        text = (
            f"No pricing data found for '{query}' in either "
            "Habitissimo or CronoShare databases."
        )

    national_range, city_prices, items = _extract_structured(
        city_rows, fts_results, city,
    )

    return MarketReport(
        query=query,
        city=city,
        total_results=len(city_rows) + len(fts_results),
        sources_used=sorted(s for s in sources_used if s),
        national_range_eur=national_range,
        city_prices_eur=city_prices,
        items=items,
        text=text,
    )
