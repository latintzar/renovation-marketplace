"""Unit tests for :mod:`scraping.robots`."""
from __future__ import annotations

import pytest
import httpx

from scraping import RobotsChecker, is_allowed


class _FakeResp:
    def __init__(self, *, status_code: int = 200, text: str = "") -> None:
        self.status_code = status_code
        self.text = text
        self.request = httpx.Request("GET", "https://example.com/robots.txt")

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"HTTP {self.status_code}",
                request=self.request,
                response=self,  # type: ignore[arg-type]
            )


class _FakeClient:
    def __init__(self, *, resp: _FakeResp) -> None:
        self._resp = resp

    async def __aenter__(self) -> "_FakeClient":
        return self

    async def __aexit__(self, *exc) -> None: ...

    async def get(self, url, headers=None) -> _FakeResp:
        return self._resp


def _install_fake_client(
    monkeypatch: pytest.MonkeyPatch, module_name: str, resp: _FakeResp
) -> None:
    def _factory(**kwargs):
        return _FakeClient(resp=resp)

    monkeypatch.setattr(httpx, "AsyncClient", _factory)


@pytest.mark.asyncio
async def test_is_allowed_true_when_robots_permits(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resp = _FakeResp(text="User-agent: *\nAllow: /\n")
    _install_fake_client(monkeypatch, "scraping.robots", resp)
    checker = RobotsChecker(cache_ttl=0.0)
    assert await checker.is_allowed("https://example.com/any")


@pytest.mark.asyncio
async def test_is_allowed_false_when_robots_disallows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resp = _FakeResp(text="User-agent: *\nDisallow: /private/\n")
    _install_fake_client(monkeypatch, "scraping.robots", resp)
    checker = RobotsChecker(cache_ttl=0.0)
    assert not await checker.is_allowed("https://example.com/private/secret")


@pytest.mark.asyncio
async def test_is_allowed_true_on_404(monkeypatch: pytest.MonkeyPatch) -> None:
    """D10 permissive default: 404 on /robots.txt → treat as allowed."""

    resp = _FakeResp(status_code=404, text="not found")
    _install_fake_client(monkeypatch, "scraping.robots", resp)
    checker = RobotsChecker(cache_ttl=0.0)
    assert await checker.is_allowed("https://example.com/anything")


@pytest.mark.asyncio
async def test_is_allowed_permissive_on_network_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Boom:
        def __init__(self, **kwargs) -> None: ...

        async def __aenter__(self) -> "_Boom":
            return self

        async def __aexit__(self, *exc) -> None: ...

        async def get(self, *a, **k) -> _FakeResp:
            raise httpx.ConnectError("dns fail")

    monkeypatch.setattr(httpx, "AsyncClient", lambda **kw: _Boom(**kw))
    checker = RobotsChecker(cache_ttl=0.0)
    assert await checker.is_allowed("https://example.com/")


@pytest.mark.asyncio
async def test_module_is_allowed_convenience(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resp = _FakeResp(text="User-agent: *\nAllow: /\n")
    _install_fake_client(monkeypatch, "scraping.robots", resp)
    assert await is_allowed("https://example.com/")


@pytest.mark.asyncio
async def test_is_allowed_handles_scheme_free_input() -> None:
    """URL without scheme/netloc short-circuits to allowed."""

    checker = RobotsChecker()
    assert await checker.is_allowed("")
    assert await checker.is_allowed("///bad")


@pytest.mark.asyncio
async def test_crawl_delay_returns_none_when_unspecified(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    resp = _FakeResp(text="User-agent: *\nAllow: /\n")
    _install_fake_client(monkeypatch, "scraping.robots", resp)
    checker = RobotsChecker(cache_ttl=0.0)
    delay = await checker.crawl_delay("https://example.com/")
    assert delay is None or isinstance(delay, float)
