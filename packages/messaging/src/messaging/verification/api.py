"""Verification & trust-signal utilities (Spanish-market focused).

Stateless functions for verifying tradesperson identity and aggregating
trust signals. Originally extracted from ``routes/profile_import.py`` to
break the inverted dependency where ``leo_agent/hermes_tools.py`` was
importing from a route file; now a full resident of :mod:`messaging.verification`
so the dependency arrow points one way — ``routes/`` ──> ``packages/`` and never
the reverse.

Post-migration dependency graph (all one-way):

::

    apps/scope/product/backend/routes/profile_import.py ──> messaging.verification.api
    apps/scope/product/backend/records/dossier.py       ──> messaging.verification.api
    apps/scope/product/backend/agent/tools/discovery.py ──> messaging.verification.api
    messaging.verification.api                  ──> messaging.verification.types

Data contracts (:class:`~messaging.verification.types.ProfileResult`,
:class:`~messaging.verification.types.TrustSignals`,
:class:`~messaging.verification.types.Credential`) live in
:mod:`~.types`.

Search architecture
-------------------
All internet searches go through one of two engines:

  SearXNG (fast checks — NIF/REA/reviews)
      Port 8888, serialized with 1.5s min interval.
      Used for ≤5 cheap queries per profile (NIF validation, review aggregator checks).
      Never used for FB/forum social proof — too slow at volume.

  Bright Data Web Unlocker (social proof — FB groups, forums)
      REST API: https://api.brightdata.com/request  zone=mcp_unlocker
      Each request routes through a fresh residential IP (150M+ pool).
      Up to 10 concurrent requests via ThreadPoolExecutor.
      Falls back to SearXNG if BD returns non-200.
      If BD returns 402 (out of credit): sends WhatsApp alert to Peter, falls back to SearXNG.
      API key: BRIGHT_DATA_API_KEY in .env.local.

Understanding zero results
--------------------------
Zero results from any search function are logged at INFO level with an explanation
of the most likely cause. The possibilities are:

  1. Genuine absence — the contractor isn't mentioned publicly in that venue.
     (FB groups and Spanish forums are sparse for most contractors.)
  2. Query too narrow — phone-only or name-only queries rarely appear in forum text.
     Use expand_fb_queries() to broaden.
  3. Bright Data credit exhausted — check logs for "Bright Data credit exhausted (402)"
     and the WhatsApp credit alert. Top up at https://brightdata.com/cp/billing.
  4. Bright Data returned an unexpected status — check logs for "Bright Data returned <N>".
     This triggers a SearXNG fallback and that result is also logged.

The logs always tell you which layer gave the zero, so you never have to guess.
"""

from __future__ import annotations

import logging
import os
import re
import threading as _threading
import time
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

import httpx

from core.resilience import as_completed, shared_thread_pool

from .types import Credential, ProfileResult, TrustSignals

logger = logging.getLogger(__name__)


# ─── SearXNG (fast NIF/REA/review queries — serialized) ──────────────
# Used for the cheap, low-volume checks (≤5 queries per profile).
# Social proof queries (FB groups, forums) go through Bright Data Web Unlocker instead.

_SEARXNG_URL = "http://localhost:8888/search"
_MIN_QUERY_INTERVAL = 1.5  # seconds between sequential calls through SearXNG

_searxng_lock = _threading.Lock()
_last_query_time = 0.0


def _searxng_search(query: str, max_results: int = 10, days_back: int = 0) -> list[dict]:
    """SearXNG JSON search. Serialized — used only for the fast NIF/REA/review checks.

    For social proof (high volume, FB/forum) use _social_search_parallel() which
    fires queries concurrently through Bright Data Web Unlocker instead.

    Args:
        days_back: If > 0, map to SearXNG time_range: day (≤1), week (≤7),
                   month (≤31), year (≤365). 0 = no date filter.
    """
    global _last_query_time

    params: dict = {"q": query, "format": "json"}
    if days_back > 0:
        if days_back <= 1:
            params["time_range"] = "day"
        elif days_back <= 7:
            params["time_range"] = "week"
        elif days_back <= 31:
            params["time_range"] = "month"
        elif days_back <= 365:
            params["time_range"] = "year"
        logger.debug("SearXNG time_range=%s (days_back=%d)", params.get("time_range", "none"), days_back)

    with _searxng_lock:
        elapsed = time.monotonic() - _last_query_time
        if elapsed < _MIN_QUERY_INTERVAL:
            time.sleep(_MIN_QUERY_INTERVAL - elapsed)
        try:
            _last_query_time = time.monotonic()
            resp = httpx.get(
                _SEARXNG_URL,
                params=params,
                headers={"Accept": "application/json"},
                timeout=15,
            )
            if resp.status_code != 200:
                logger.warning("SearXNG returned %d for query: %s", resp.status_code, query[:80])
                return []
            results = resp.json().get("results") or []
            logger.debug("SearXNG query='%s' -> %d results", query[:60], len(results))
            return results[:max_results]
        except Exception as e:
            logger.warning("SearXNG search failed: %s", e)
            return []


# ─── Bright Data Web Unlocker (social proof queries — FB groups and forums) ──
# All high-volume searches (FB groups, Spanish forums) go through Bright Data.
# Zone: mcp_unlocker (unblocker type, uses residential IPs under the hood).
# Each request routes through a fresh residential IP automatically — no pool to manage,
# no per-IP rate limits. Up to 10 concurrent requests via ThreadPoolExecutor.
# Falls back to SearXNG if BD returns non-200 or credit runs out (402).
# API key: BRIGHT_DATA_API_KEY in .env.local.

_BD_API_KEY: str = ""  # loaded lazily

# Track whether we've already sent a credit-out alert this session
_bd_credit_alert_sent = False
_bd_credit_alert_lock = _threading.Lock()


def _load_bd_key() -> str:
    """Load Bright Data API key from env or .env.local."""
    global _BD_API_KEY
    if _BD_API_KEY:
        return _BD_API_KEY
    key = os.environ.get("BRIGHT_DATA_API_KEY", "")
    if not key:
        env_path = "/root/leo/.env.local"
        try:
            for line in open(env_path):
                line = line.strip()
                if line.startswith("BRIGHT_DATA_API_KEY="):
                    key = line.split("=", 1)[1].strip().strip('"')
                    break
        except FileNotFoundError:
            pass
    _BD_API_KEY = key
    if not key:
        logger.warning("BRIGHT_DATA_API_KEY not set — social proof will fall back to SearXNG")
    return key


def _google_via_brightdata(query: str, max_results: int = 8, days_back: int = 0) -> list[dict]:
    """Run one Google search through Bright Data Web Unlocker.

    Each call automatically uses a fresh residential IP — no pool management needed.
    Returns [{url, title, content}].

    Args:
        query: Search query string.
        max_results: Max results to parse from Google HTML.
        days_back: If > 0, adds Google's tbs=qdr: date-restrict parameter.
            Maps to: 1→d (day), ≤7→w (week), ≤31→m (month), ≤90→m3, ≤365→y.
            This is baked into the Google URL — not post-hoc filtering.

    Falls back to SearXNG on:
    - 402 (out of credit): sends WhatsApp alert once per session
    - Any other non-200: logs and falls back silently

    Zero results from this function means one of:
    - Google returned a page but had no <a href="/url?q=..."> links for this query
      (genuine no-results — the query is too narrow or the content doesn't exist publicly)
    - Bright Data returned non-200 and SearXNG also returned nothing
      (check logs for "Bright Data returned <N>" or "SearXNG returned 0" above)
    - Bright Data returned 402 and SearXNG also returned nothing
      (check logs for "Bright Data credit exhausted")
    """
    import urllib.parse

    bd_key = _load_bd_key()
    if not bd_key:
        return _searxng_search(query, max_results=max_results, days_back=days_back)

    # Build Google date-restrict (tbs) parameter
    tbs_suffix = ""
    if days_back > 0:
        if days_back <= 1:
            tbs_suffix = "&tbs=qdr:d"
        elif days_back <= 7:
            tbs_suffix = "&tbs=qdr:w"
        elif days_back <= 31:
            tbs_suffix = "&tbs=qdr:m"
        elif days_back <= 90:
            tbs_suffix = "&tbs=qdr:m3"
        else:
            tbs_suffix = "&tbs=qdr:y"
        logger.debug("Google date-restrict | days_back=%d → tbs=%s", days_back, tbs_suffix.split("=")[-1])

    # gl=es → country=Spain, cr=countryES → restrict index to .es TLD + Spanish pages.
    # hl=es → UI language Spanish (affects snippet formatting, not relevance).
    # Without gl/cr, Google serves Spanish-language results globally (Puerto Rico,
    # Mexico, Argentina etc.) which is not what we want for Spain-focused searches.
    google_url = (
        f"https://www.google.com/search?q={urllib.parse.quote(query)}"
        f"&num={max_results}&hl=es&gl=es&cr=countryES{tbs_suffix}"
    )

    try:
        resp = httpx.post(
            "https://api.brightdata.com/request",
            headers={
                "Authorization": f"Bearer {bd_key}",
                "Content-Type": "application/json",
            },
            json={
                "zone": "mcp_unlocker",
                "url": google_url,
                "method": "GET",
                "format": "raw",
            },
            timeout=30,
        )

        if resp.status_code == 402:
            _handle_bd_credit_exhausted()
            fallback = _searxng_search(query, max_results=max_results, days_back=days_back)
            logger.info(
                "Bright Data 402 fallback to SearXNG | query='%s' -> %d results",
                query[:60], len(fallback),
            )
            return fallback

        if resp.status_code != 200:
            logger.warning(
                "Bright Data returned %d for query '%s' — falling back to SearXNG",
                resp.status_code, query[:60],
            )
            fallback = _searxng_search(query, max_results=max_results, days_back=days_back)
            if not fallback:
                logger.info(
                    "SearXNG also returned 0 results for query '%s' "
                    "(both Bright Data and SearXNG found nothing — "
                    "content likely doesn't exist publicly for this query)",
                    query[:80],
                )
            return fallback

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(resp.text, "html.parser")
        results: list[dict] = []
        seen: set[str] = set()

        for a in soup.select("a[href]"):
            href = a.get("href", "")
            # Google result links come as /url?q=<actual_url>&...
            if href.startswith("/url?q="):
                actual_url = href.split("/url?q=")[1].split("&")[0]
                actual_url = urllib.parse.unquote(actual_url)
            elif href.startswith("http") and "google" not in href:
                actual_url = href
            else:
                continue

            if not actual_url.startswith("http") or actual_url in seen:
                continue
            seen.add(actual_url)
            title = a.get_text(strip=True)
            results.append({"url": actual_url, "title": title[:120], "content": ""})
            if len(results) >= max_results:
                break

        if results:
            logger.debug(
                "Bright Data Web Unlocker | query='%s' -> %d results",
                query[:60], len(results),
            )
        else:
            logger.info(
                "Bright Data Web Unlocker | query='%s' -> 0 results "
                "(Google returned a page but no result links — query may be too narrow "
                "or content genuinely doesn't exist publicly)",
                query[:80],
            )
        return results

    except Exception as e:
        logger.warning("Bright Data search failed: %s — falling back to SearXNG", e)
        return _searxng_search(query, max_results=max_results)


def _handle_bd_credit_exhausted() -> None:
    """Send a WhatsApp alert when Bright Data credit runs out. Only fires once per session."""
    global _bd_credit_alert_sent
    with _bd_credit_alert_lock:
        if _bd_credit_alert_sent:
            return
        _bd_credit_alert_sent = True

    logger.error("Bright Data credit exhausted (HTTP 402) — social proof falling back to SearXNG")
    _send_brightdata_credit_alert()


def _send_brightdata_credit_alert() -> None:
    """Send WhatsApp message to Peter warning that Bright Data credit is out."""
    try:
        env_path = "/root/leo/.env.local"
        wa_token = ""
        wa_phone_id = ""
        founder_phone = ""
        for line in open(env_path):
            line = line.strip()
            if line.startswith("META_WA_TOKEN="):
                wa_token = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("META_WA_PHONE_NUMBER_ID="):
                wa_phone_id = line.split("=", 1)[1].strip().strip('"')
            elif line.startswith("META_FOUNDER_PHONE="):
                founder_phone = line.split("=", 1)[1].strip().strip('"')

        if not wa_token or not wa_phone_id or not founder_phone:
            logger.warning("WhatsApp credentials incomplete — cannot send Bright Data credit alert")
            return

        message = (
            "⚠️ *Bright Data Credit Exhausted*\n\n"
            "Your Bright Data Web Unlocker credit has run out (HTTP 402).\n\n"
            "Social proof searches (Facebook groups, forum mentions) are "
            "falling back to SearXNG, which is slower and less reliable.\n\n"
            "👉 Top up at: https://brightdata.com/cp/billing\n"
            "Account: API key ending in …73ff"
        )

        resp = httpx.post(
            f"https://graph.facebook.com/v19.0/{wa_phone_id}/messages",
            json={
                "messaging_product": "whatsapp",
                "to": founder_phone,
                "type": "text",
                "text": {"body": message},
            },
            headers={
                "Authorization": f"Bearer {wa_token}",
                "Content-Type": "application/json",
            },
            timeout=10,
        )
        if resp.status_code == 200:
            logger.info("Bright Data credit alert sent to founder via WhatsApp")
        else:
            logger.warning("WhatsApp alert failed: %d %s", resp.status_code, resp.text[:100])
    except Exception as e:
        logger.warning("Failed to send Bright Data credit alert: %s", e)


def _social_search_parallel(queries: list[str], max_results: int = 8, days_back: int = 0) -> list[list[dict]]:
    """Run multiple social proof queries in parallel via Bright Data Web Unlocker.

    Each query fires concurrently — Bright Data automatically uses a fresh residential
    IP per request. No pool to manage, no per-IP rate limits.
    Up to 10 concurrent requests.

    Args:
        queries: List of search query strings (typically 3–12 for social proof).
        max_results: Max results to return per query.
        days_back: If > 0, applies Google tbs=qdr: date-restrict to every query.

    Returns:
        List of result lists, in the same order as the input queries.
        Each inner list may be empty — that means either Bright Data found nothing
        for that query or it fell back to SearXNG which also found nothing.
        Check the per-query INFO logs from _google_via_brightdata for the reason.
    """
    results: list[list[dict]] = [[] for _ in queries]

    def _run(idx: int, q: str) -> tuple[int, list[dict]]:
        return idx, _google_via_brightdata(q, max_results=max_results, days_back=days_back)

    pool = shared_thread_pool(max_workers=10)
    futures = {pool.submit(_run, i, q): i for i, q in enumerate(queries)}
    for future in as_completed(futures):
        try:
            idx, res = future.result()
            results[idx] = res
        except Exception as e:
            logger.warning("Parallel social search query failed: %s", e)

    return results


# ─── Bright Data Credit Monitor ──────────────────────────────────────
# Checks whether the Bright Data key is still functional by probing a cheap
# request. If credit is gone (402) sends a WhatsApp alert.


def check_brightdata_credit(notify: bool = True) -> dict:
    """Verify Bright Data Web Unlocker is working and has credit.

    Does a cheap probe request (ipify.org, tiny response). Returns
    {ok: bool, status_code: int, alert_sent: bool}.

    Args:
        notify: If True and credit is out (402), sends WhatsApp alert to Peter.
    """
    bd_key = _load_bd_key()
    if not bd_key:
        logger.warning("BRIGHT_DATA_API_KEY not set — cannot check Bright Data credit")
        return {"ok": False, "status_code": 0, "alert_sent": False, "error": "no_api_key"}

    try:
        resp = httpx.post(
            "https://api.brightdata.com/request",
            headers={
                "Authorization": f"Bearer {bd_key}",
                "Content-Type": "application/json",
            },
            json={
                "zone": "mcp_unlocker",
                "url": "https://api.ipify.org",
                "method": "GET",
                "format": "raw",
            },
            timeout=20,
        )

        if resp.status_code == 200:
            ip = resp.text.strip()
            logger.info("Bright Data credit OK — probe IP: %s", ip)
            return {"ok": True, "status_code": 200, "alert_sent": False, "probe_ip": ip}

        if resp.status_code == 402:
            logger.error("Bright Data credit exhausted (402)")
            alert_sent = False
            if notify:
                _handle_bd_credit_exhausted()
                alert_sent = True
            return {"ok": False, "status_code": 402, "alert_sent": alert_sent}

        logger.warning("Bright Data probe returned unexpected %d", resp.status_code)
        return {"ok": False, "status_code": resp.status_code, "alert_sent": False}

    except Exception as e:
        logger.warning("Bright Data credit check failed: %s", e)
        return {"ok": False, "status_code": 0, "alert_sent": False, "error": str(e)}


# ─── NIF / CIF / NIE Validation (pure math, no network) ─────────────

def validate_nif(nif: str) -> dict:
    """Validate a Spanish NIF/CIF/NIE using the official checksum algorithm.

    Returns {valid: bool, type: "nif"|"cif"|"nie"|"unknown", normalized: str}.
    No network call -- pure math.
    """
    nif = (nif or "").strip().upper().replace(" ", "").replace("-", "")
    if len(nif) < 8 or len(nif) > 9:
        return {"valid": False, "type": "unknown", "normalized": nif}

    _NIF_LETTERS = "TRWAGMYFPDXBNJZSQVHLCKE"

    first = nif[0]
    if first in "XYZ":
        prefix = str("XYZ".index(first))
        numeric = prefix + nif[1:-1]
        if not numeric.isdigit():
            return {"valid": False, "type": "nie", "normalized": nif}
        expected = _NIF_LETTERS[int(numeric) % 23]
        return {"valid": nif[-1] == expected, "type": "nie", "normalized": nif}

    if first in "ABCDEFGHJNPQRSUVW":
        digits = nif[1:-1]
        if not digits.isdigit() or len(digits) != 7:
            return {"valid": False, "type": "cif", "normalized": nif}
        even_sum = sum(int(digits[i]) for i in range(1, 7, 2))
        odd_sum = 0
        for i in range(0, 7, 2):
            d = int(digits[i]) * 2
            odd_sum += d // 10 + d % 10
        total = even_sum + odd_sum
        control = (10 - (total % 10)) % 10
        control_letter = chr(64 + control) if control > 0 else chr(64 + 10)
        last = nif[-1]
        if first in "NPQRSW":
            valid = last == control_letter
        elif first in "ABEH":
            valid = last == str(control)
        else:
            valid = last == str(control) or last == control_letter
        return {"valid": valid, "type": "cif", "normalized": nif}

    if first.isdigit():
        numeric = nif[:-1]
        if not numeric.isdigit():
            return {"valid": False, "type": "nif", "normalized": nif}
        expected = _NIF_LETTERS[int(numeric) % 23]
        return {"valid": nif[-1] == expected, "type": "nif", "normalized": nif}

    return {"valid": False, "type": "unknown", "normalized": nif}


# ─── VIES VAT Check (EU API) ────────────────────────────────────────

def check_vies(nif: str) -> dict:
    """Check a Spanish VAT number against the EU VIES REST API.

    Returns {valid: bool, company_name: str, address: str, error: str|None}.
    Free, no API key needed. Rate-limited by the EU.
    """
    nif = (nif or "").strip().upper().replace(" ", "").replace("-", "")
    if nif.startswith("ES"):
        vat_number = nif[2:]
    else:
        vat_number = nif

    try:
        resp = httpx.post(
            "https://ec.europa.eu/taxation_customs/vies/rest-api/check-vat-number",
            json={"countryCode": "ES", "vatNumber": vat_number},
            headers={"Content-Type": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            logger.warning("VIES API returned %d for %s", resp.status_code, nif)
            return {"valid": None, "company_name": "", "address": "", "error": f"HTTP {resp.status_code}"}

        data = resp.json()
        return {
            "valid": data.get("valid", False),
            "company_name": (data.get("name") or "").strip(),
            "address": (data.get("address") or "").strip(),
            "error": None,
        }
    except Exception as e:
        logger.warning("VIES check failed for %s: %s", nif, e)
        return {"valid": None, "company_name": "", "address": "", "error": str(e)}


# ─── REA Construction Accreditation Check ────────────────────────────

def check_rea(identifier: str, id_type: str = "CIF") -> dict:
    """Check if a company is registered in Spain's REA (construction accreditation).

    Scrapes the public lookup at expinterweb.mites.gob.es.
    id_type: CIF, NIF, NIE, IED, PASS, or REA.
    Returns {registered: bool|None, status: str, error: str|None}.
    """
    id_type_map = {"CIF": "CIF", "NIF": "NIF", "NIE": "NIE", "IED": "IED", "PASS": "PASS", "REA": "REA"}
    tipo = id_type_map.get(id_type.upper(), "CIF")
    identifier = (identifier or "").strip().upper()

    try:
        resp = httpx.get(
            "https://expinterweb.mites.gob.es/rea/pub/consultaAccreditacion.htm",
            params={"tipoId": tipo, "numId": identifier},
            timeout=15,
            follow_redirects=True,
        )
        if resp.status_code != 200:
            return {"registered": None, "status": "", "error": f"HTTP {resp.status_code}"}

        text = resp.text.lower()
        if "inscrita" in text or "vigente" in text or "acreditada" in text:
            return {"registered": True, "status": "INSCRITA", "error": None}
        elif "no consta" in text or "no se han encontrado" in text or "sin resultado" in text:
            return {"registered": False, "status": "NOT_FOUND", "error": None}
        else:
            logger.info("REA response ambiguous for %s, length=%d", identifier, len(resp.text))
            return {"registered": None, "status": "AMBIGUOUS", "error": None}
    except Exception as e:
        logger.warning("REA check failed for %s: %s", identifier, e)
        return {"registered": None, "status": "", "error": str(e)}


# ─── Review Signal Search (SearXNG) ─────────────────────────────────

_REVIEW_DOMAINS = {
    "habitissimo.es": "Habitissimo",
    "houzz.es": "Houzz",
    "cronoshare.com": "Cronoshare",
    "trustlocal.es": "TrustLocal",
    "paginasamarillas.es": "Páginas Amarillas",
    "google.com/maps": "Google Maps",
    "yelp.com": "Yelp",
    "trustpilot.com": "Trustpilot",
    "hogami.leroymerlin.es": "Hogami",
    "planreforma.com": "PlanReforma",
}

_RATING_RE = re.compile(
    r"(\d[.,]\d)\s*/\s*5"
    r"|(\d[.,]\d)\s+(?:estrellas|stars)"
    r"|(?:puntuaci[oó]n|rating|media|nota)\s*(?:de|:)?\s*(\d[.,]\d)"
    r"|(?:puntaje|score)\s+(?:total\s+)?(?:de\s+)?(\d[.,]\d)"
    r"|media\s+de\s+opini[oó]n\s+de\s+(\d[.,]?\d?)\s*/\s*5"
)
_COUNT_RE = re.compile(r"(\d+)\s+(?:opiniones|reseñas|reviews|valoraciones|calificaciones)")


def search_review_signals(name: str, city: str = "", phone: str = "", website: str = "") -> dict:
    """Search SearXNG for review/rating data about a tradesperson.

    Returns {sources: [{source, rating, count, url, snippet}], avg_rating, total_count}.
    """
    sources: list[dict] = []
    seen_domains: set[str] = set()

    queries = []
    domain = ""
    if website:
        from urllib.parse import urlparse as _urlparse
        domain = (_urlparse(website).hostname or "").replace("www.", "")

    # Phone + domain are the most reliable identifiers — put them first.
    # Phone-based query catches review pages that list the phone number.
    if phone:
        clean_phone = phone.strip().lstrip("+").replace(" ", "")
        if len(clean_phone) >= 9:
            queries.append(f'"{clean_phone}" opiniones')
    # Domain is a very strong signal — Google Maps often shows domain in business info.
    if domain:
        queries.append(f'"{domain}" opiniones reseñas')
        queries.append(f'site:google.com/maps "{domain}"')
    # Name + city is the classic Google My Business lookup.
    if name and city:
        queries.append(f'"{name}" {city} google maps reseñas')
    if name and city:
        queries.append(f'"{name}" {city} opiniones reseñas')
    if name:
        queries.append(f'"{name}" valoraciones google')

    for q in queries[:5]:
        results = _searxng_search(q, max_results=12)
        for r in results:
            url = r.get("url", "")
            snippet = (r.get("content") or "") + " " + (r.get("title") or "")

            for domain, source_name in _REVIEW_DOMAINS.items():
                if domain in url and domain not in seen_domains:
                    seen_domains.add(domain)
                    rating_match = _RATING_RE.search(snippet)
                    count_match = _COUNT_RE.search(snippet)
                    rating = None
                    if rating_match:
                        raw = next((g for g in rating_match.groups() if g), None)
                        if raw:
                            rating = float(raw.replace(",", "."))
                    count = int(count_match.group(1)) if count_match else 0
                    sources.append({
                        "source": source_name,
                        "rating": rating,
                        "count": count,
                        "url": url,
                        "snippet": snippet[:200].strip(),
                    })
                    break

    ratings_with_values = [s["rating"] for s in sources if s.get("rating")]
    avg_rating = round(sum(ratings_with_values) / len(ratings_with_values), 1) if ratings_with_values else None
    total_count = sum(s.get("count", 0) for s in sources)

    return {
        "sources": sources,
        "avg_rating": avg_rating,
        "total_count": total_count,
    }


# ─── Facebook Group Search (SearXNG) ─────────────────────────────────
# Shared engine used by both the search_fb_groups Hermes tool (discovery)
# and search_social_proof (verification). All FB search goes through here.

TRADE_TRANSLATIONS = {
    "painter": ["pintor", "painter", "decorator", "pintura"],
    "plumber": ["fontanero", "plumber", "fontanería"],
    "electrician": ["electricista", "electrician", "eléctrico"],
    "builder": ["albañil", "builder", "constructor", "obra"],
    "carpenter": ["carpintero", "carpenter", "madera"],
    "roofer": ["tejador", "roofer", "tejado", "cubierta"],
    "tiler": ["alicatador", "tiler", "azulejos", "baldosas"],
    "hvac": ["climatización", "hvac", "aire acondicionado", "calefacción"],
    "general-contractor": ["reformas", "general contractor", "contratista"],
    "handyman": ["manitas", "handyman", "multiservicio"],
    "architect": ["arquitecto", "architect"],
    "interior-designer": ["interiorista", "interior designer", "decorador"],
}


def expand_fb_queries(query: str, max_queries: int = 4) -> list[str]:
    """Generate query variations: English, Spanish, and related trade synonyms."""
    queries = [query]
    q_lower = query.lower()

    for en_trade, variants in TRADE_TRANSLATIONS.items():
        if en_trade in q_lower or any(v in q_lower for v in variants):
            location_words = [w for w in q_lower.split()
                             if w not in variants and w != en_trade and len(w) > 2]
            location = " ".join(location_words)
            for v in variants:
                candidate = f"{v} {location}".strip()
                if candidate.lower() != query.lower() and candidate not in queries:
                    queries.append(candidate)
            break

    return queries[:max_queries]


def search_fb_posts(queries: list[str], max_results: int = 15, days_back: int = 0) -> list[dict]:
    """Search Facebook groups for contractor mentions via Bright Data Web Unlocker (parallel).

    Each query fires concurrently through Bright Data — each request gets a fresh
    residential IP automatically. Falls back per-query to SearXNG if Bright Data
    returns non-200 or is out of credit.

    Args:
        queries: One or more query strings to run (capped at 3 for FB).
        max_results: Upper bound on total results returned.
        days_back: If > 0, applies Google tbs=qdr: date-restrict so results are
            genuinely from within that window. Applied at the Google search level —
            not post-hoc filtering.

    Returns deduplicated list of {url, title, snippet, group_name} dicts.

    Zero results mean one of:
    - No public Facebook group posts mention this contractor in the time window (genuine absence)
    - The queries were too narrow (name only, no city) — broaden with expand_fb_queries()
    - Bright Data credit is out and SearXNG also found nothing (check logs for 402 / credit alert)
    """
    capped = queries[:3]
    search_queries = [f"{q} site:facebook.com/groups" for q in capped]
    all_raw = _social_search_parallel(search_queries, max_results=15, days_back=days_back)

    results: list[dict] = []
    seen_urls: set[str] = set()
    for raw in all_raw:
        for r in raw:
            url = r.get("url", "")
            if "facebook.com/groups" not in url or url in seen_urls:
                continue
            seen_urls.add(url)
            title = r.get("title", "")
            group_name = ""
            for sep in [" | ", " - "]:
                if sep in title:
                    group_name = title.split(sep)[0].strip()
                    break
            results.append({
                "url": url,
                "title": title,
                "snippet": (r.get("content", "") or "")[:300].strip(),
                "group_name": group_name[:100],
            })
            if len(results) >= max_results:
                break

    if results:
        logger.info(
            "FB search via Bright Data | %d results from %d parallel queries",
            len(results), len(capped),
        )
    else:
        logger.info(
            "FB search via Bright Data | 0 results for queries=%s "
            "(no public FB group posts found — either genuine absence or queries too narrow; "
            "check per-query Bright Data logs above for 402/fallback details)",
            capped,
        )
    return results[:max_results]


# ─── Spanish Forum Search (Forocoches, Mediavida, Reddit ES) ──────────
# Site-restricted Google search targeting forocoches.com/foro, mediavida.com/foro,
# and reddit.com/r/ threads. All queries fire in parallel through Bright Data
# Web Unlocker (residential IP rotation — no proxy pool to manage).
# Forocoches is Spain's largest forum (~20M sessions/month); tradespeople are
# frequently recommended in local/trade subthreads.

FORUM_SITES = [
    ("forocoches.com/foro", "Forocoches"),
    ("mediavida.com/foro", "Mediavida"),
    ("reddit.com/r/spain", "Reddit ES"),
    ("reddit.com/r/espana", "Reddit ES"),
]


def search_forum_posts(queries: list[str], max_results: int = 15, days_back: int = 0) -> list[dict]:
    """Search Spanish forums (Forocoches, Mediavida, Reddit ES) via Bright Data (parallel).

    Builds one query per (base_query × forum_site) combination and fires them all
    at once through Bright Data Web Unlocker. Each request gets a fresh residential IP.
    3 queries × 4 forum sites = 12 parallel searches that finish in ~1.5s.
    Falls back per-query to SearXNG if Bright Data is unavailable or out of credit.

    Args:
        queries: Base query strings (phone number, name+city, "recomendar name").
        max_results: Upper bound on total results returned.
        days_back: If > 0, applies Google tbs=qdr: date-restrict so results are
            genuinely from within that window. Applied at the Google search level —
            not post-hoc filtering.

    Returns deduplicated list of {url, title, snippet, forum_name} dicts.

    Zero results mean one of:
    - No forum threads mention this contractor in the time window (genuine absence)
    - Queries too narrow for these forums (phone-only queries rarely appear in forum text)
    - Bright Data credit exhausted and SearXNG also found nothing (check logs for 402)
    """
    capped = queries[:3]
    # Build (query_string, forum_label) pairs for filtering after results come back
    search_pairs: list[tuple[str, str]] = []
    for q in capped:
        for site, label in FORUM_SITES:
            search_pairs.append((f"{q} site:{site}", label))

    all_raw = _social_search_parallel([p[0] for p in search_pairs], max_results=8, days_back=days_back)

    results: list[dict] = []
    seen_urls: set[str] = set()
    for raw, (_, label) in zip(all_raw, search_pairs):
        for r in raw:
            url = r.get("url", "")
            if not url or url in seen_urls:
                continue
            # Confirm it's actually on the right forum site
            matched_label = None
            for site, flabel in FORUM_SITES:
                if site in url:
                    matched_label = flabel
                    break
            if matched_label is None:
                continue
            seen_urls.add(url)
            results.append({
                "url": url,
                "title": r.get("title", ""),
                "snippet": (r.get("content", "") or "")[:300].strip(),
                "forum_name": matched_label,
            })
            if len(results) >= max_results:
                break

    if results:
        logger.info(
            "Forum search via Bright Data | %d results | %d parallel queries (%d sites x %d queries)",
            len(results), len(search_pairs), len(FORUM_SITES), len(capped),
        )
    else:
        logger.info(
            "Forum search via Bright Data | 0 results | queries=%s "
            "(Forocoches/Mediavida/Reddit ES found nothing — these forums are sparse "
            "for most contractors; check per-query Bright Data logs above for error details)",
            capped,
        )
    return results[:max_results]


# ─── Social Proof (Facebook Group Mentions) ──────────────────────────

def search_social_proof(name: str, city: str = "", phone: str = "") -> dict:
    """Search for Facebook group and forum mentions/recommendations of a contractor.

    Checks both Facebook groups and Spanish forums (Forocoches, Mediavida, Reddit ES)
    so forum endorsements count toward the trust score.

    Returns {
        fb_mentions: [{url, snippet, source_name, author_name?, author_url?, author_avatar?}],
        forum_mentions: [{url, snippet, source_name}],
        count: int
    }.
    """
    # Build queries — phone-first so the strongest identifier leads.
    # Without a phone number, name-only queries are unreliable for generic company
    # names (e.g. "Electric Solutions" appears in many countries). We still run
    # them but apply strict snippet-level filtering to reject false positives.
    queries = []
    clean_phone = ""
    if phone:
        clean_phone = phone.strip().lstrip("+").replace(" ", "")
        if len(clean_phone) >= 9:
            queries.append(f'"{clean_phone}"')
    if name and city:
        queries.append(f'"{name}" {city}')
    if name:
        queries.append(f'recomendar "{name}"')

    if not queries:
        return {"fb_mentions": [], "forum_mentions": [], "count": 0}

    if not clean_phone:
        logger.warning(
            "search_social_proof: no phone number — name-only search for '%s' may "
            "produce false positives; results will require city match to count",
            name,
        )

    def _has_identifying_signal(snippet: str, title: str = "") -> bool:
        """Return True if the text contains the phone or the city.

        Phone match is definitive. City match is a reasonable proxy.
        Name-only match is deliberately excluded — the whole point is that a
        generic name appearing in a snippet doesn't prove it's this company.
        """
        text = (snippet + " " + title).lower()
        if clean_phone and clean_phone[-6:] in text:
            return True
        if city and city.lower() in text:
            return True
        return False

    fb_mentions = []
    forum_mentions = []

    fb_posts = search_fb_posts(queries[:3], max_results=10)
    for p in fb_posts:
        snippet = p.get("snippet", "")
        title = p.get("title", "")
        # Apply the same signal filter to FB mentions as to forum mentions.
        # This prevents a Gibraltar Facebook group from counting as a mention
        # for a Málaga contractor just because the generic name appears there.
        if not _has_identifying_signal(snippet, title):
            logger.debug(
                "Filtered FB mention (no phone/city match): %s", p.get("url", "")[:80]
            )
            continue
        fb_mentions.append({
            "url": p["url"],
            "snippet": snippet[:250],
            "source_name": p.get("group_name") or "Facebook group",
            "author_name": p.get("author_name"),
            "author_url": p.get("author_url"),
            "author_avatar": p.get("author_avatar"),
            "date": p.get("date"),
        })

    forum_posts = search_forum_posts(queries[:3], max_results=10)
    for p in forum_posts:
        snippet = p.get("snippet", "")
        title = p.get("title", "")
        if not _has_identifying_signal(snippet, title):
            logger.debug("Filtered irrelevant forum mention: %s", p.get("url", "")[:80])
            continue
        forum_mentions.append({
            "url": p["url"],
            "snippet": snippet[:250],
            "source_name": p.get("forum_name") or "Forum",
            "date": p.get("date"),
        })

    all_mentions = fb_mentions + forum_mentions
    return {
        "fb_mentions": fb_mentions,
        "forum_mentions": forum_mentions,
        "mentions": all_mentions,  # backwards compat
        "count": len(all_mentions),
    }


# ─── Composite Verification Pipeline ────────────────────────────────

def run_verification_checks(profile: "ProfileResult") -> None:
    """Run the fast verification checks: NIF/VIES/REA + review signals.

    Intentionally excludes social proof (search_social_proof) — that runs
    ~15 SearXNG queries and takes 25–45s. Call run_social_proof_checks()
    separately in a background task after the canvas is first delivered.

    Called after enrich_credentials_from_web(). Non-destructive — only adds data.
    """
    signals = profile.trust_signals or TrustSignals()

    nif_value = ""
    for c in profile.credentials:
        if c.label in ("NIF/CIF", "NIF", "CIF") and c.value:
            nif_value = c.value
            break

    if nif_value:
        nif_result = validate_nif(nif_value)
        signals.nif_valid = nif_result["valid"]
        signals.nif_value = nif_result["normalized"]
        logger.info("NIF validation: %s -> valid=%s type=%s", nif_value, nif_result["valid"], nif_result["type"])

        if nif_result["type"] == "cif":
            vies_result = check_vies(nif_value)
            signals.vies_valid = vies_result["valid"]
            signals.vies_company_name = vies_result["company_name"]
            signals.vies_address = vies_result["address"]
            logger.info("VIES check: %s -> valid=%s name='%s'", nif_value, vies_result["valid"], vies_result["company_name"][:40])

            rea_result = check_rea(nif_value, id_type=nif_result["type"].upper())
            signals.rea_registered = rea_result["registered"]
            signals.rea_status = rea_result["status"]
            logger.info("REA check: %s -> registered=%s status=%s", nif_value, rea_result["registered"], rea_result["status"])

    review_result = search_review_signals(
        name=profile.name,
        city=(profile.location or "").split(",")[0].strip(),
        phone=profile.phone,
        website=getattr(profile, "website", "") or getattr(profile, "source_url", ""),
    )
    signals.review_sources = review_result["sources"]
    signals.review_avg_rating = review_result["avg_rating"]
    signals.review_total_count = review_result["total_count"]
    logger.info("Review signals: %d sources, avg=%.1f, total=%d reviews",
                len(review_result["sources"]),
                review_result["avg_rating"] or 0,
                review_result["total_count"])

    # Partial trust score without social proof — updated when run_social_proof_checks() runs
    score = 0
    if signals.nif_valid:
        score += 15
    if signals.vies_valid:
        score += 15
    if signals.rea_registered:
        score += 10
    if signals.review_avg_rating:
        score += min(20, int(signals.review_avg_rating * 4))
    if signals.review_total_count > 0:
        score += min(10, signals.review_total_count)
    if profile.name and (profile.portfolio_images or profile.projects or profile.reviews):
        score += 15

    signals.trust_score = min(100, score)
    signals.last_checked_at = datetime.now(timezone.utc).isoformat()

    profile.trust_signals = signals
    logger.info("Trust score (pre-social) for '%s': %d/100", profile.name[:30], signals.trust_score)


def run_social_proof_checks(profile: "ProfileResult") -> None:
    """Run the slow social proof searches: Facebook groups + forums (~15 SearXNG calls).

    Separated from run_verification_checks() so it can run as a background task
    after the canvas is first delivered — doesn't block the import stream.

    Updates profile.trust_signals in-place. Caller is responsible for persisting.

    Phone-gating: if no phone number is available, name-only queries for generic
    company names would match unrelated businesses worldwide. We still run the
    search (the snippet filter in search_social_proof handles most cases), but
    we cap any hits to 0 points so they don't inflate the trust score.
    """
    signals = profile.trust_signals or TrustSignals()

    has_phone = bool((profile.phone or "").strip())
    if not has_phone:
        logger.warning(
            "run_social_proof_checks: no phone for '%s' — social proof skipped "
            "(name-only search would be unreliable for verification)",
            profile.name[:40],
        )
        profile.trust_signals = signals
        return

    social_result = search_social_proof(
        name=profile.name,
        city=(profile.location or "").split(",")[0].strip(),
        phone=profile.phone,
    )
    signals.fb_mentions = social_result["fb_mentions"]
    signals.fb_mention_count = len(social_result["fb_mentions"])
    signals.forum_mentions = social_result["forum_mentions"]
    signals.forum_mention_count = len(social_result["forum_mentions"])
    total_mentions = social_result["count"]
    logger.info(
        "Social proof for '%s': %d FB + %d forum = %d total mentions",
        profile.name[:30], signals.fb_mention_count, signals.forum_mention_count, total_mentions,
    )

    # Add social proof points on top of existing trust score
    score = (signals.trust_score or 0) + min(15, total_mentions * 5)
    signals.trust_score = min(100, score)
    signals.last_checked_at = datetime.now(timezone.utc).isoformat()

    profile.trust_signals = signals
    logger.info("Trust score (post-social) for '%s': %d/100", profile.name[:30], signals.trust_score)


def enrich_contractor_from_phone(phone: str, name: str = "", trade: str = "", city: str = "") -> dict:
    """Standalone verification for a contractor we know by phone but may not have a profile URL for.

    Used by the Hermes enrich_contractor tool. Returns a dict with all trust signals.
    """
    profile = ProfileResult(source="phone_lookup", source_url="", phone=phone, name=name, trade=trade, location=city)

    if name and city:
        try:
            enrich_credentials_from_web(profile)
        except Exception as e:
            logger.warning("enrich_credentials_from_web failed: %s", e)

    run_verification_checks(profile)

    return {
        "phone": phone,
        "name": name or profile.name,
        "trade": trade or profile.trade,
        "city": city or profile.location,
        "credentials": [c.model_dump() for c in profile.credentials],
        "trust_signals": profile.trust_signals.model_dump() if profile.trust_signals else {},
    }


# ─── Web Credential Enrichment (migrated from routes/profile_import) ─
# Pulls NIF/CIF and razón social from legal pages on the contractor's own
# website, then queries SearXNG for registry-backed signals. Appends to
# ``profile.credentials`` and ``profile.qa_pairs`` in place.

_CREDENTIAL_SNIPPET_PATTERNS = [
    (
        r"(?:NIF|CIF|N\.?I\.?F\.?|C\.?I\.?F\.?)\s*:?\s*([A-Z]\d{7,8}[A-Z]?)",
        "registration",
        "NIF/CIF",
    ),
]

_HIGH_VALUE_DOMAINS = (
    # Spanish business registries — the fact they have a page IS the verification
    "einforma.com", "empresia.es", "axesor.es", "infocif.es",
    "empresite.eleconomista.es", "infoempresa.com", "borme.es",
    # Spanish trade / review platforms
    "habitissimo.es", "houzz.es", "hogami.leroymerlin.es",
    "cronoshare.com",
    "planreforma.com", "reformasdiseno.com",
    "google.com/maps", "trustpilot.com", "paginasamarillas.es",
    # Broader directories
    "kompass.com", "europages.es",
)

_LEGAL_PATHS = (
    "/aviso-legal", "/aviso-legal/",
    "/legal", "/legal/",
    "/politica-de-privacidad", "/politica-de-privacidad/",
    "/privacy-policy", "/privacy-policy/",
    "/condiciones-legales", "/condiciones-legales/",
    "/legal-notice", "/legal-notice/",
    "/nota-legal", "/nota-legal/",
    "/terminos-legales", "/terminos-legales/",
)

_NIF_RE = re.compile(
    r"(?:NIF|CIF|N\.I\.F\.|C\.I\.F\.|N\.?I\.?F|C\.?I\.?F)"
    r"\s*:?\s*([A-Z]\d{7,8}[A-Z]?)",
    re.IGNORECASE,
)

_RAZON_SOCIAL_RE = re.compile(
    r"(?:^|\s|,|:|;|\()"
    r"([A-ZÁÉÍÓÚÑÜ][a-záéíóúñü0-9A-ZÁÉÍÓÚÑÜ\s,\.&\-]{2,60}"
    r"(?:S\.?L\.?U?\.?|S\.?A\.?U?\.?|S\.?C\.?|S\.?L\.?\s*L\.?|"
    r"Sociedad\s+Limitada|Sociedad\s+An[oó]nima|"
    r"Cooperativa|S\.?\s*Coop\.?))",
)

_REGISTRO_RE = re.compile(
    r"(?:Registro Mercantil|inscrita?\s+en\s+el\s+Registro\s+Mercantil)"
    r"\s+(?:de\s+)?"
    r"((?:Madrid|Barcelona|Valencia|Sevilla|Málaga|Zaragoza|Bilbao|"
    r"Las Palmas|Palma|Santa Cruz|A Coruña|Alicante|Córdoba|Valladolid|"
    r"Vigo|Murcia|Granada|Cádiz|Navarra|Vizcaya|Guipúzcoa|Álava)"
    r"[^<\n\"]{0,100})",
    re.IGNORECASE,
)

_DOMICILIO_RE = re.compile(
    r"(?:domicilio\s+(?:social|fiscal)?|sede\s+social)\s*:?\s*"
    r"((?:C/|Calle|Avda\.?|Avenida|Plaza|Paseo|Pza\.?|Camino|Ronda|Carretera|Ctra\.?)"
    r"[^<\n\"]{5,120})",
    re.IGNORECASE,
)


def _extract_legal_identity(website_url: str) -> dict:
    """Fetch legal / privacy pages and extract NIF, razón social, etc.

    Uses :mod:`scrapling` via the local :data:`_fetcher` singleton.
    """
    from scrapling import Fetcher

    fetcher = Fetcher()

    parsed = urlparse(website_url)
    base = f"{parsed.scheme}://{parsed.hostname}"
    found: dict[str, str] = {}

    for path in _LEGAL_PATHS:
        if found.get("nif") and found.get("razon_social"):
            break
        url = base + path
        try:
            resp = fetcher.get(url)
            if resp.status != 200:
                continue
            text = resp.css("body")[0].get_all_text(strip=True)
        except Exception:
            continue

        if not found.get("nif"):
            m = _NIF_RE.search(text)
            if m:
                found["nif"] = m.group(1).upper()

        if not found.get("razon_social"):
            m = _RAZON_SOCIAL_RE.search(text)
            if m:
                val = m.group(1).strip().rstrip(".")
                if len(val) > 5:
                    found["razon_social"] = val

        if not found.get("registro_mercantil"):
            m = _REGISTRO_RE.search(text)
            if m:
                found["registro_mercantil"] = m.group(1).strip()

        if not found.get("domicilio"):
            m = _DOMICILIO_RE.search(text)
            if m:
                found["domicilio"] = m.group(1).strip()

    if found:
        logger.info(
            "Legal identity from %s: %s",
            base, {k: v[:40] for k, v in found.items()},
        )
    return found


def _company_name_is_specific(name: str) -> bool:
    """Return True if the name is unambiguous enough for a web credential search."""
    if not name or len(name) < 4:
        return False
    if re.search(r"S\.?L\.?U?\.?|S\.?A\.?U?\.?|S\.?C\.|Sociedad\s+Limitada|Sociedad\s+An[oó]nima", name):
        return True
    words = name.split()
    _GENERIC_TRADE = {
        "reformas", "pinturas", "construcciones", "instalaciones", "fontanería",
        "electricidad", "albañilería", "carpintería", "cerrajería", "cristalería",
        "mudanzas", "limpiezas", "jardinería", "climatización", "decoración",
        "interiorismo", "rehabilitaciones", "obras", "mantenimiento",
    }
    _GENERIC_GEO = {
        "madrid", "barcelona", "valencia", "sevilla", "málaga", "zaragoza",
        "bilbao", "murcia", "granada", "córdoba", "alicante", "cádiz",
        "norte", "sur", "este", "oeste", "centro", "capital",
    }
    trade_words = sum(1 for w in words if w.lower() in _GENERIC_TRADE)
    geo_words = sum(1 for w in words if w.lower() in _GENERIC_GEO)
    if len(words) <= 2 and trade_words + geo_words >= len(words) - 1:
        non_generic = [
            w for w in words
            if w.lower() not in _GENERIC_TRADE and w.lower() not in _GENERIC_GEO
        ]
        if not non_generic or all(len(w) <= 3 for w in non_generic):
            return False
    return True


def enrich_credentials_from_web(profile: ProfileResult) -> None:
    """Search the web for registrations/licenses/certifications via SearXNG.

    Two phases:

    1. If a website is known, fetch legal pages for NIF/CIF + razón social.
    2. If we have a specific-enough identity, search the web for additional
       credentials in Spanish business registries.
    """
    if not profile.name or len(profile.name) < 3:
        return

    existing_values = {c.value.lower() for c in profile.credentials if c.value}

    website = profile.website
    if not website:
        for url in profile.merged_from_websites:
            website = url
            break
    legal_identity: dict[str, str] = {}
    if website:
        try:
            legal_identity = _extract_legal_identity(website)
        except Exception as e:
            logger.warning("Legal identity extraction failed: %s", e)

    if legal_identity.get("nif"):
        nif = legal_identity["nif"]
        if nif.lower() not in existing_values:
            profile.credentials.append(Credential(
                type="registration", label="NIF/CIF", value=nif, verified=True,
            ))
            existing_values.add(nif.lower())
            logger.info("Found NIF/CIF from website: %s", nif)

    if legal_identity.get("razon_social"):
        rs = legal_identity["razon_social"]
        if rs.lower() not in existing_values:
            profile.credentials.append(Credential(
                type="registration", label="Razón Social", value=rs, verified=True,
            ))
            existing_values.add(rs.lower())

    if legal_identity.get("registro_mercantil"):
        rm = legal_identity["registro_mercantil"]
        if rm.lower() not in existing_values:
            profile.credentials.append(Credential(
                type="registration", label="Registro Mercantil", value=rm, verified=True,
            ))
            existing_values.add(rm.lower())

    if legal_identity.get("domicilio") and not profile.address:
        profile.address = legal_identity["domicilio"]

    search_name = legal_identity.get("razon_social") or profile.name
    nif_for_search = legal_identity.get("nif") or ""

    has_nif = bool(nif_for_search)
    has_specific_name = _company_name_is_specific(search_name)

    if not has_nif and not has_specific_name:
        logger.info(
            "Web credential search SKIPPED — not enough identifying info: "
            "name='%s', nif='%s'", search_name[:40], nif_for_search,
        )
        return

    location_hint = profile.location or profile.address or ""
    location_short = location_hint.split(",")[0].strip() if location_hint else ""

    queries: list[str] = []
    if has_nif:
        queries.append(f"{nif_for_search} empresa")
    if has_specific_name:
        queries.append(f'"{search_name}" {location_short} empresa')

    all_results: list[dict] = []
    for q in queries:
        results = _searxng_search(q)
        all_results.extend(results)
        logger.info("Web credentials search [%s]: %d results", q[:60], len(results))

    if not all_results:
        return

    new_creds: list[Credential] = []
    found_values: set[str] = set(existing_values)

    for r in all_results:
        snippet = (r.get("content") or "") + " " + (r.get("title") or "")
        url = r.get("url", "")
        for pattern, cred_type, label in _CREDENTIAL_SNIPPET_PATTERNS:
            for m in re.finditer(pattern, snippet, re.IGNORECASE):
                value = m.group(1).strip().upper()
                if value.lower() in found_values or len(value) < 5:
                    continue
                is_official = any(d in url for d in (
                    ".gob.es", "borme.es", "einforma.com", "axesor.es", "infocif.es",
                ))
                new_creds.append(Credential(
                    type=cred_type, label=label, value=value, verified=is_official,
                ))
                found_values.add(value.lower())

    external_profiles: list[dict] = []
    seen_domains: set[str] = set()
    for r in all_results:
        url = r.get("url", "")
        if profile.source_url and url.rstrip("/") == profile.source_url.rstrip("/"):
            continue
        for domain in _HIGH_VALUE_DOMAINS:
            if domain in url:
                if domain not in seen_domains:
                    seen_domains.add(domain)
                    external_profiles.append({
                        "url": url,
                        "title": (r.get("title") or "")[:120],
                        "snippet": (r.get("content") or "")[:200],
                        "domain": domain,
                    })
                break

    if new_creds:
        profile.credentials.extend(new_creds)
        logger.info(
            "Web credential enrichment: added %d credentials for '%s'",
            len(new_creds), search_name[:40],
        )

    if external_profiles:
        logger.info(
            "Web credential enrichment: found %d directory listings",
            len(external_profiles),
        )
        for ep in external_profiles[:8]:
            profile.qa_pairs.append({
                "source": "web_search",
                "type": "external_listing",
                "url": ep["url"],
                "title": ep["title"],
                "snippet": ep["snippet"],
                "domain": ep["domain"],
            })
