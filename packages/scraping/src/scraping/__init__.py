"""``@scope/scraping`` — web-scraping capability primitives.

Shared building blocks for any Leo app that needs to fetch, parse, or
render a web page. Site-specific adapters (Habitissimo, Instagram,
Houzz, Facebook) and the contractor-discovery orchestrator
(``ContractorLead`` + cross-platform ``search``) moved to
``apps/scope/product/backend/scrapers/`` in Phase 5 Wave 5 — see that
directory's README for scope-side usage.

Three concern groups sit behind one package:

1. **Parsing** — ``lxml`` (:func:`parse_html`, :func:`iter_tags`,
   :func:`tag_attr`, :func:`tag_lineno`, :func:`tag_text`,
   :func:`parse_srcset`, :func:`is_external_url`, :class:`ParsedHtml`,
   :class:`Tag`); ``tinycss2`` (:func:`iter_css_refs`, :class:`CssRef`);
   ``bs4`` (:func:`parse_soup` — the one sanctioned ``BeautifulSoup``
   factory); text extraction (:func:`html_to_text`).

2. **Fetching** — static (:func:`fetch_static`), CDP-first browser
   (:func:`fetch_browser`), auto-routed (:func:`fetch`,
   :class:`FetchStrategy`, :data:`JS_HOSTS`, :func:`extend_js_hosts`),
   batch (:func:`fetch_many`), one-shot text (:func:`extract_text`),
   opt-in disk cache (:func:`cached_fetch`). robots.txt support
   through :func:`is_allowed` / :class:`RobotsChecker`.

3. **Browser + anti-bot posture** — :func:`browser_page`,
   :func:`browser_context`, sync variants, GDPR dismissal
   (:func:`dismiss_gdpr`, :func:`dismiss_gdpr_async`,
   :data:`GDPR_SELECTORS`), viewport (:data:`DEFAULT_VIEWPORT`),
   canonical UA pool (:data:`USER_AGENTS`, :data:`DESKTOP_USER_AGENTS`,
   :data:`MOBILE_USER_AGENTS`, :func:`pick_user_agent`,
   :func:`pick_desktop`, :func:`pick_mobile`).

4. **Errors** — :class:`ScrapingError`, :class:`FetchError`,
   :class:`BrowserUnavailable`, :class:`RobotsDisallowed`.

Packages MAY import ``core``, ``httpx``, ``lxml``, ``tinycss2``,
``beautifulsoup4``, ``trafilatura``, ``playwright``, ``scrapling``.
Packages MUST NOT import ``fulltext``, ``messaging``, ``storage``,
``voice``, ``payments``, ``brand``, or any ``apps.*`` sibling.
"""
from __future__ import annotations

from .browser import (
    DEFAULT_VIEWPORT,
    GDPR_SELECTORS,
    CDP_DEFAULT_PORT,
    browser_context,
    browser_context_sync,
    browser_page,
    browser_page_sync,
    dismiss_gdpr,
    dismiss_gdpr_async,
    persistent_browser,
)
from .cache import DEFAULT_CACHE_DIR, cache_path, cached_fetch
from .css import CssRef, iter_css_refs
from .errors import (
    BrowserUnavailable,
    FetchError,
    RobotsDisallowed,
    ScrapingError,
)
from .fetch import (
    JS_HOSTS,
    FetchStrategy,
    extend_js_hosts,
    extract_text,
    fetch,
    fetch_browser,
    fetch_many,
    fetch_static,
)
from .html import (
    ParsedHtml,
    Tag,
    is_external_url,
    iter_tags,
    parse_html,
    parse_srcset,
    tag_attr,
    tag_lineno,
    tag_text,
)
from .robots import RobotsChecker, is_allowed
from .soup import parse_soup
from .text import html_to_text
from .user_agents import (
    DESKTOP_USER_AGENTS,
    MOBILE_USER_AGENTS,
    USER_AGENTS,
    pick_desktop,
    pick_mobile,
    pick_user_agent,
)

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
    "CssRef",
    "iter_css_refs",
    "parse_soup",
    "html_to_text",
    "FetchStrategy",
    "JS_HOSTS",
    "extend_js_hosts",
    "fetch",
    "fetch_static",
    "fetch_browser",
    "fetch_many",
    "extract_text",
    "cached_fetch",
    "cache_path",
    "DEFAULT_CACHE_DIR",
    "browser_page",
    "browser_context",
    "browser_page_sync",
    "browser_context_sync",
    "dismiss_gdpr",
    "dismiss_gdpr_async",
    "persistent_browser",
    "GDPR_SELECTORS",
    "DEFAULT_VIEWPORT",
    "CDP_DEFAULT_PORT",
    "USER_AGENTS",
    "DESKTOP_USER_AGENTS",
    "MOBILE_USER_AGENTS",
    "pick_user_agent",
    "pick_desktop",
    "pick_mobile",
    "is_allowed",
    "RobotsChecker",
    "ScrapingError",
    "FetchError",
    "BrowserUnavailable",
    "RobotsDisallowed",
]
