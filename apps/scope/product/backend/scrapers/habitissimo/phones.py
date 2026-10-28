"""Habitissimo phone reveal + modal parser.

Phone extraction from Habitissimo's AJAX "reveal phone" modal is a
three-strategy affair preserved from audit §1.7:

1. ``tel:`` anchor (``<a href="tel:+34...">``).
2. Known ``data-phone="..."`` attribute.
3. Regex over modal HTML (last resort).

:data:`HABITISSIMO_PROXY_PREFIX` is a known proxy-number band that
Habitissimo rewrites phones into for non-premium scrapers — filtered
out at the adapter boundary so consumers see only real numbers.

:data:`AJAX_JS` is the JavaScript snippet Playwright injects to
trigger the phone-reveal modal without clicking through the UI
(preserved from ``get_phones.py``).

Wave-9 scope: constants preserved; I/O functions are scaffolded.
"""
from __future__ import annotations

from typing import Optional

__all__ = [
    "HABITISSIMO_PROXY_PREFIX",
    "AJAX_JS",
    "reveal_phone",
    "extract_phone_from_modal_html",
]


HABITISSIMO_PROXY_PREFIX: str = "911"
"""Proxy-number band prefix. Habitissimo rewrites real phones to
``911XXXXXXX`` for non-premium scrapers; filter before surfacing."""


AJAX_JS: str = """
(() => {
  const form = new FormData();
  form.append("action", "habitissimo_phone");
  form.append("slug", "{slug}");
  return fetch("/ajax/phone", {method: "POST", body: form})
    .then(r => r.text());
})()
""".strip()
"""JS snippet for Playwright ``page.evaluate`` to trigger the phone-
reveal AJAX without UI clicks. Callers format ``{slug}`` before
evaluating."""


def extract_phone_from_modal_html(html: str) -> Optional[str]:
    """Parse a phone number out of Habitissimo's reveal-modal HTML.

    Three-strategy extraction (preserved from the pre-migration
    ``_habi_extract_phone_from_modal``):

    1. ``tel:`` anchor.
    2. ``data-phone`` attribute on any element.
    3. Loose ``+?\\d{9,11}`` regex.

    Returns ``None`` when no phone found **or** the extracted phone
    starts with :data:`HABITISSIMO_PROXY_PREFIX` (proxy number, not
    real).

    Pure function — safe to import and unit-test without any browser.
    """

    import re

    if not html:
        return None

    m = re.search(r'href=["\']tel:\s*([+\d\s\-()]+)["\']', html)
    if m:
        raw = _clean(m.group(1))
        return raw if not _is_proxy(raw) else None

    m = re.search(r'data-phone=["\']\s*([+\d\s\-()]+)["\']', html)
    if m:
        raw = _clean(m.group(1))
        return raw if not _is_proxy(raw) else None

    m = re.search(r"\+?\d[\d\s\-()]{8,14}", html)
    if m:
        raw = _clean(m.group(0))
        if len(raw) >= 9 and not _is_proxy(raw):
            return raw

    return None


def _clean(raw: str) -> str:
    """Strip whitespace / dashes / parens from a raw phone string."""

    import re

    return re.sub(r"[\s\-()]", "", raw or "")


def _is_proxy(phone: str) -> bool:
    """True if ``phone`` starts with :data:`HABITISSIMO_PROXY_PREFIX`
    after stripping a leading ``+34`` if present."""

    p = phone
    if p.startswith("+34"):
        p = p[3:]
    elif p.startswith("0034"):
        p = p[4:]
    elif p.startswith("34") and len(p) >= 11:
        p = p[2:]
    return p.startswith(HABITISSIMO_PROXY_PREFIX)


async def reveal_phone(slug: str) -> Optional[str]:
    """Reveal the phone for a Habitissimo company by slug.

    Wraps: load session → open browser page → inject cookies → trigger
    :data:`AJAX_JS` → parse with :func:`extract_phone_from_modal_html`.

    .. note::
       **Wave-9 scope**: stub. Full implementation in Phase 5. See
       ``internal/refactor/packages/scraping/design.md`` §D5.
    """

    raise NotImplementedError(
        "scrapers.habitissimo.phones.reveal_phone is scaffolded "
        "for Wave 9; full implementation in Phase 5."
    )
