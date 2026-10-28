"""SQLite FTS5 index — BM25-ranked full-text search for a single
domain collection (prices, forum threads, CYPE rubrics, etc.) (D1).

:class:`DomainIndex` owns one SQLite database file (``{name}.db``) and
exposes a small synchronous surface:

* :meth:`add` / :meth:`add_city_price` — write path (caller commits).
* :meth:`search` — BM25 lookup, synonym-expanded, optional city boost.
* :meth:`search_city` — flat city_prices join (cheap exact-city lookup
  with optional FTS narrowing).
* :meth:`rebuild` / :meth:`drop` / :meth:`close` — lifecycle.

Schema (three tables):

* ``documents``  — source-of-truth rows (doc_id PK, slug/title/body
  stored *pre-stemmed* for space + search parity).
* ``city_prices`` — flat (doc_id, city) lookup for the pricing
  consumer (generic; other consumers can ignore).
* ``docs_fts``   — FTS5 virtual table shadowing ``documents``; triggers
  keep it in sync. Field weights ``(slug=10, title=5, body=1)`` are
  baked into every ``bm25()`` call.

``sqlite3.OperationalError`` from malformed FTS5 queries is caught
and logged → empty list. This is intentional (D8): retrieval is a
best-effort feature of every tool; a bad expansion must never 500.
"""
from __future__ import annotations

import json as _json
import logging
import os
import sqlite3
from pathlib import Path
from typing import Any, Optional

from core.text import strip_accents

from ._stemmer import stem_word
from .results import SearchResult
from .synonyms import expand_query
from .tokenizer import tokenize

logger = logging.getLogger(__name__)

__all__ = ["DomainIndex"]


class DomainIndex:
    """Thin wrapper over a single SQLite FTS5 domain collection."""

    def __init__(self, name: str, db_path: Optional[str] = None):
        """:param name: Logical collection name (``"prices"``, ``"cype"``).
        :param db_path: Optional explicit path; if omitted, uses
            ``<package_root>/data/indexes/{name}.db`` relative to the
            consumer — pass one explicitly in production callers.
        """

        self.name = name
        if db_path is None:
            db_path = str(
                Path.cwd() / "data" / "indexes" / f"{name}.db"
            )
        self.db_path = db_path

        os.makedirs(os.path.dirname(self.db_path) or ".", exist_ok=True)

        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._setup_tables()

    def _setup_tables(self) -> None:
        self._conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS documents (
                doc_id   TEXT PRIMARY KEY,
                slug     TEXT NOT NULL DEFAULT '',
                title    TEXT NOT NULL DEFAULT '',
                body     TEXT NOT NULL DEFAULT '',
                meta     TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS city_prices (
                doc_id   TEXT NOT NULL,
                city     TEXT NOT NULL COLLATE NOCASE,
                prices   TEXT NOT NULL DEFAULT '[]',
                source   TEXT NOT NULL DEFAULT '',
                title    TEXT NOT NULL DEFAULT '',
                slug     TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (doc_id, city)
            );
            CREATE INDEX IF NOT EXISTS idx_city ON city_prices(city COLLATE NOCASE);

            CREATE VIRTUAL TABLE IF NOT EXISTS docs_fts USING fts5(
                slug,
                title,
                body,
                content='documents',
                content_rowid='rowid',
                tokenize='unicode61'
            );

            CREATE TRIGGER IF NOT EXISTS docs_ai AFTER INSERT ON documents BEGIN
                INSERT INTO docs_fts(rowid, slug, title, body)
                VALUES (new.rowid, new.slug, new.title, new.body);
            END;

            CREATE TRIGGER IF NOT EXISTS docs_ad AFTER DELETE ON documents BEGIN
                INSERT INTO docs_fts(docs_fts, rowid, slug, title, body)
                VALUES ('delete', old.rowid, old.slug, old.title, old.body);
            END;

            CREATE TRIGGER IF NOT EXISTS docs_au AFTER UPDATE ON documents BEGIN
                INSERT INTO docs_fts(docs_fts, rowid, slug, title, body)
                VALUES ('delete', old.rowid, old.slug, old.title, old.body);
                INSERT INTO docs_fts(rowid, slug, title, body)
                VALUES (new.rowid, new.slug, new.title, new.body);
            END;
            """
        )

    def add(
        self,
        doc_id: str,
        slug: str = "",
        title: str = "",
        body: str = "",
        meta: Optional[dict] = None,
    ) -> None:
        """Insert or replace a document. All text fields are stemmed at
        index time — the ``documents`` table stores the post-tokenisation
        form, which the FTS triggers then index. This keeps index-time
        and query-time tokenisation in lock-step (D4)."""

        slug_stemmed = " ".join(tokenize(slug.replace("-", " ")))
        title_stemmed = " ".join(tokenize(title))
        body_stemmed = " ".join(tokenize(body))
        meta_json = _json.dumps(meta or {}, ensure_ascii=False)

        self._conn.execute(
            """
            INSERT OR REPLACE INTO documents (doc_id, slug, title, body, meta)
            VALUES (?, ?, ?, ?, ?)
            """,
            (doc_id, slug_stemmed, title_stemmed, body_stemmed, meta_json),
        )

    def add_city_price(
        self,
        doc_id: str,
        city: str,
        prices: list,
        source: str = "",
        title: str = "",
        slug: str = "",
    ) -> None:
        """Insert or replace a (doc_id, city) pricing row.

        ``city_prices`` is a **flat** table — one row per city per
        document — letting the pricing consumer do exact-city lookups
        without scanning the FTS index. ``prices`` is a list of raw
        price mention strings, JSON-encoded for storage."""

        self._conn.execute(
            """
            INSERT OR REPLACE INTO city_prices
              (doc_id, city, prices, source, title, slug)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                doc_id,
                city,
                _json.dumps(prices, ensure_ascii=False),
                source,
                title,
                slug,
            ),
        )

    def commit(self) -> None:
        """Flush pending writes."""

        self._conn.commit()

    def count(self) -> int:
        """Return number of indexed documents."""

        row = self._conn.execute("SELECT COUNT(*) FROM documents").fetchone()
        return row[0] if row else 0

    def search(
        self,
        query: str,
        limit: int = 10,
        city: str = "",
    ) -> list[SearchResult]:
        """Full-text search with BM25 ranking.

        Query is expanded via :func:`fulltext.synonyms.expand_query`.
        Field weights: slug × 10, title × 5, body × 1.
        If ``city`` is supplied, results mentioning it in
        ``meta["city_prices"]`` receive a rank boost (lower-is-better,
        so we subtract 20.0). Over-fetches 3× ``limit`` so the boost
        has a meaningful pool to rerank from.

        Returns ``[]`` on any FTS5 syntax error — the only way
        retrieval is allowed to fail is silently.
        """

        fts_query = expand_query(query)
        if not fts_query.strip():
            return []

        try:
            rows = self._conn.execute(
                """
                SELECT
                    d.doc_id,
                    bm25(docs_fts, 10.0, 5.0, 1.0) AS rank,
                    d.slug,
                    d.title,
                    d.body,
                    d.meta
                FROM docs_fts f
                JOIN documents d ON d.rowid = f.rowid
                WHERE docs_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (fts_query, limit * 3),
            ).fetchall()
        except sqlite3.OperationalError as e:
            logger.warning(
                "FTS5 query failed | query=%r | fts=%r | err=%s",
                query,
                fts_query,
                e,
            )
            return []

        results: list[SearchResult] = []
        for doc_id, rank, slug, title, body, meta_json in rows:
            meta: dict[str, Any] = _json.loads(meta_json) if meta_json else {}
            results.append(
                SearchResult(
                    doc_id=doc_id,
                    rank=rank,
                    slug=slug,
                    title=title,
                    body=body,
                    meta=meta,
                )
            )

        if city:
            city_stem = stem_word(strip_accents(city.lower()))
            boosted: list[SearchResult] = []
            from dataclasses import replace as _replace

            for r in results:
                cps = r.meta.get("city_prices", []) if isinstance(r.meta, dict) else []
                applied = False
                for cp in cps:
                    cp_city = strip_accents((cp.get("city") or "").lower())
                    if not cp_city:
                        continue
                    if city_stem in cp_city or cp_city in city_stem:
                        boosted.append(_replace(r, rank=r.rank - 20.0))
                        applied = True
                        break
                if not applied:
                    boosted.append(r)
            boosted.sort(key=lambda x: x.rank)
            results = boosted

        return results[:limit]

    def search_city(
        self,
        city: str,
        query: str = "",
        limit: int = 10,
    ) -> list[dict]:
        """Flat city-price lookup, optionally narrowed by an FTS query.

        When ``query`` is provided we first pull the top matching
        ``doc_id`` set via FTS5 (over-fetched 3× to survive the join),
        then intersect against ``city_prices`` for the exact ``city``.
        Without ``query``, returns the first ``limit`` rows for the
        city, grouped by slug.

        Returns a list of plain dicts (``title``, ``slug``, ``source``,
        ``city``, ``prices``) rather than ``SearchResult`` — callers
        are price-rendering tools that want the raw mention list.
        """

        if query:
            fts_query = expand_query(query)
            try:
                fts_rows = self._conn.execute(
                    """
                    SELECT d.doc_id
                    FROM docs_fts f
                    JOIN documents d ON d.rowid = f.rowid
                    WHERE docs_fts MATCH ?
                    ORDER BY bm25(docs_fts, 10.0, 5.0, 1.0)
                    LIMIT ?
                    """,
                    (fts_query, limit * 3),
                ).fetchall()
            except sqlite3.OperationalError as e:
                logger.warning("FTS5 city search failed | err=%s", e)
                fts_rows = []

            doc_ids = list(dict.fromkeys(r[0] for r in fts_rows))
            if not doc_ids:
                return []

            placeholders = ",".join("?" * len(doc_ids))
            rows = self._conn.execute(
                f"""
                SELECT cp.title, cp.slug, cp.source, cp.city, cp.prices
                FROM city_prices cp
                WHERE cp.city = ? COLLATE NOCASE
                  AND cp.doc_id IN ({placeholders})
                GROUP BY cp.slug
                LIMIT ?
                """,
                [city, *doc_ids, limit],
            ).fetchall()
        else:
            rows = self._conn.execute(
                """
                SELECT title, slug, source, city, prices
                FROM city_prices
                WHERE city = ? COLLATE NOCASE
                GROUP BY slug
                LIMIT ?
                """,
                (city, limit),
            ).fetchall()

        results: list[dict] = []
        for title, slug, source, city_val, prices_json in rows:
            prices = _json.loads(prices_json) if prices_json else []
            results.append(
                {
                    "title": title,
                    "slug": slug,
                    "source": source,
                    "city": city_val,
                    "prices": prices,
                }
            )
        return results

    def rebuild(self) -> None:
        """Rebuild the FTS5 index from scratch (expensive)."""

        self._conn.execute("INSERT INTO docs_fts(docs_fts) VALUES ('rebuild')")
        self._conn.commit()
        logger.info("Rebuilt FTS5 index for %s", self.name)

    def drop(self) -> None:
        """Drop and recreate all tables."""

        self._conn.executescript(
            """
            DROP TABLE IF EXISTS docs_fts;
            DROP TABLE IF EXISTS city_prices;
            DROP TABLE IF EXISTS documents;
            """
        )
        self._setup_tables()
        self._conn.commit()

    def close(self) -> None:
        """Close the underlying SQLite connection."""

        self._conn.close()

    def __del__(self) -> None:  # pragma: no cover - best-effort cleanup
        try:
            self._conn.close()
        except Exception:
            pass
