"""Lock the public surface of :mod:`scraping`.

Post Phase 5 Wave 5: site adapters (``habitissimo``, ``instagram``,
``houzz``, ``facebook``) and the contractor-discovery orchestrator
(``ContractorLead`` + cross-platform ``search`` + ``fb_expand_comments``)
live in ``apps/scope/product/backend/scrapers/``. ``packages/scraping`` is pure
primitives: parse, fetch, browser, cache, robots, user-agents.
"""
from __future__ import annotations

import scraping


EXPECTED_ALL: frozenset[str] = frozenset(
    {
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
    }
)


def test_all_matches_expected() -> None:
    assert frozenset(scraping.__all__) == EXPECTED_ALL


def test_all_symbols_importable() -> None:
    for symbol in scraping.__all__:
        assert hasattr(scraping, symbol), f"missing: {symbol}"


def test_adapters_not_in_top_level() -> None:
    """Site adapters + scope orchestration live in apps/scope/product/backend/scrapers/."""

    banned = {
        "habitissimo", "instagram", "houzz", "facebook", "adapters",
        "ContractorLead", "search", "fb_expand_comments",
        "directories", "instagram_scraper", "whatsapp_checker",
    }
    for name in banned:
        assert name not in scraping.__all__, (
            f"{name!r} should live in apps/scope/product/backend/scrapers/ — "
            "packages/scraping is capability primitives only post-Wave 5"
        )


def test_scope_submodules_not_in_scraping() -> None:
    """Scope submodules were physically moved — confirm they're gone."""
    import importlib
    for name in (
        "scraping.adapters",
        "scraping.directories",
        "scraping.instagram_scraper",
        "scraping.whatsapp_checker",
    ):
        try:
            importlib.import_module(name)
        except ImportError:
            continue  # good — it moved
        else:
            raise AssertionError(
                f"{name} still importable from packages/scraping — "
                "it should live in apps/scope/product/backend/scrapers/"
            )
