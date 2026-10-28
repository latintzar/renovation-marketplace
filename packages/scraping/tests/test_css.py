"""Unit tests for :mod:`scraping.css`."""
from __future__ import annotations

from scraping import CssRef, iter_css_refs


def test_iter_css_refs_empty() -> None:
    assert iter_css_refs("") == []


def test_import_at_rule() -> None:
    refs = iter_css_refs('@import url("./reset.css");')
    assert len(refs) == 1
    assert refs[0].kind == "import"
    assert refs[0].url == "./reset.css"
    assert refs[0].line == 1


def test_font_face_at_rule() -> None:
    css = """@font-face {
  font-family: "Inter";
  src: url("./fonts/inter.woff2") format("woff2");
}"""
    refs = iter_css_refs(css)
    assert len(refs) == 1
    assert refs[0].kind == "font"
    assert refs[0].url == "./fonts/inter.woff2"


def test_inline_url_in_qualified_rule() -> None:
    css = ".hero { background-image: url(/assets/hero.jpg); }"
    refs = iter_css_refs(css)
    assert [r.kind for r in refs] == ["url"]
    assert refs[0].url == "/assets/hero.jpg"


def test_multiple_refs_in_one_stylesheet() -> None:
    css = """@import url("./reset.css");
@font-face { src: url("./f.woff2"); }
.bg { background: url("./a.jpg"); }
"""
    refs = iter_css_refs(css)
    kinds = [r.kind for r in refs]
    assert sorted(kinds) == ["font", "import", "url"]


def test_frozen_dataclass_returns_consistent_shape() -> None:
    ref = CssRef(kind="url", url="/a.jpg", line=2, col=3)
    assert ref.kind == "url"
    assert ref.url == "/a.jpg"
