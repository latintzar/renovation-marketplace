# `scrapers` — scope-app site scrapers + contractor discovery

Every site-specific scraping concern the scope app needs: **Habitissimo** session refresh + phone reveal + RFQ blast, **Instagram** directory + profile import, **Houzz** directory search, **Facebook** group monitoring + comment expansion, cross-platform **contractor-lead** discovery, and legacy one-offs (`instagram_scraper`, `whatsapp_checker`).

Lives at `apps/scope/product/backend/scrapers/` (moved from `packages/scraping/src/scraping/adapters/` + siblings in Phase 5 Wave 5). Reached via `from scrapers import ...` — the scope backend puts `apps/scope/product/backend/` on `PYTHONPATH` so the import resolves.

## Pairing with `packages/scraping`

`scrapers` describes *what the scope app scrapes and how it shapes contractor leads*. `packages/scraping` provides the generic capability primitives — `fetch_browser`, `parse_html`, `persistent_browser`, `USER_AGENTS`, `dismiss_gdpr`, etc. Scope code imports both:

```python
from scraping import fetch_browser, parse_html, USER_AGENTS    # generic primitives
from scrapers.habitissimo import refresh_session, reveal_phone  # scope site-adapter
from scrapers import ContractorLead, search                     # scope orchestrator
```

The scope-vanishes test: if the scope app were deleted tomorrow, `scrapers` goes with it, but `packages/scraping` still works for any other Leo app that needs to fetch/parse a web page.

## Layout

```
apps/scope/product/backend/scrapers/
  __init__.py              # re-exports: ContractorLead, search, fb_expand_comments
  directories.py           # cross-platform contractor orchestrator + dedup
  instagram_scraper.py     # legacy Bright Data Instagram phone scraper
  whatsapp_checker.py      # WhatsApp Web phone-validity pinger (VNC browser)
  habitissimo/
    __init__.py            # session + phones + blast + search re-exports
    session.py             # cookie refresh + session management
    phones.py              # modal phone reveal via AJAX
    blast.py               # RFQ submission
    search.py              # directory listing + search
  instagram/
    __init__.py            # profile + search + scraper re-exports
    profile.py             # profile page extraction
    search.py              # Google site:instagram.com search
    scraper.py             # adapter-shaped ContractorLead producer
  houzz/
    __init__.py
    search.py              # directory search adapter
  facebook/
    __init__.py            # expand_comments + capture_graphql re-exports
    expand.py              # "see more comments" expansion
    groups.py              # group-level GraphQL capture
```

## Canonical imports

### Cross-platform discovery (the scope flow)

```python
from scrapers import ContractorLead, search
leads = await search(trade="fontanero", city="Málaga", platforms=["habitissimo", "instagram"])
```

### Site-specific entry points

```python
from scrapers.habitissimo import (
    refresh_session, get_session,
    reveal_phone, AJAX_JS, HABITISSIMO_PROXY_PREFIX,
    submit_rfq, build_submissions,
    list_companies, search,
)
from scrapers.instagram import (
    fetch_profile, extract_profile_fields,
    google_search, IG_USERNAME_SKIP,
    search,
)
from scrapers.houzz import build_query, search
from scrapers.facebook import (
    expand_comments, FB_MORE_SELECTORS,
    capture_graphql,
)
```

### Legacy one-offs

```python
from scrapers.instagram_scraper import scrape_instagram_profiles, instagram_handle_from_bio
from scrapers.whatsapp_checker import check_number, check_bulk
```

### Convenience top-level re-exports

```python
from scrapers import fb_expand_comments   # == scrapers.facebook.expand_comments
```

## Callers (production)

| Caller | What it imports |
|---|---|
| `apps/scope/product/backend/routes/landing_leads.py` | `scrapers.whatsapp_checker.check_number` — WA validity guard before lead ingest. |
| `apps/scope/product/backend/routes/search_instagram.py` | `scrapers.instagram_scraper.scrape_instagram_profiles` — profile-import API. |
| `apps/scope/product/backend/workflows/contractor_discovery.py` | `scrapers.whatsapp_checker.check_bulk` + `scrapers.fb_expand_comments` — contractor discovery orchestration. |
| `internal/scripts/habitissimo-growth-hack/find_prospects.py` | `scrapers.instagram_scraper.*` — one-off growth script (adds `apps/scope/product/backend/` to `sys.path` itself). |

## Testing

```bash
cd /root/leo/apps/scope/product/backend
./venv/bin/python3 -m pytest tests/scrapers/
```

The existing `conftest.py` provides `simple_html` and `ig_profile_html` fixtures. No Playwright / network; adapters that need those mock them locally.

## Open tech-debt: stranded `packages/messaging` pricing tool

The agent-tool wrapper `packages/messaging/src/messaging/leo_agent/tools/pricing.py` imports from `pricing.*` (which resolves via scope backend's `PYTHONPATH`). That tool file itself is scope-specific and will migrate to `apps/scope/product/backend/messaging/` in Phase 5 Wave 6 (messaging split + agent-framework protocol).

## Changelog

- **Phase 5 Wave 5**: created. All site adapters (Habitissimo, Instagram, Houzz, Facebook), the cross-platform contractor-discovery orchestrator (`ContractorLead` + `search`), the legacy `instagram_scraper` + `whatsapp_checker` modules, and the `fb_expand_comments` re-export moved here from `packages/scraping/`. The `adapters/` nesting was flattened — site modules now sit one level deeper (`scrapers.habitissimo` vs old `scraping.adapters.habitissimo`).
