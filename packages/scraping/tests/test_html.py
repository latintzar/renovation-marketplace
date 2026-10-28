"""Unit tests for :mod:`scraping.html`."""
from __future__ import annotations

from scraping import (
    ParsedHtml,
    is_external_url,
    iter_tags,
    parse_html,
    parse_srcset,
    tag_attr,
    tag_lineno,
    tag_text,
)


def test_parse_html_returns_wrapper(simple_html: str) -> None:
    parsed = parse_html(simple_html)
    assert isinstance(parsed, ParsedHtml)


def test_iter_tags_all(simple_html: str) -> None:
    parsed = parse_html(simple_html)
    tags = [t.tag for t in iter_tags(parsed)]
    assert "html" in tags
    assert "body" in tags
    assert "h1" in tags


def test_iter_tags_filtered(simple_html: str) -> None:
    parsed = parse_html(simple_html)
    links = list(iter_tags(parsed, {"a"}))
    assert len(links) == 1
    assert tag_attr(links[0], "href") == "tel:+34 612 345 678"


def test_tag_attr_case_insensitive(simple_html: str) -> None:
    parsed = parse_html(simple_html)
    img = next(iter_tags(parsed, {"img"}))
    assert tag_attr(img, "SRC") == "/a.jpg"
    assert tag_attr(img, "Missing") is None


def test_tag_lineno_is_positive(simple_html: str) -> None:
    parsed = parse_html(simple_html)
    title = next(iter_tags(parsed, {"title"}))
    assert tag_lineno(title) >= 1


def test_tag_text_collapses_whitespace() -> None:
    parsed = parse_html("<p>   hi \n   there   </p>")
    p = next(iter_tags(parsed, {"p"}))
    assert tag_text(p) == "hi there"


def test_parse_srcset_strips_descriptors() -> None:
    assert parse_srcset("a.jpg 1x, b.jpg 2x, c.jpg 3x") == [
        "a.jpg",
        "b.jpg",
        "c.jpg",
    ]


def test_parse_srcset_handles_whitespace() -> None:
    assert parse_srcset("  a.jpg 1x,  b.jpg  ") == ["a.jpg", "b.jpg"]


def test_parse_srcset_empty() -> None:
    assert parse_srcset("") == []


def test_is_external_url() -> None:
    assert is_external_url("http://example.com")
    assert is_external_url("https://example.com")
    assert is_external_url("//cdn.example.com/a.js")
    assert is_external_url("data:image/png;base64,xxx")
    assert is_external_url("mailto:x@example.com")
    assert is_external_url("tel:+34")
    assert is_external_url("javascript:void(0)")
    assert is_external_url("#anchor")
    assert is_external_url("")
    assert not is_external_url("/local/path")
    assert not is_external_url("./rel.html")


def test_parse_html_tolerates_malformed() -> None:
    """lxml ``recover=True`` must survive missing close tags."""

    parsed = parse_html("<div><p>hello<span>world</div>")
    spans = list(iter_tags(parsed, {"span"}))
    assert len(spans) == 1
