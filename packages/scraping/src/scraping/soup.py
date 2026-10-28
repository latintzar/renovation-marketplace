"""BeautifulSoup wrapper — :func:`parse_soup` (D8).

lxml-backed ``parse_html`` (position-accurate, walker-camp) and
bs4-backed ``parse_soup`` (ergonomic, scraper-camp) coexist because
they serve different jobs; see ``design.md`` D8. This module keeps
the bs4 import in one place so the rest of the monorepo's
``from bs4 import BeautifulSoup`` ban holds.

``parse_soup(html)`` returns a plain :class:`BeautifulSoup` instance
using the stdlib ``html.parser`` backend. That parser is slower than
lxml but safer in the face of malformed HTML from scraping targets,
and it avoids dragging a separate lxml-for-bs4 chain at parse-time.
"""
from __future__ import annotations

from typing import Any

__all__ = ["parse_soup"]


def parse_soup(html: str) -> Any:
    """Parse ``html`` into a :class:`bs4.BeautifulSoup` tree.

    Typed as ``Any`` to keep ``bs4`` out of package-level type
    annotations (some hosts don't install it). The return is a real
    ``BeautifulSoup`` — callers can use ``.find_all``, ``.select``,
    ``.get_text`` freely.
    """

    from bs4 import BeautifulSoup

    return BeautifulSoup(html, "html.parser")
