"""Unit tests for :func:`scraping.parse_soup`."""
from __future__ import annotations

from scraping import parse_soup


def test_parse_soup_returns_soup(simple_html: str) -> None:
    soup = parse_soup(simple_html)
    assert soup.__class__.__name__ == "BeautifulSoup"


def test_parse_soup_find(simple_html: str) -> None:
    soup = parse_soup(simple_html)
    h1 = soup.find("h1")
    assert h1 is not None
    assert "Cocina" in h1.get_text()


def test_parse_soup_selector(simple_html: str) -> None:
    soup = parse_soup(simple_html)
    anchors = soup.select("a[href]")
    assert len(anchors) == 1
    assert anchors[0]["href"].startswith("tel:")


def test_parse_soup_empty_string() -> None:
    soup = parse_soup("")
    assert soup.__class__.__name__ == "BeautifulSoup"
    assert soup.get_text() == ""


def test_parse_soup_malformed_recovers() -> None:
    soup = parse_soup("<p>foo<span>bar</p>")
    assert "foo" in soup.get_text()
    assert "bar" in soup.get_text()
