"""Unit tests for :mod:`scraping.fetch` — dispatch, JS_HOSTS, fetch_many."""
from __future__ import annotations

import asyncio
import sys
from typing import Any

import httpx
import pytest

from scraping import (
    FetchStrategy,
    JS_HOSTS,
    extend_js_hosts,
    fetch,
    fetch_many,
    fetch_static,
)
from scraping.errors import FetchError

fetch_mod = sys.modules["scraping.fetch"]


@pytest.fixture(autouse=True)
def _restore_js_hosts():
    """Snapshot :data:`JS_HOSTS` before each test and restore after."""

    snapshot = set(JS_HOSTS)
    yield
    JS_HOSTS.clear()
    JS_HOSTS.update(snapshot)


def test_fetch_strategy_enum_values() -> None:
    assert FetchStrategy.AUTO.value == "auto"
    assert FetchStrategy.STATIC.value == "static"
    assert FetchStrategy.BROWSER.value == "browser"


def test_js_hosts_default_includes_known_js_sites() -> None:
    for h in ("facebook.com", "instagram.com", "x.com", "tiktok.com"):
        assert h in JS_HOSTS


def test_extend_js_hosts_idempotent() -> None:
    before = len(JS_HOSTS)
    extend_js_hosts(["reddit.com", "threads.net"])
    extend_js_hosts(["reddit.com"])
    assert "reddit.com" in JS_HOSTS
    assert "threads.net" in JS_HOSTS
    assert len(JS_HOSTS) == before + 2


def test_extend_js_hosts_ignores_empty() -> None:
    before = len(JS_HOSTS)
    extend_js_hosts(["", ""])
    assert len(JS_HOSTS) == before


@pytest.mark.asyncio
async def test_fetch_static_raises_on_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Static tier wraps httpx errors into :class:`FetchError`."""

    class _FakeResp:
        def __init__(self) -> None:
            self.status_code = 500
            self.text = ""
            self.request = httpx.Request("GET", "https://example.com")

        def raise_for_status(self) -> None:
            raise httpx.HTTPStatusError("500", request=self.request, response=self)  # type: ignore[arg-type]

    class _FakeClient:
        def __init__(self, **kwargs) -> None: ...

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *exc) -> None: ...

        async def get(self, *args, **kwargs) -> _FakeResp:
            return _FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _FakeClient(**kw))

    with pytest.raises(FetchError):
        await fetch_static("https://example.com/fail")


@pytest.mark.asyncio
async def test_fetch_static_returns_body(monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeResp:
        text = "<html>ok</html>"
        status_code = 200

        def raise_for_status(self) -> None: ...

    class _FakeClient:
        def __init__(self, **kwargs) -> None: ...

        async def __aenter__(self) -> "_FakeClient":
            return self

        async def __aexit__(self, *exc) -> None: ...

        async def get(self, url, headers=None) -> _FakeResp:
            return _FakeResp()

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _FakeClient(**kw))

    body = await fetch_static("https://example.com/")
    assert "ok" in body


@pytest.mark.asyncio
async def test_fetch_browser_returns_empty_on_cdp_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When the underlying CDP fetch raises, :func:`fetch_browser` logs
    and returns ``""`` — preserving the pre-migration empty-string
    contract consumed by ``workflows.contractor_discovery``."""

    async def _boom(url, **kwargs):
        raise RuntimeError("CDP down")

    monkeypatch.setattr("scraping._cdp.fetch_via_cdp", _boom)

    from scraping import fetch_browser

    out = await fetch_browser("https://facebook.com/group/123")
    assert out == ""


@pytest.mark.asyncio
async def test_fetch_dispatches_to_browser_on_js_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, Any] = {}

    async def _fake_browser(url, **kwargs):
        called["browser"] = url
        return "<html>browser</html>"

    async def _fake_static(url, **kwargs):
        called["static"] = url
        return "<html>static</html>"

    async def _allow(url, user_agent="*", strict=False):
        return True

    monkeypatch.setattr(fetch_mod, "fetch_browser", _fake_browser)
    monkeypatch.setattr(fetch_mod, "fetch_static", _fake_static)
    monkeypatch.setattr("scraping.robots.is_allowed", _allow)

    body = await fetch("https://www.facebook.com/group/123")
    assert "browser" in body
    assert "browser" in called
    assert "static" not in called


@pytest.mark.asyncio
async def test_fetch_dispatches_to_static_on_non_js_host(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called: dict[str, Any] = {}

    async def _fake_static(url, **kwargs):
        called["static"] = url
        return "<html>static</html>"

    async def _allow(url, user_agent="*", strict=False):
        return True

    monkeypatch.setattr(fetch_mod, "fetch_static", _fake_static)
    monkeypatch.setattr("scraping.robots.is_allowed", _allow)

    body = await fetch("https://boe.es/eli/es/rd/2020/01/01")
    assert "static" in body
    assert "static" in called


@pytest.mark.asyncio
async def test_fetch_respects_robots_disallow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from scraping import RobotsDisallowed

    async def _deny(url, user_agent="*", strict=False):
        return False

    monkeypatch.setattr("scraping.robots.is_allowed", _deny)

    with pytest.raises(RobotsDisallowed):
        await fetch("https://respectful.example/scrapeme")


@pytest.mark.asyncio
async def test_fetch_skips_robots_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _deny(url, user_agent="*", strict=False):
        return False

    async def _fake_static(url, **kwargs):
        return "ok"

    monkeypatch.setattr("scraping.robots.is_allowed", _deny)
    monkeypatch.setattr(fetch_mod, "fetch_static", _fake_static)

    out = await fetch("https://any.example/", respect_robots=False)
    assert out == "ok"


@pytest.mark.asyncio
async def test_fetch_many_populates_empty_on_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_static(url, **kwargs):
        if "good" in url:
            return "ok"
        raise FetchError("boom")

    async def _allow(url, user_agent="*", strict=False):
        return True

    monkeypatch.setattr(fetch_mod, "fetch_static", _fake_static)
    monkeypatch.setattr("scraping.robots.is_allowed", _allow)

    out = await fetch_many(
        ["https://good.example/", "https://bad.example/"],
        strategy=FetchStrategy.STATIC,
    )
    assert out["https://good.example/"] == "ok"
    assert out["https://bad.example/"] == ""


@pytest.mark.asyncio
async def test_extract_text_composes_fetch_and_html_to_text(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    async def _fake_fetch(url, **kwargs):
        return "<p>hello world</p>"

    async def _allow(url, user_agent="*", strict=False):
        return True

    monkeypatch.setattr(fetch_mod, "fetch", _fake_fetch)
    monkeypatch.setattr("scraping.robots.is_allowed", _allow)

    from scraping.fetch import extract_text

    text = await extract_text("https://example.com/")
    assert "hello world" in text
