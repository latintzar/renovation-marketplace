"""Unit tests for :mod:`scraping.errors`."""
from __future__ import annotations

from scraping import (
    BrowserUnavailable,
    FetchError,
    RobotsDisallowed,
    ScrapingError,
)


def test_hierarchy() -> None:
    assert issubclass(FetchError, ScrapingError)
    assert issubclass(BrowserUnavailable, ScrapingError)
    assert issubclass(RobotsDisallowed, ScrapingError)


def test_robots_disallowed_attrs() -> None:
    err = RobotsDisallowed("https://example.com/", user_agent="LeoBot/1.0")
    assert err.url == "https://example.com/"
    assert err.user_agent == "LeoBot/1.0"
    assert "example.com" in str(err)


def test_robots_disallowed_default_ua() -> None:
    err = RobotsDisallowed("https://example.com/")
    assert err.user_agent == "*"
