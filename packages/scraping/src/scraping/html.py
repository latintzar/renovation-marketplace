"""scraping.html — canonical HTML parser for the monorepo.

Backed by lxml (tolerant, fast, accurate line numbers). Exposes a small surface
that covers every HTML-parsing need across the codebase:

- parse_html(text)            -> ParsedHtml
- iter_tags(parsed, names)    -> Iterator[Tag]
- tag_attr(tag, name)         -> str | None
- tag_lineno(tag)             -> int (1-indexed)
- tag_text(tag)               -> str (inner text, no tags)
- parse_srcset(srcset)        -> list[str]  (urls only; candidate descriptors dropped)
- is_external_url(url)        -> bool       (http/https/data/mailto/tel/js/#/protocol-relative)

Rationale: every consumer (walkers, scrapers, tests, tools) should use this so
HTML parsing behavior is consistent repo-wide. lxml is chosen over bs4 because
it handles malformed HTML more predictably, is substantially faster, and gives
us exact line numbers (critical for walker evidence).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, Iterator, Optional

from lxml import etree, html as lxml_html


__all__ = [
    "ParsedHtml",
    "Tag",
    "parse_html",
    "iter_tags",
    "tag_attr",
    "tag_lineno",
    "tag_text",
    "parse_srcset",
    "is_external_url",
]


@dataclass(frozen=True)
class ParsedHtml:
    """A parsed HTML document. Opaque wrapper over lxml tree."""

    tree: etree._ElementTree  # type: ignore[name-defined]


# lxml elements already expose .sourceline / .attrib / .tag — we alias the type
# so downstream code doesn't import lxml directly.
Tag = etree._Element  # type: ignore[assignment]


_EXTERNAL_PREFIXES = (
    "http://", "https://", "//", "data:", "blob:",
    "mailto:", "tel:", "sms:", "javascript:",
)


def is_external_url(url: str) -> bool:
    """True if `url` is not a repo-local reference worth resolving."""
    if not url:
        return True
    u = url.strip()
    if not u or u.startswith("#"):
        return True
    return u.startswith(_EXTERNAL_PREFIXES)


def parse_html(text: str) -> ParsedHtml:
    """Parse HTML tolerantly. Preserves 1-indexed sourceline on every tag.

    Uses a document-level parse (not fragment) so `<head>` children like
    `<link>` and `<script>` are retained. Works on fragments too: lxml's
    recover mode synthesizes missing html/body structure without discarding
    real tags.
    """
    parser = lxml_html.HTMLParser(recover=True, remove_comments=False)
    root = lxml_html.document_fromstring(text, parser=parser)
    tree = etree.ElementTree(root)
    return ParsedHtml(tree=tree)


def iter_tags(parsed: ParsedHtml, names: Iterable[str] | None = None) -> Iterator[Tag]:
    """Iterate tags in document order, optionally filtered by tag name(s)."""
    name_set = {n.lower() for n in names} if names else None
    for el in parsed.tree.iter():
        if not isinstance(el.tag, str):
            continue  # skip comments, PIs
        if name_set is None or el.tag.lower() in name_set:
            yield el


def tag_attr(tag: Tag, name: str) -> Optional[str]:
    """Case-insensitive attribute lookup. Returns None if absent."""
    v = tag.get(name)
    if v is not None:
        return v
    lower = name.lower()
    for k, val in tag.attrib.items():
        if k.lower() == lower:
            return val
    return None


def tag_lineno(tag: Tag) -> int:
    """1-indexed line of the tag's opening bracket (0 if unknown)."""
    return int(getattr(tag, "sourceline", 0) or 0)


def tag_text(tag: Tag) -> str:
    """Inner text with no markup, whitespace-collapsed."""
    return " ".join((tag.text_content() or "").split())


# srcset: parse "url 1x, url2 2x, url3 600w" → ["url", "url2", "url3"]
_SRCSET_CAND_RE = re.compile(r"\s*([^\s,][^\s,]*)(?:\s+[^,]+)?")


def parse_srcset(value: str) -> list[str]:
    """Return the URL portion of every candidate in a srcset string."""
    if not value:
        return []
    out: list[str] = []
    for part in value.split(","):
        m = _SRCSET_CAND_RE.match(part)
        if m:
            out.append(m.group(1).strip())
    return [u for u in out if u]
