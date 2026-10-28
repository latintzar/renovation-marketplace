# `scraping`

Shared web-scraping capability primitives: parse HTML/CSS, fetch pages (static + CDP browser), manage cache, rotate user agents, respect robots.txt, dismiss GDPR banners, keep a persistent browser alive.

After Phase 5 Wave 5, this package is **pure capability** — no site-specific adapters, no contractor-lead orchestration. Those scope-policy pieces live at `apps/scope/product/backend/scrapers/`. If the scope app were deleted, `packages/scraping` would still be useful to any other Leo app that needs to fetch/parse a page.

## Why this package exists

HTML, CSS, fetch orchestration, and anti-bot posture show up everywhere in the monorepo: walkers (dependency graph analysis), scrapers (Leo app + future apps), static-site tools (leo.casa sitemap), and tests. Consolidating them means every consumer uses the same tolerant parser, the same fetch-strategy router, the same UA pool, and the same robots.txt contract.

The repo's `.cursor/hooks/banned-imports.txt` actively prevents raw `from bs4 import BeautifulSoup`, `from playwright.async_api import async_playwright`, `httpx.AsyncClient(...)`, and friends outside `packages/` / `vendor/` — this package is their canonical home.

## Public API (47 symbols)

### Parsing

```python
from scraping import parse_html, iter_tags, tag_attr, tag_lineno, parse_srcset, is_external_url
from scraping import iter_css_refs, CssRef
from scraping import parse_soup, html_to_text  # bs4 + trafilatura wrappers
```

### Fetching

```python
from scraping import fetch, fetch_static, fetch_browser, fetch_many, extract_text
from scraping import cached_fetch, DEFAULT_CACHE_DIR
from scraping import FetchStrategy, JS_HOSTS, extend_js_hosts
from scraping import is_allowed, RobotsChecker  # robots.txt
```

### Browser + anti-bot

```python
from scraping import browser_page, browser_context, browser_page_sync, browser_context_sync
from scraping import persistent_browser
from scraping import dismiss_gdpr, dismiss_gdpr_async, GDPR_SELECTORS
from scraping import DEFAULT_VIEWPORT, CDP_DEFAULT_PORT
from scraping import USER_AGENTS, DESKTOP_USER_AGENTS, MOBILE_USER_AGENTS
from scraping import pick_user_agent, pick_desktop, pick_mobile
```

### Errors

```python
from scraping import ScrapingError, FetchError, BrowserUnavailable, RobotsDisallowed
```

## What moved out in Phase 5 Wave 5

| Scope-policy concern | New home |
|---|---|
| `scraping.adapters.habitissimo` | `scrapers.habitissimo` (`apps/scope/product/backend/scrapers/habitissimo/`) |
| `scraping.adapters.instagram` | `scrapers.instagram` (`apps/scope/product/backend/scrapers/instagram/`) |
| `scraping.adapters.houzz` | `scrapers.houzz` (`apps/scope/product/backend/scrapers/houzz/`) |
| `scraping.adapters.facebook` | `scrapers.facebook` (`apps/scope/product/backend/scrapers/facebook/`) |
| `scraping.directories` (`ContractorLead`, cross-platform `search`) | `scrapers.directories` |
| `scraping.instagram_scraper` (legacy IG scraper) | `scrapers.instagram_scraper` |
| `scraping.whatsapp_checker` | `scrapers.whatsapp_checker` |
| top-level `fb_expand_comments` re-export | `scrapers.fb_expand_comments` |

Scope code imports both layers:

```python
from scraping import fetch_browser, parse_html          # capability
from scrapers.habitissimo import refresh_session        # scope-policy
from scrapers import ContractorLead, search             # scope-orchestration
```

## Implementation

- `scraping.html` — backed by [`lxml`](https://lxml.de/). Chosen over `html.parser` for malformed-input leniency, over `BeautifulSoup` for speed (~20×) and accurate `sourceline` on every tag.
- `scraping.css` — backed by [`tinycss2`](https://doc.courtbouillon.org/tinycss2/). CSS Syntax Module Level 3 tokenizer; tolerant, preserves token positions, handles malformed declarations without raising.
- `scraping.fetch` — routes to static (`httpx`) vs browser (`playwright` via CDP) based on `JS_HOSTS` and caller-provided `FetchStrategy`.
- `scraping.browser` — persistent browser pool keyed by user-data-dir + UA; GDPR dismissal via `GDPR_SELECTORS` shared across all sites.
- `scraping.cache` — opt-in disk cache keyed by URL + strategy; callers pass a path under `DEFAULT_CACHE_DIR` or bring their own.
- `scraping.user_agents` — curated UA pool with `pick_*` helpers for device-class selection.
- `scraping.robots` — respectful `robots.txt` check with 24h cache; `is_allowed(url, ua)` is the single call site.

## Testing

```bash
cd /root/leo
PYTHONPATH="packages/scraping/src:packages/core/src" \
    /root/leo/apps/scope/product/backend/venv/bin/python3 \
    -m pytest packages/scraping/tests/
```

The `test_public_api.py` contract locks the 47-symbol surface and asserts that scope submodules (`adapters/`, `directories`, `instagram_scraper`, `whatsapp_checker`) are no longer importable from `scraping.*`. Scope-scraper tests live alongside the scope code at `apps/scope/product/backend/tests/scrapers/`.

## Changelog

- **Phase 5 Wave 5**: split. Site adapters (Habitissimo, Instagram, Houzz, Facebook), contractor-discovery orchestrator (`ContractorLead` + `search`), `fb_expand_comments` re-export, `instagram_scraper`, and `whatsapp_checker` all moved to `apps/scope/product/backend/scrapers/`. `packages/scraping` is now pure primitives. Three caller sites in the scope backend (`routes/landing_leads.py`, `routes/search_instagram.py`, `workflows/contractor_discovery.py`) were updated to import from `scrapers` for the scope-specific pieces; primitives still come from `scraping`.
- **Phase 5 Wave 2**: `domain.phone` / `domain.text` references replaced with `core.phone` / `core.text`.
- **Pre-Phase-5**: package consolidated from scattered `shared/browser.py`, `shared/web.py`, `tools/web_fetch.py` etc. into a single coherent capability layer (~40 callers codemodded).
