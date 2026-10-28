"""
Instagram Phone Scraper
=======================

Finds tradespeople on Instagram by trade + city and extracts phone numbers.

Strategy:
  1. Google `site:instagram.com <trade> <city>` via Bright Data (10 queries,
     paginated with `start=` offsets) to collect profile URLs.
  2. For each unique username, fetch the Instagram profile page through Bright
     Data Web Unlocker (residential proxy) to get the rendered bio text.
  3. Extract phone numbers from:
     - Bio text (Spanish mobile: 6xx/7xx, and +34 prefixes)
     - Website field / linktree URLs (fetch one level deep)
  4. Deduplicate by username + phone.

Why Bright Data?
  Instagram blocks scrapers heavily. Residential proxies bypass their bot
  detection well enough to read public profile pages. This is the same
  infrastructure we already use for Facebook group searches.

Cost:
  ~20-30 Bright Data requests per city+trade run. At ~$0.001/req = <$0.03/run.
  Always logs actual request count so you can track spend.

Usage (standalone test):
  PYTHONPATH=apps/scope/product/backend python3 -m scrapers.instagram_scraper --trade fontanero --city Málaga
"""

from __future__ import annotations

import asyncio
import logging
import re
import sys
import urllib.parse
from typing import Any

from core import http_client_sync
from core.phone import normalize as _norm_phone
from scraping import parse_html

logger = logging.getLogger(__name__)

# ─── Config ──────────────────────────────────────────────────────────────────

_BD_TIMEOUT = 30  # seconds per Bright Data request
_SEARCH_QUERIES_PER_TRADE = 10  # paginated Google queries (each returns ~10 urls)
_MAX_PROFILE_FETCHES = 60       # max Instagram profiles to fetch per run
_PHONE_REGEX = re.compile(
    r"""(?x)
    (?:\+34\s?|0034\s?|34\s?)?   # optional Spain prefix
    (?:6\d{2}|7[0-9]\d)          # mobile: 6xx or 7[0-9]x
    [\s.\-]?
    \d{3}
    [\s.\-]?
    \d{3}
    """
)
_INSTAGRAM_PROFILE_RE = re.compile(
    r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]+)(?:/[^?]*)?"
)

# Usernames that are never real contractor profiles (paths / help pages)
IG_USERNAME_SKIP = frozenset({
    "p", "explore", "reels", "stories", "tv", "accounts", "about", "legal",
    "help", "directory", "developer", "press",
})

# Junk captures from snippets (e.g. "instagram: https://...")
IG_USERNAME_REJECT = frozenset({
    "https", "http", "www", "com", "html", "php", "null", "none",
})


def instagram_handle_from_bio(bio: str | None) -> str | None:
    """
    Best-effort Instagram @handle from a Google snippet / Wallapop line / bio string.
    Used to backfill profile_url for PHONE-only scraper rows.
    """
    if not bio:
        return None
    text = bio.strip()
    if not text:
        return None
    # instagram.com/username (skip help/about/reels root paths)
    m = re.search(
        r"instagram\.com/(?!help\b|about\b|legal\b|reels\b|p\b|stories\b)([A-Za-z0-9._]{2,30})(?=[/?#\"'\\s<]|$)",
        text,
        re.I,
    )
    if m:
        u = m.group(1).strip().strip(".")
        if u and not u.isdigit() and u.lower() not in IG_USERNAME_SKIP | IG_USERNAME_REJECT:
            return u
    # "instagram: handle" — must not be a URL (snippets often have "Instagram: https://help…")
    m = re.search(
        r"instagram\s*:\s*(?!https?://)\s*@?([A-Za-z0-9._]{2,30})\b",
        text,
        re.I,
    )
    if m:
        u = m.group(1).strip(".")
        if u and not u.isdigit() and u.lower() not in IG_USERNAME_SKIP | IG_USERNAME_REJECT:
            return u
    # "IG @handle" / "ig: handle"
    m = re.search(r"\big\s*:\s*(?!https?://)\s*@?([A-Za-z0-9._]{2,30})\b", text, re.I)
    if m:
        u = m.group(1).strip(".")
        if u and not u.isdigit() and u.lower() not in IG_USERNAME_SKIP | IG_USERNAME_REJECT:
            return u
    # Instagram title pattern: "… (@username)"
    m = re.search(r"\(@\s*([A-Za-z0-9._]{2,30})\s*\)", text)
    if m:
        u = m.group(1).strip(".")
        if u and not u.isdigit() and u.lower() not in IG_USERNAME_SKIP | IG_USERNAME_REJECT:
            return u
    return None


# ─── Bright Data helpers (reused from verification.py pattern) ────────────────

def _load_bd_key() -> str:
    import os
    key = os.environ.get("BRIGHT_DATA_API_KEY", "")
    if not key:
        try:
            for line in open("/root/leo/.env.local"):
                line = line.strip()
                if line.startswith("BRIGHT_DATA_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
                    break
        except OSError:
            pass
    return key


def _google_instagram_search(query: str, start: int, bd_key: str, num: int = 10) -> list[str]:
    """One paginated Google search for tradespeople with Instagram presence.

    Modern Google returns a JS-rendered page where result URLs are encoded
    in multiple ways. We use three extraction strategies in order:

    1. BeautifulSoup <a href> + /url?q= (classic layout — still works sometimes)
    2. Regex on raw HTML for any https://instagram.com/<username> pattern
    3. Extract phone numbers from snippet text directly (most reliable — phones
       appear visibly in the snippet HTML even when IG profile URLs don't)

    Returns list of Instagram profile URLs AND synthetic phone rows
    (format: ``PHONE:<digits>|BIO:<snippet>[|IG:<username>]``) where ``IG`` is set
    when an instagram.com link appeared in the **same** Google result block as the phone.
    """
    google_url = (
        f"https://www.google.com/search?"
        f"q={urllib.parse.quote(query)}&num={num}&start={start}&hl=es&gl=es&cr=countryES"
    )
    try:
        with http_client_sync(timeout=_BD_TIMEOUT) as client:
            resp = client.post(
                "https://api.brightdata.com/request",
                headers={"Authorization": f"Bearer {bd_key}", "Content-Type": "application/json"},
                json={"zone": "mcp_unlocker", "url": google_url, "method": "GET", "format": "raw"},
            )
        if resp.status_code != 200:
            logger.warning("BD Google search returned %d for query=%r start=%d", resp.status_code, query[:60], start)
            return []

        html = resp.text
        urls: list[str] = []

        # Strategy 1: classic Google /url?q= anchor links
        soup = parse_html(html)
        for a in soup.find_all("a", href=True):
            href = a["href"]
            if href.startswith("/url?q="):
                decoded = urllib.parse.unquote(href[7:].split("&")[0])
                if "instagram.com/" in decoded:
                    urls.append(decoded)
            elif "instagram.com/" in href and href.startswith("http"):
                urls.append(href)

        # Strategy 2: raw regex for instagram.com/username anywhere in HTML
        # Handles JSON-escaped URLs like "https:\/\/instagram.com\/username" too
        raw_ig = re.findall(
            r'https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{3,30})(?=[/"?\\\\<\s])',
            html,
        )
        for uname in raw_ig:
            urls.append(f"https://www.instagram.com/{uname}/")

        # Strategy 3: per Google result block — pair phones with Instagram URLs from the *same* block
        result_blocks = soup.find_all("div", class_="MjjYud")
        if not result_blocks:
            result_blocks = (
                soup.find_all(attrs={"data-snf": True}) or
                soup.find_all(class_=re.compile(r"^(VwiC3b|IsZvec|aCOpRe|r0bn4c)$"))
            )

        seen_phones_in_search: set[str] = set()
        for block in result_blocks:
            try:
                block_html = str(block)
                block_text = block.get_text(" ", strip=True)
            except Exception:
                continue
            if not block_text or len(block_text) < 8:
                continue

            ig_in_block = re.findall(
                r"https?://(?:www\.)?instagram\.com/([A-Za-z0-9._]{2,30})(?=[/?#\"'\\s<&]|$)",
                block_html,
                flags=re.I,
            )
            ig_ordered: list[str] = []
            for raw_u in ig_in_block:
                u = raw_u.strip("/")
                ul = u.lower()
                if not u or ul in IG_USERNAME_SKIP or u.isdigit():
                    continue
                if u not in ig_ordered:
                    ig_ordered.append(u)

            phone_matches = list(dict.fromkeys(_PHONE_REGEX.findall(block_text)))
            for phone in phone_matches:
                phone_clean = _norm_phone(phone)
                if len(phone_clean) < 9 or phone_clean in seen_phones_in_search:
                    continue
                seen_phones_in_search.add(phone_clean)
                bio_hint = re.sub(r"\s+", " ", block_text[:240]).strip()[:180].replace("|", " ")
                ig_pick = ig_ordered[0] if ig_ordered else ""
                if not ig_pick:
                    ig_pick = instagram_handle_from_bio(block_text) or ""
                row = f"PHONE:{phone_clean}|BIO:{bio_hint}"
                if ig_pick:
                    row += f"|IG:{ig_pick}"
                urls.append(row)

        n_syn = sum(1 for u in urls if isinstance(u, str) and u.startswith("PHONE:"))
        logger.debug(
            "BD Google search q=%r start=%d → %d entries (synthetic phones in this page: %d)",
            query[:60], start, len(urls), n_syn,
        )
        return urls
    except Exception as e:
        logger.warning("BD Google search failed: %s", e)
        return []


def _fetch_instagram_profile(username: str, bd_key: str) -> dict[str, Any]:
    """Fetch an Instagram profile page and extract bio + phone. Returns dict."""
    url = f"https://www.instagram.com/{username}/"
    try:
        with http_client_sync(timeout=_BD_TIMEOUT) as client:
            resp = client.post(
                "https://api.brightdata.com/request",
                headers={"Authorization": f"Bearer {bd_key}", "Content-Type": "application/json"},
                json={
                    "zone": "mcp_unlocker",
                    "url": url,
                    "method": "GET",
                    "format": "raw",
                    "headers": {
                        "Accept-Language": "es-ES,es;q=0.9",
                        "User-Agent": (
                            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
                            "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
                        ),
                    },
                },
            )
        if resp.status_code != 200:
            logger.debug("Instagram profile %s → HTTP %d", username, resp.status_code)
            return {}

        html = resp.text

        # Extract bio from Instagram's JSON-LD or meta tags (less JS-heavy)
        bio = _extract_bio_from_html(html)
        phone = _extract_phone(bio) if bio else None
        display_name = _extract_display_name(html)
        website = _extract_website(html)

        # If no phone in bio, try website (linktree etc.)
        phone_source = "bio" if phone else None
        if not phone and website:
            phone = _try_fetch_website_phone(website, bd_key)
            if phone:
                phone_source = "website"

        logger.debug(
            "Instagram @%s | bio_len=%d | phone=%s | source=%s",
            username, len(bio or ""), phone or "—", phone_source or "none",
        )

        return {
            "username": username,
            "name": display_name or username,
            "bio": (bio or "")[:300],
            "phone": _normalise_phone(phone) if phone else None,
            "phone_source": phone_source,
            "website": website,
            "url": url,
            "profile_url": url,
        }
    except Exception as e:
        logger.warning("Instagram profile fetch failed @%s: %s", username, e)
        return {}


def _extract_bio_from_html(html: str) -> str:
    """Extract bio text from Instagram page HTML. Tries meta description first."""
    # Meta description often contains bio for public profiles
    m = re.search(r'<meta\s+(?:[^>]*?)name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.I | re.S)
    if m:
        return m.group(1)
    # Try og:description
    m = re.search(r'<meta\s+(?:[^>]*?)property=["\']og:description["\']\s+content=["\'](.*?)["\']', html, re.I | re.S)
    if m:
        return m.group(1)
    # JSON blob in page: "biography":"..."
    m = re.search(r'"biography"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if m:
        return m.group(1).encode().decode("unicode_escape", errors="replace")
    return ""


def _extract_display_name(html: str) -> str:
    m = re.search(r'"full_name"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if m:
        return m.group(1)
    m = re.search(r'<title>([^<]+)</title>', html)
    if m:
        return m.group(1).split("•")[0].strip().split("(")[0].strip()
    return ""


def _extract_website(html: str) -> str:
    m = re.search(r'"external_url"\s*:\s*"((?:[^"\\]|\\.)*)"', html)
    if m:
        url = m.group(1)
        if url and url != "null":
            return url
    return ""


def _extract_phone(text: str) -> str | None:
    """Extract first Spanish mobile phone number from text."""
    if not text:
        return None
    m = _PHONE_REGEX.search(text)
    return m.group(0).strip() if m else None


def _normalise_phone(raw: str) -> str:
    """Normalise to +34XXXXXXXXX format."""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0034"):
        digits = digits[4:]
    elif digits.startswith("34") and len(digits) == 11:
        digits = digits[2:]
    if len(digits) == 9 and digits[0] in ("6", "7"):
        return f"+34{digits}"
    if len(digits) == 11 and digits.startswith("34"):
        return f"+{digits}"
    return f"+34{digits}" if digits else raw


def _try_fetch_website_phone(url: str, bd_key: str) -> str | None:
    """Fetch a linked website (linktree, etc.) and look for a phone number."""
    if not url or not url.startswith("http"):
        return None
    try:
        with http_client_sync(timeout=10, follow_redirects=True) as client:
            resp = client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; Leo/1.0)"})
        if resp.status_code == 200:
            return _extract_phone(resp.text)
    except Exception:
        pass
    return None


# ─── Main scrape function ─────────────────────────────────────────────────────

async def scrape_instagram_profiles(
    trade: str,
    city: str,
    parallelize: bool = True,
) -> dict[str, Any]:
    """
    Search Instagram for tradespeople profiles by trade + city.
    Returns:
      {
        "total_profiles": int,
        "profiles_with_phone": int,
        "profiles": [...],
        "proxies_used": int,
        "queries_run": int,
      }
    """
    bd_key = _load_bd_key()
    if not bd_key:
        logger.error("BRIGHT_DATA_API_KEY not set — cannot scrape Instagram")
        return {"total_profiles": 0, "profiles_with_phone": 0, "profiles": [], "proxies_used": 0, "queries_run": 0}

    # Build search queries: main + synonyms
    trade_lower = trade.lower().strip()
    city_title = city.strip()

    queries = [
        # Mix site: and non-site: queries — Google JS layout picks up both
        f'site:instagram.com "{trade_lower}" "{city_title}"',
        f'site:instagram.com {trade_lower} {city_title}',
        f'{trade_lower} {city_title} instagram.com telefono',
        f'{trade_lower} {city_title} instagram.com movil presupuesto',
        f'site:instagram.com {trade_lower} {city_title} presupuesto',
    ]

    logger.info("Instagram scrape start | trade=%s city=%s queries=%d", trade, city, len(queries))

    # Step 1: Collect profile URLs (paginated Google searches in a thread pool)
    all_urls: list[str] = []
    bd_requests = 0

    def _run_search(q: str, start: int) -> list[str]:
        nonlocal bd_requests
        bd_requests += 1
        return _google_instagram_search(q, start, bd_key)

    loop = asyncio.get_event_loop()
    search_tasks = []
    for q in queries:
        for start in [0, 10, 20]:  # 3 pages per query = up to 30 results each
            search_tasks.append((q, start))

    if parallelize:
        # Run searches concurrently (up to 5 at a time)
        sem = asyncio.Semaphore(5)

        async def _bounded_search(q: str, start: int) -> list[str]:
            async with sem:
                return await loop.run_in_executor(None, _run_search, q, start)

        results = await asyncio.gather(*[_bounded_search(q, s) for q, s in search_tasks])
        for r in results:
            all_urls.extend(r)
    else:
        for q, s in search_tasks:
            all_urls.extend(_run_search(q, s))

    # Extract unique usernames (skip reserved words / non-profile paths)
    # Also extract synthetic PHONE: entries that bypass profile fetch
    seen_usernames: set[str] = set()
    direct_phones: list[dict] = []  # phones found directly in Google snippets

    def _parse_synthetic_phone_row(entry: str) -> dict[str, str] | None:
        if not entry.startswith("PHONE:"):
            return None
        ig_user = ""
        body = entry
        if "|IG:" in entry:
            body, ig_tail = entry.rsplit("|IG:", 1)
            ig_user = ig_tail.strip().lstrip("@").rstrip("/")
        bio = ""
        if "|BIO:" in body:
            left, bio = body.split("|BIO:", 1)
            phone_raw = left[len("PHONE:") :].strip()
        else:
            phone_raw = body[len("PHONE:") :].split("|")[0].strip()
        phone_clean = _norm_phone(phone_raw)
        if len(phone_clean) < 9:
            return None
        return {"phone": phone_clean, "bio": bio.replace("|", " "), "ig": ig_user}

    for entry in all_urls:
        if entry.startswith("PHONE:"):
            parsed = _parse_synthetic_phone_row(entry)
            if not parsed:
                continue
            phone = parsed["phone"]
            bio = parsed["bio"]
            ig_user = parsed["ig"]
            if not ig_user:
                ig_user = instagram_handle_from_bio(bio) or ""
            profile_url = f"https://www.instagram.com/{ig_user}/" if ig_user else ""
            display_name = f"@{ig_user}" if ig_user else ""
            direct_phones.append({
                "username": ig_user or f"google_snippet_{phone[-4:]}",
                "phone": phone,
                "name": display_name,
                "bio": bio,
                "profile_url": profile_url,
                "website": "",
                "followers": "",
                "source_query": "",
            })
        else:
            m = _INSTAGRAM_PROFILE_RE.match(entry)
            if m:
                uname = m.group(1).lower().rstrip("/")
                if uname and uname not in IG_USERNAME_SKIP and "/" not in uname:
                    seen_usernames.add(uname)

    usernames = list(seen_usernames)[:_MAX_PROFILE_FETCHES]
    logger.info(
        "Instagram scrape | search phase done | unique_profiles=%d direct_phones=%d bd_search_requests=%d",
        len(usernames), len(direct_phones), bd_requests,
    )

    if not usernames and not direct_phones:
        logger.warning("Instagram scrape: no profiles found for %s in %s", trade, city)
        return {"total_profiles": 0, "profiles_with_phone": 0, "profiles": [], "proxies_used": bd_requests, "queries_run": len(search_tasks)}

    # Step 2: Fetch each profile (concurrently, up to 8 at a time)
    profiles: list[dict] = []

    if parallelize:
        fetch_sem = asyncio.Semaphore(8)

        async def _bounded_fetch(uname: str) -> dict:
            nonlocal bd_requests
            async with fetch_sem:
                result = await loop.run_in_executor(None, _fetch_instagram_profile, uname, bd_key)
                bd_requests += 1
                return result

        fetched = await asyncio.gather(*[_bounded_fetch(u) for u in usernames])
        profiles = [p for p in fetched if p]
    else:
        for uname in usernames:
            result = _fetch_instagram_profile(uname, bd_key)
            bd_requests += 1
            if result:
                profiles.append(result)

    # Merge direct phone entries (from snippets) with fetched IG profiles
    # Direct phone entries already have phone set; profiles may or may not
    profiles_combined = direct_phones + profiles

    # Deduplicate by phone
    seen_phones: set[str] = set()
    deduped: list[dict] = []
    for p in profiles_combined:
        phone = p.get("phone")
        norm = _norm_phone(phone or "")
        if norm:
            if norm not in seen_phones:
                seen_phones.add(norm)
                deduped.append(p)
        else:
            deduped.append(p)

    with_phone = [p for p in deduped if p.get("phone")]

    logger.info(
        "Instagram scrape done | total=%d with_phone=%d bd_requests=%d",
        len(deduped), len(with_phone), bd_requests,
    )

    return {
        "total_profiles": len(deduped),
        "profiles_with_phone": len(with_phone),
        "profiles": deduped,
        "proxies_used": bd_requests,
        "queries_run": len(search_tasks),
    }


# ─── CLI ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    from core import bootstrap_init as _shared_init
    _shared_init()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stdout,
    )

    parser = argparse.ArgumentParser(description="Instagram phone scraper")
    parser.add_argument("--trade", default="fontanero", help="Trade type")
    parser.add_argument("--city", default="Málaga", help="City")
    args = parser.parse_args()

    result = asyncio.run(scrape_instagram_profiles(args.trade, args.city))
    print(f"\n✓ Found {result['total_profiles']} profiles, {result['profiles_with_phone']} with phones")
    print(f"  Bright Data requests used: {result['proxies_used']}")
    for p in result["profiles"]:
        phone_str = p.get("phone") or "—"
        print(f"  @{p['username']:30} {phone_str:15} {p.get('bio','')[:60]}")
