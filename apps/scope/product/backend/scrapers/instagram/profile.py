"""IG profile HTML parse (scaffolded with pure-logic helpers).

Mobile-UA fetch (audit §1.10 I3) returns simpler SSR HTML — bio,
website, phone links are parseable without JS execution. This
module exposes the pure parser (:func:`extract_profile_fields`) so
tests can feed saved HTML fixtures without any network.
"""
from __future__ import annotations

import re
from typing import Any, Optional

__all__ = ["extract_profile_fields", "fetch_profile"]


_RE_BIO = re.compile(
    r'"biography"\s*:\s*"([^"]*)"',
    flags=re.DOTALL,
)
_RE_EXTERNAL_URL = re.compile(r'"external_url"\s*:\s*"([^"]*)"')
_RE_FULL_NAME = re.compile(r'"full_name"\s*:\s*"([^"]*)"')
_RE_USERNAME = re.compile(r'"username"\s*:\s*"([^"]*)"')
_RE_PHONE_ANY = re.compile(r"(\+?\d[\d\s\-()]{7,14})")


def extract_profile_fields(html: str) -> dict[str, Any]:
    """Parse the bio, website, name, and phones out of IG profile HTML.

    Pure function — unit-tested with saved HTML fixtures.

    Returns a dict with keys:

    * ``username`` — IG handle (``""`` if unparseable).
    * ``full_name`` — display name (may be ``""``).
    * ``biography`` — bio text (possibly with embedded newlines as ``\\n``).
    * ``external_url`` — linked website URL (``""`` if absent).
    * ``phones`` — list of phone strings extracted from the bio.
        Deduplicated in-order. Empty list if no matches.
    """

    if not html:
        return {
            "username": "",
            "full_name": "",
            "biography": "",
            "external_url": "",
            "phones": [],
        }

    username = _first_match(_RE_USERNAME, html)
    full_name = _first_match(_RE_FULL_NAME, html)
    biography = _first_match(_RE_BIO, html).encode("utf-8").decode(
        "unicode_escape", errors="replace"
    ) if _first_match(_RE_BIO, html) else ""
    external_url = _first_match(_RE_EXTERNAL_URL, html).encode("utf-8").decode(
        "unicode_escape", errors="replace"
    ) if _first_match(_RE_EXTERNAL_URL, html) else ""

    phones: list[str] = []
    seen: set[str] = set()
    for match in _RE_PHONE_ANY.finditer(biography):
        raw = match.group(1).strip()
        if raw and raw not in seen:
            seen.add(raw)
            phones.append(raw)

    return {
        "username": username,
        "full_name": full_name,
        "biography": biography,
        "external_url": external_url,
        "phones": phones,
    }


def _first_match(pattern: re.Pattern[str], text: str) -> str:
    m = pattern.search(text)
    return m.group(1) if m else ""


async def fetch_profile(username: str) -> Optional[dict[str, Any]]:
    """Fetch an IG profile by username and return extracted fields.

    .. note::
       **Wave-9 scope**: stub returning ``None``. Full implementation
       uses :func:`scraping.fetch_static` with ``user_agent=pick_mobile()``
       then runs :func:`extract_profile_fields`.
    """

    return None
