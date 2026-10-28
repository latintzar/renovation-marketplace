"""Opt-in disk cache for :func:`fetch` (D11).

Plain file-based TTL cache under ``~/.cache/leo/scraping/``. Simple
enough to be ~30 lines of stdlib (no :mod:`diskcache` dep), LRU
eviction is future-work when needed.

Cache key = ``sha256(url + strategy).hexdigest()``. Two files per
entry:

* ``<key>.html`` — the raw HTML body.
* ``<key>.json`` — metadata: ``{"url", "timestamp", "strategy",
  "content_length"}``.

On each call:

1. Stat the metadata file. If fresh (``now - timestamp < ttl``), return
   the cached HTML.
2. Otherwise fetch via :func:`fetch` and rewrite both files atomically.
3. ``refresh=True`` forces re-fetch regardless of cache state.

Not silently caching is a deliberate choice (D11): the disk layer is
only engaged when the caller opts in with :func:`cached_fetch`. No
middleware-style wrapping of :func:`fetch`.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Optional

from .fetch import FetchStrategy, fetch

logger = logging.getLogger(__name__)

__all__ = ["cached_fetch", "cache_path", "DEFAULT_CACHE_DIR"]


DEFAULT_CACHE_DIR = Path.home() / ".cache" / "leo" / "scraping"


def _cache_key(url: str, strategy: FetchStrategy) -> str:
    """Deterministic hex key for ``(url, strategy)``."""

    payload = f"{url}|{strategy.value}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def cache_path(
    url: str,
    *,
    strategy: FetchStrategy = FetchStrategy.AUTO,
    cache_dir: Optional[Path] = None,
) -> Path:
    """Return the HTML path (``<dir>/<key>.html``) for an entry.

    Does **not** check whether the file exists. Primarily useful for
    tests that want to inspect cache contents."""

    root = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    key = _cache_key(url, strategy)
    return root / f"{key}.html"


def _meta_path(html_path: Path) -> Path:
    return html_path.with_suffix(".json")


def _atomic_write_text(path: Path, content: str) -> None:
    """Write ``content`` to ``path`` via a tempfile rename.

    Avoids half-written files on crash mid-write. ``tempfile.mkstemp``
    in the target directory keeps the rename on-filesystem."""

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except Exception:
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise


async def cached_fetch(
    url: str,
    *,
    ttl: float = 3600.0,
    strategy: FetchStrategy = FetchStrategy.AUTO,
    cache_dir: Optional[Path] = None,
    refresh: bool = False,
    respect_robots: bool = True,
    timeout: float = 15.0,
) -> str:
    """File-based TTL cache around :func:`fetch`.

    :param ttl: Max age in seconds. Entries older than this are
        re-fetched.
    :param cache_dir: Override cache root. Defaults to
        ``~/.cache/leo/scraping/``.
    :param refresh: Force a fresh fetch + cache overwrite.
    :returns: The HTML body. Empty string if the underlying
        :func:`fetch_browser` returned empty AND no prior cached copy
        exists.
    """

    root = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
    key = _cache_key(url, strategy)
    html_path = root / f"{key}.html"
    meta_path = _meta_path(html_path)

    if not refresh and meta_path.exists() and html_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            ts = float(meta.get("timestamp", 0))
            if time.time() - ts < ttl:
                return html_path.read_text(encoding="utf-8")
        except (OSError, ValueError, json.JSONDecodeError) as e:
            logger.debug("cache metadata unreadable at %s: %s", meta_path, e)

    html = await fetch(
        url,
        strategy=strategy,
        respect_robots=respect_robots,
        timeout=timeout,
    )

    if html:
        _atomic_write_text(html_path, html)
        meta = {
            "url": url,
            "timestamp": time.time(),
            "strategy": strategy.value,
            "content_length": len(html),
        }
        _atomic_write_text(
            meta_path, json.dumps(meta, ensure_ascii=False, indent=2)
        )

    return html
