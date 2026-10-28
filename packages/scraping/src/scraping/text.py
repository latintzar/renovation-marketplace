"""HTML → plain text extraction with graceful-degradation fallback (D9).

Three-tier:

1. :mod:`trafilatura` — readability-style, best for article bodies.
2. :mod:`bs4` — generic DOM walk with script/style stripped.
3. Regex — last-ditch tag stripper. Never raises.

Each tier catches ``ImportError`` and falls through, so the extractor
is always available even on hosts that lack trafilatura/bs4.

Bytes-level parity with the pre-migration ``shared.web.html_to_text``:
whitespace collapse, triple-newline → double, final strip. Tests lock
all three branches by forcing ``ImportError`` via monkeypatch.
"""
from __future__ import annotations

import re

__all__ = ["html_to_text"]


def html_to_text(html: str) -> str:
    """Return the readable plain text of an HTML document.

    Empty input returns ``""``. On every tier we prefer "some text"
    over raising; the regex fallback is deliberate — a degraded
    answer is still better than a 500 in a production pipeline.
    """

    if not html:
        return ""

    try:
        import trafilatura

        out = trafilatura.extract(
            html,
            include_tables=True,
            include_links=False,
            favor_recall=True,
            no_fallback=False,
        )
        if out:
            return out.strip()
    except ImportError:
        pass

    try:
        from bs4 import BeautifulSoup

        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "noscript", "iframe"]):
            tag.decompose()
        text = soup.get_text(separator="\n")
        return re.sub(r"\n{3,}", "\n\n", text).strip()
    except ImportError:
        pass

    text = re.sub(r"<[^>]+>", "", html)
    return re.sub(r"\s+\n", "\n", text).strip()
