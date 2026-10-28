"""Unit tests for :mod:`scraping.cache`."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest

from scraping import FetchStrategy, cache_path, cached_fetch


def test_cache_path_deterministic(cache_tmp: Path) -> None:
    p1 = cache_path(
        "https://example.com/", strategy=FetchStrategy.STATIC, cache_dir=cache_tmp
    )
    p2 = cache_path(
        "https://example.com/", strategy=FetchStrategy.STATIC, cache_dir=cache_tmp
    )
    assert p1 == p2


def test_cache_path_differs_by_strategy(cache_tmp: Path) -> None:
    p_static = cache_path(
        "https://example.com/", strategy=FetchStrategy.STATIC, cache_dir=cache_tmp
    )
    p_browser = cache_path(
        "https://example.com/", strategy=FetchStrategy.BROWSER, cache_dir=cache_tmp
    )
    assert p_static != p_browser


@pytest.mark.asyncio
async def test_cached_fetch_writes_on_miss(
    cache_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def _fake_fetch(url, **kwargs):
        calls.append(url)
        return "<html>hello</html>"

    monkeypatch.setattr("scraping.cache.fetch", _fake_fetch)

    out = await cached_fetch(
        "https://example.com/",
        strategy=FetchStrategy.STATIC,
        cache_dir=cache_tmp,
        respect_robots=False,
    )
    assert out == "<html>hello</html>"
    assert len(calls) == 1

    entry = cache_path(
        "https://example.com/", strategy=FetchStrategy.STATIC, cache_dir=cache_tmp
    )
    assert entry.exists()
    meta = entry.with_suffix(".json")
    assert meta.exists()
    meta_json = json.loads(meta.read_text(encoding="utf-8"))
    assert meta_json["url"] == "https://example.com/"
    assert meta_json["strategy"] == "static"


@pytest.mark.asyncio
async def test_cached_fetch_hits_cache_within_ttl(
    cache_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []

    async def _fake_fetch(url, **kwargs):
        calls.append(url)
        return "<html>fresh</html>"

    monkeypatch.setattr("scraping.cache.fetch", _fake_fetch)

    await cached_fetch(
        "https://example.com/",
        ttl=3600.0,
        strategy=FetchStrategy.STATIC,
        cache_dir=cache_tmp,
        respect_robots=False,
    )

    out = await cached_fetch(
        "https://example.com/",
        ttl=3600.0,
        strategy=FetchStrategy.STATIC,
        cache_dir=cache_tmp,
        respect_robots=False,
    )

    assert out == "<html>fresh</html>"
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_cached_fetch_refetches_after_ttl_expiry(
    cache_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = iter(["<html>v1</html>", "<html>v2</html>"])

    async def _fake_fetch(url, **kwargs):
        return next(answers)

    monkeypatch.setattr("scraping.cache.fetch", _fake_fetch)

    await cached_fetch(
        "https://example.com/",
        ttl=0.0,
        strategy=FetchStrategy.STATIC,
        cache_dir=cache_tmp,
        respect_robots=False,
    )
    time.sleep(0.01)
    out = await cached_fetch(
        "https://example.com/",
        ttl=0.0,
        strategy=FetchStrategy.STATIC,
        cache_dir=cache_tmp,
        respect_robots=False,
    )
    assert out == "<html>v2</html>"


@pytest.mark.asyncio
async def test_cached_fetch_refresh_bypasses(
    cache_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    answers = iter(["v1", "v2"])

    async def _fake_fetch(url, **kwargs):
        return next(answers)

    monkeypatch.setattr("scraping.cache.fetch", _fake_fetch)

    await cached_fetch(
        "https://example.com/",
        strategy=FetchStrategy.STATIC,
        cache_dir=cache_tmp,
        respect_robots=False,
    )
    out = await cached_fetch(
        "https://example.com/",
        strategy=FetchStrategy.STATIC,
        cache_dir=cache_tmp,
        refresh=True,
        respect_robots=False,
    )
    assert out == "v2"


@pytest.mark.asyncio
async def test_cached_fetch_does_not_persist_empty(
    cache_tmp: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Empty string from :func:`fetch_browser` must not pollute the cache."""

    async def _fake_fetch(url, **kwargs):
        return ""

    monkeypatch.setattr("scraping.cache.fetch", _fake_fetch)

    out = await cached_fetch(
        "https://facebook.com/group/123",
        strategy=FetchStrategy.BROWSER,
        cache_dir=cache_tmp,
        respect_robots=False,
    )
    assert out == ""

    entry = cache_path(
        "https://facebook.com/group/123",
        strategy=FetchStrategy.BROWSER,
        cache_dir=cache_tmp,
    )
    assert not entry.exists()
