"""
Profile Import API
==================

Scrapes tradesperson profiles from Habitissimo, Houzz, Hogami, CronoShare, or generic websites.
AppWebel (Webel) URLs are detected but not imported — their API blocks our servers without a paid proxy.

**Generic websites:** the entry URL is fetched in full (large ``raw_about`` excerpt), then up to 25
same-domain pages prioritized (about / services / portfolio-like paths), skipping admin and
common legal pages. Images use lazy/srcset hints plus ``og:image`` / JSON-LD logo when present.

Habitissimo: pulls avatar, gallery, projects (detail pages when linked), paginated reviews,
and — when a business website is listed — merges a multi-page crawl of that site (photos + text).

Endpoints:
    POST /api/profile-import  — SSE stream with progress + profile JSON
    POST /api/profile-import-sync  — JSON only
"""

import logging
import re
import json
import httpx
from urllib.parse import urlparse, urljoin, urlunparse
from typing import Callable, Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from scrapling import Fetcher
from scrapling.parser import Adaptor as ScraplingAdaptor

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

fetcher = Fetcher()

# Playwright browser instance (lazy-init for headless rendering of SPAs)
_pw_browser = None
_pw_lock = None


def _get_playwright_browser():
    """Lazy-init a persistent Playwright Chromium browser for SPA scraping."""
    global _pw_browser, _pw_lock
    import threading
    if _pw_lock is None:
        _pw_lock = threading.Lock()
    with _pw_lock:
        if _pw_browser is None or not _pw_browser.is_connected():
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            _pw_browser = pw.chromium.launch(headless=True)
            logger.info("Playwright browser launched for SPA scraping")
        return _pw_browser


def _render_spa(url: str, wait_seconds: int = 6, accept_cookies: bool = True) -> tuple[str, list[dict]]:
    """
    Render a SPA page with Playwright headless. Returns (page_text, list_of_img_dicts).
    Each img dict has keys: src, alt, cls.
    """
    browser = _get_playwright_browser()
    ctx = browser.new_context(
        locale="es-ES",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        viewport={"width": 1280, "height": 900},
    )
    page = ctx.new_page()
    try:
        page.goto(url, timeout=35000, wait_until="domcontentloaded")
        import time
        if accept_cookies:
            try:
                page.click(
                    "#didomi-notice-agree-button, #onetrust-accept-btn-handler, "
                    "button:has-text('Aceptar'), button:has-text('Accept All')",
                    timeout=6000,
                )
            except Exception:
                pass
        for _ in range(wait_seconds):
            time.sleep(1)
            t = page.inner_text("body")
            if len(t) > 600:
                break
        text = page.inner_text("body")
        imgs_raw = page.evaluate("""() => {
            return [...document.querySelectorAll('img')].map(i => ({
                src: i.src || i.dataset.src || '',
                alt: i.alt || '',
                cls: i.className || '',
            }));
        }""")
        return text, imgs_raw
    finally:
        ctx.close()


class ImportRequest(BaseModel):
    url: str
    contractor_id: str = ""


class Review(BaseModel):
    author: str = ""
    rating: Optional[float] = None
    text: str = ""
    date: str = ""


class Project(BaseModel):
    title: str = ""
    description: str = ""
    images: list[str] = []
    url: str = ""


class PageChunk(BaseModel):
    """One crawled page — text + images with provenance."""
    url: str
    text: str = ""
    image_urls: list[str] = []


class TeamMember(BaseModel):
    name: str = ""
    role: str = ""
    bio: str = ""
    image_url: str = ""


class Credential(BaseModel):
    """A verified license, certification, insurance, or similar credential."""
    type: str = ""       # e.g. "license", "insurance", "certification", "award", "badge"
    label: str = ""      # e.g. "License Number", "BBB Accredited"
    value: str = ""      # e.g. "CSLB#1065685"
    verified: bool = False


class TrustSignals(BaseModel):
    """Aggregated trust data from verification checks. Stored on ProfileResult."""
    nif_valid: Optional[bool] = None
    nif_value: str = ""
    vies_valid: Optional[bool] = None
    vies_company_name: str = ""
    vies_address: str = ""
    rea_registered: Optional[bool] = None
    rea_status: str = ""
    review_sources: list[dict] = []       # [{source, rating, count, url, snippet}]
    review_avg_rating: Optional[float] = None
    review_total_count: int = 0
    fb_mentions: list[dict] = []          # [{url, snippet, group_name}]
    fb_mention_count: int = 0
    forum_mentions: list[dict] = []       # [{url, snippet, forum_name}]
    forum_mention_count: int = 0
    trust_score: Optional[int] = None     # 0-100 composite
    last_checked_at: str = ""


class ProfileResult(BaseModel):
    source: str  # "habitissimo", "houzz", "hogami", "website"
    source_url: str
    name: str = ""
    description: str = ""
    location: str = ""
    trade: str = ""
    rating: Optional[float] = None
    review_count: int = 0
    years_experience: Optional[int] = None
    phone: str = ""
    phone_source: str = ""  # "habitissimo_ajax" | "scraped" | "whatsapp" | "" — for discrepancy detection
    email: str = ""
    website: str = ""
    avatar_url: str = ""
    cover_images: list[str] = []
    portfolio_images: list[str] = []
    projects: list[Project] = []
    reviews: list[Review] = []
    services: list[str] = []
    people: list[TeamMember] = []
    credentials: list[Credential] = []
    address: str = ""
    typical_job_cost: str = ""
    qa_pairs: list[dict] = []
    raw_about: str = ""
    page_chunks: list[PageChunk] = []
    # Extra business URLs we crawled and merged (e.g. own site linked from Habitissimo)
    merged_from_websites: list[str] = []
    # Objective AI summary of customer reviews (Bedrock); individual reviews stay in `reviews`
    review_summary: str = ""
    # Trust signals from verification checks (VIES, REA, NIF, reviews, social proof)
    trust_signals: Optional[TrustSignals] = None


def detect_platform(url: str) -> str:
    domain = urlparse(url).hostname or ""
    if "habitissimo" in domain:
        return "habitissimo"
    if "houzz" in domain:
        return "houzz"
    if "cronoshare" in domain:
        return "cronoshare"
    if "appwebel" in domain or "webel" in domain:
        return "webel"
    if "hogami" in domain or ("leroymerlin" in domain and "profesional" in (urlparse(url).path or "")):
        return "hogami"
    return "website"


# ─── Cross-platform discovery ──────────────────────────────────────

_PLATFORM_DOMAINS = {
    "habitissimo": ("habitissimo.es", "habitissimo.com"),
    "houzz": ("houzz.es", "houzz.com", "houzz.co.uk"),
    "hogami": ("hogami.leroymerlin.es",),
    "cronoshare": ("cronoshare.com",),
}


def _discover_platform_links(profile: ProfileResult) -> dict[str, str]:
    """Scan page_chunks + raw_about + website field for links to known directory platforms.

    Returns e.g. {"habitissimo": "https://www.habitissimo.es/pro/hogar-solar", "houzz": "..."}.
    Only returns platforms different from the profile's own source.
    """
    found: dict[str, str] = {}
    source_platform = profile.source

    all_text = profile.raw_about or ""
    for chunk in profile.page_chunks:
        all_text += " " + chunk.text
    if profile.description:
        all_text += " " + profile.description

    url_pattern = re.compile(r'https?://[^\s<>"\')\],]+')
    candidates = url_pattern.findall(all_text)

    # Also check the website field itself
    if profile.website:
        candidates.append(profile.website)

    for href in candidates:
        href_clean = href.rstrip(".,;:)")
        host = _hostname(href_clean)
        if not host:
            continue
        for platform, domains in _PLATFORM_DOMAINS.items():
            if platform == source_platform:
                continue
            if platform in found:
                continue
            if any(host.endswith(d) for d in domains):
                path = urlparse(href_clean).path or ""
                if len(path) > 5 and path != "/":
                    found[platform] = href_clean
                    logger.info("Cross-platform discovery: found %s link -> %s", platform, href_clean)

    # If we came from a platform and they have a website, include it
    if profile.website and source_platform != "website":
        wh = _hostname(profile.website)
        if wh and not any(wh.endswith(d) for ds in _PLATFORM_DOMAINS.values() for d in ds):
            if "website" not in found:
                found["website"] = profile.website

    return found


def _merge_profile_data(target: ProfileResult, source: ProfileResult) -> None:
    """Merge fields from source into target without losing existing data."""
    if not target.name and source.name:
        target.name = source.name
    if not target.description and source.description:
        target.description = source.description
    if not target.location and source.location:
        target.location = source.location
    if not target.trade and source.trade:
        target.trade = source.trade
    if not target.phone and source.phone:
        target.phone = source.phone
    if not target.email and source.email:
        target.email = source.email
    if not target.avatar_url and source.avatar_url:
        target.avatar_url = source.avatar_url
    if source.rating is not None and target.rating is None:
        target.rating = source.rating
    if source.review_count and not target.review_count:
        target.review_count = source.review_count
    if source.years_experience and not target.years_experience:
        target.years_experience = source.years_experience

    existing_review_keys = {(r.author, (r.text or "")[:80]) for r in target.reviews}
    for r in source.reviews:
        key = (r.author, (r.text or "")[:80])
        if key not in existing_review_keys:
            target.reviews.append(r)
            existing_review_keys.add(key)

    existing_proj_titles = {p.title.lower() for p in target.projects if p.title}
    for p in source.projects:
        if p.title and p.title.lower() not in existing_proj_titles:
            target.projects.append(p)
            existing_proj_titles.add(p.title.lower())

    existing_svc = {s.lower() for s in target.services}
    for s in source.services:
        if s.lower() not in existing_svc:
            target.services.append(s)
            existing_svc.add(s.lower())

    existing_people_names = {p.name.lower() for p in target.people if p.name}
    for p in source.people:
        if p.name and p.name.lower() not in existing_people_names:
            target.people.append(p)
            existing_people_names.add(p.name.lower())

    existing_imgs = set(target.portfolio_images)
    existing_fps = {_image_fingerprint(img) for img in target.portfolio_images}
    for img in source.portfolio_images:
        if img in existing_imgs or len(target.portfolio_images) >= 200:
            continue
        fp = _image_fingerprint(img)
        if fp in existing_fps:
            continue
        if _is_noise_image(img):
            continue
        target.portfolio_images.append(img)
        existing_imgs.add(img)
        existing_fps.add(fp)

    for chunk in source.page_chunks:
        if not any(c.url == chunk.url for c in target.page_chunks):
            target.page_chunks.append(chunk)

    if source.qa_pairs:
        existing_qs = {qa.get("q", "").lower() for qa in target.qa_pairs}
        for qa in source.qa_pairs:
            if qa.get("q", "").lower() not in existing_qs:
                target.qa_pairs.append(qa)

    target.review_count = max(target.review_count, len(target.reviews))
    target.cover_images = target.portfolio_images[:5]

    if source.source_url and source.source_url not in target.merged_from_websites:
        target.merged_from_websites.append(source.source_url)

    logger.info(
        "Merged %s (%s) into profile: +%d reviews, +%d projects, +%d images -> total: %d reviews, %d projects, %d images",
        source.source, source.source_url,
        len(source.reviews), len(source.projects), len(source.portfolio_images),
        len(target.reviews), len(target.projects), len(target.portfolio_images),
    )


def cross_pollinate(profile: ProfileResult) -> ProfileResult:
    """Discover links to other platforms in the profile data and scrape+merge them.

    E.g. a website with a link to Habitissimo → scrape Habitissimo reviews/projects
    and merge them in.  Or a Habitissimo profile linking to their own website + Houzz.
    """
    discovered = _discover_platform_links(profile)
    if not discovered:
        logger.info("Cross-pollinate: no additional platforms found for %s", profile.source_url)
        return profile

    logger.info("Cross-pollinate: discovered %d additional platforms: %s",
                len(discovered), list(discovered.keys()))

    for platform, link in discovered.items():
        try:
            if platform == "habitissimo":
                sub = scrape_habitissimo(link, merge_external_site=False)
            elif platform == "houzz":
                sub = scrape_houzz(link)
            elif platform == "hogami":
                sub = scrape_hogami(link)
            elif platform == "cronoshare":
                sub = scrape_cronoshare(link)
            elif platform == "website":
                sub = scrape_website(link)
            else:
                continue

            _merge_profile_data(profile, sub)

        except Exception as e:
            logger.warning("Cross-pollinate: failed to scrape %s (%s): %s", platform, link, e)

    _deduplicate_portfolio(profile)
    return profile


# ─── Web Credential Enrichment (SearXNG) ───────────────────────────

_SEARXNG_URL = "http://localhost:8888/search"


def _searxng_search(query: str, max_results: int = 10) -> list[dict]:
    """Run a SearXNG JSON search and return result dicts (title, url, content)."""
    from core import http_client_sync
    try:
        with http_client_sync(timeout=12) as client:
            resp = client.get(
                _SEARXNG_URL,
                params={"q": query, "format": "json"},
                headers={"Accept": "application/json"},
            )
        if resp.status_code != 200:
            logger.warning("SearXNG returned %d for query: %s", resp.status_code, query[:80])
            return []
        return (resp.json().get("results") or [])[:max_results]
    except Exception as e:
        logger.warning("SearXNG search failed: %s", e)
        return []


_CREDENTIAL_SNIPPET_PATTERNS = [
    # NIF/CIF — very specific format, safe to extract from snippets
    (r"(?:NIF|CIF|N\.?I\.?F\.?|C\.?I\.?F\.?)\s*:?\s*([A-Z]\d{7,8}[A-Z]?)", "registration", "NIF/CIF"),
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


def enrich_credentials_from_web(profile: ProfileResult) -> None:
    """Search the web for company registration, licenses, and certifications via SearXNG.

    Runs in two phases:
    1. If a website is known, fetch legal pages (aviso legal, privacidad) for NIF/CIF + razón social.
    2. If we have a specific enough company identity, search the web for additional credentials.

    Focused on Spanish business context: NIF/CIF, Registro Mercantil, REA,
    seguros de responsabilidad civil, carnés de instalador, colegios profesionales.
    """
    if not profile.name or len(profile.name) < 3:
        return

    existing_values = {c.value.lower() for c in profile.credentials if c.value}

    # ── Phase 1: Extract identity from website legal pages ──
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

    # Store NIF/CIF and razón social as credentials
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

    # ── Phase 2: Web search — only if we have a specific enough identity ──
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
        queries.append(f'{nif_for_search} empresa')
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

    # Only extract NIF/CIF from snippets — the one pattern that's unambiguous
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

    # Collect high-value directory URLs where this company appears
    # The fact einforma/empresia has a page for them IS the verification
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
        logger.info("Web credential enrichment: added %d credentials for '%s'", len(new_creds), search_name[:40])

    if external_profiles:
        logger.info("Web credential enrichment: found %d directory listings", len(external_profiles))
        for ep in external_profiles[:8]:
            profile.qa_pairs.append({
                "source": "web_search",
                "type": "external_listing",
                "url": ep["url"],
                "title": ep["title"],
                "snippet": ep["snippet"],
                "domain": ep["domain"],
            })


# ─── Legal Identity Extraction (Aviso Legal / Política de Privacidad) ──

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
    """Fetch legal / privacy pages from a Spanish business website and extract NIF, razón social, etc.

    Returns a dict with keys: nif, razon_social, registro_mercantil, domicilio (all optional strings).
    """
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
        logger.info("Legal identity from %s: %s", base,
                     {k: v[:40] for k, v in found.items()})
    return found


def _company_name_is_specific(name: str) -> bool:
    """Check if a company name is specific enough to do a meaningful web credential search.

    Returns True for names like 'SOPORTE BAÑO, S.L.', 'Conducha', 'Goldenline Remodeling'.
    Returns False for generic names like 'Reformas JM', 'Pinturas Madrid'.
    """
    if not name or len(name) < 4:
        return False
    if re.search(r"S\.?L\.?U?\.?|S\.?A\.?U?\.?|S\.?C\.|Sociedad\s+Limitada|Sociedad\s+An[oó]nima", name):
        return True
    words = name.split()
    _GENERIC_TRADE_WORDS = {
        "reformas", "pinturas", "construcciones", "instalaciones", "fontanería",
        "electricidad", "albañilería", "carpintería", "cerrajería", "cristalería",
        "mudanzas", "limpiezas", "jardinería", "climatización", "decoración",
        "interiorismo", "rehabilitaciones", "obras", "mantenimiento",
    }
    _GENERIC_GEO_WORDS = {
        "madrid", "barcelona", "valencia", "sevilla", "málaga", "zaragoza",
        "bilbao", "murcia", "granada", "córdoba", "alicante", "cádiz",
        "norte", "sur", "este", "oeste", "centro", "capital",
    }
    trade_words = sum(1 for w in words if w.lower() in _GENERIC_TRADE_WORDS)
    geo_words = sum(1 for w in words if w.lower() in _GENERIC_GEO_WORDS)
    # "Reformas Madrid" or "Pinturas JM" — all words are generic trade/geo/initials
    if len(words) <= 2 and trade_words + geo_words >= len(words) - 1:
        non_generic = [w for w in words if w.lower() not in _GENERIC_TRADE_WORDS and w.lower() not in _GENERIC_GEO_WORDS]
        if not non_generic or all(len(w) <= 3 for w in non_generic):
            return False
    return True


# ─── Verification Checks (VIES, NIF, REA, Reviews, Social Proof) ──
# Canonical implementations live in packages/messaging/src/messaging/verification/.
# Re-exported here for backward compatibility with existing callers.
from messaging import (  # noqa: E402
    validate_nif,
    check_vies,
    check_rea,
    search_review_signals,
    search_social_proof,
    run_verification_checks,
    enrich_contractor_from_phone,
)



_SOCIAL_NOISE = (
    "facebook.com",
    "fb.com",
    "instagram.com",
    "twitter.com",
    "x.com",
    "linkedin.com",
    "youtube.com",
    "pinterest.com",
    "tiktok.com",
    "wa.me",
    "whatsapp.com",
    "maps.google",
    "goo.gl",
    "habitissimo",
    "schema.org",
)

# Substrings that signal a generic/UI image, not profile content
_IMG_NOISE = (
    "logo", "icon", "favicon", "pixel", "tracking", ".svg",
    "sprite", "placeholder", "blank.", "spacer", "loader",
    "arrow", "caret", "chevron", "badge", "banner-cta",
    "app-store", "google-play", "play-badge", "apple-badge",
    "footer", "navbar", "header-bg", "btn-", "button-",
    "avatar-default", "no-photo", "no-image",
    "rating-star", "no-rating", "star.png",
    "close.svg", "close.png", "search.svg",
    "static/img/habitissimo", "confianza-online",
    "qualityseal",
)

_IMG_NOISE_DOMAINS = (
    "pinterest.com", "pinimg.com",
    "facebook.com", "fbcdn.net", "fbsbx.com",
    "instagram.com", "cdninstagram.com",
    "twitter.com", "twimg.com",
    "linkedin.com", "licdn.com",
    "youtube.com", "ytimg.com",
    "tiktok.com",
    "whatsapp.com",
    "googleadservices.com", "googlesyndication.com", "doubleclick.net",
    "analytics.", "hotjar.com", "clarity.ms",
    "stockphoto", "shutterstock", "istockphoto", "depositphotos",
    "gravatar.com",
)

# Tiny thumbnail dimensions that indicate UI elements, not portfolio
_TINY_PATTERNS = re.compile(
    r"/w(?:_)?(?:16|24|32|48|64)(?:[/,.])|"
    r"(?:16|24|32|48)x(?:16|24|32|48)|"
    r"fit/w_(?:4[0-9]|[1-3][0-9]|[1-9]),|"  # fit/w_<50
    r"/h_(?:4[0-9]|[1-3][0-9]|[1-9])[/,.]",  # h_<50
    re.IGNORECASE,
)


def _is_noise_image(src: str) -> bool:
    """True if src looks like UI chrome rather than profile/portfolio content."""
    low = src.lower()
    if not low or "data:" in low or len(low) < 12:
        return True
    if any(n in low for n in _IMG_NOISE):
        return True
    if any(d in low for d in _IMG_NOISE_DOMAINS):
        return True
    if _TINY_PATTERNS.search(low):
        return True
    return False


def _image_fingerprint(url: str) -> str:
    """Extract a stable fingerprint for dedup — strips resize params and CDN prefixes."""
    p = urlparse(url)
    path = p.path
    # Wix: /media/HASH~mv2.jpg/v1/crop/... or /quality_auto/HASH~mv2.jpg
    wix_m = re.search(r'([a-f0-9]{6,}_[a-f0-9]+(?:~mv2)?(?:_d_\d+_\d+_s_\d+_\d+)?\.(?:jpg|png|jpeg|webp))', path, re.IGNORECASE)
    if wix_m:
        return wix_m.group(1).lower()
    # Generic: just the last path segment without query
    filename = path.rstrip('/').split('/')[-1].split('?')[0]
    # Strip common resize suffixes
    filename = re.sub(r'-\d+x\d+(?=\.)', '', filename)
    return filename.lower() if filename else url.lower()


def _deduplicate_portfolio(profile: ProfileResult) -> None:
    """Remove noise images and fingerprint-based duplicates in-place."""
    seen_fps: set[str] = set()
    cleaned: list[str] = []
    for img in profile.portfolio_images:
        if _is_noise_image(img):
            continue
        fp = _image_fingerprint(img)
        if fp in seen_fps:
            continue
        seen_fps.add(fp)
        cleaned.append(img)
    removed = len(profile.portfolio_images) - len(cleaned)
    if removed:
        logger.info("Dedup: removed %d images (%d -> %d)", removed, len(profile.portfolio_images), len(cleaned))
    profile.portfolio_images = cleaned
    profile.cover_images = cleaned[:3]


# Paths that usually host real photos (WordPress / CMS uploads) — relax "logo" substring false positives
_CMS_ASSET_PATH_HINTS = (
    "/uploads/", "/media/", "/wp-content/uploads/", "/assets/", "/images/", "/img/",
    "/sites/default/files/", "/imagenes/", "/fotos/", "/gallery/", "/portfolio/",
    "/public/", "/static/images/",
)


def _is_noise_image_website_portfolio(src: str) -> bool:
    """Like `_is_noise_image` but keeps many CMS upload URLs that contain substrings like ``logo`` in filenames."""
    low = src.lower()
    if not low or "data:" in low or len(low) < 12:
        return True
    if any(hint in low for hint in _CMS_ASSET_PATH_HINTS):
        hard = (
            "favicon", "sprite", "spacer", "loader", "pixel", "tracking",
            "emoji", "transparent", "blank.", "1x1", "analytics",
        )
        return any(h in low for h in hard)
    return _is_noise_image(src)


def _best_url_from_srcset(srcset: str) -> Optional[str]:
    """Pick the largest candidate URL from an HTML ``srcset`` (``url 400w`` …)."""
    if not srcset or not str(srcset).strip():
        return None
    best_url, best_w = None, -1
    for part in str(srcset).split(","):
        part = part.strip()
        if not part:
            continue
        bits = part.split()
        if not bits:
            continue
        url = bits[0].strip()
        w = 0
        if len(bits) > 1 and bits[1].endswith("w"):
            try:
                w = int(bits[1][:-1])
            except ValueError:
                w = 0
        if w >= best_w:
            best_w, best_url = w, url
    return best_url


# Parsel: skip images living in obvious chrome / “related” blocks (dense marketing sites).
_STRUCTURAL_ANCESTOR_XPATH = (
    "ancestor::aside | ancestor::footer | ancestor::nav | "
    "ancestor::*[@role='complementary' or @role='navigation']"
)
# Avoid matching “unrelated” — require tokens / phrases common to related-post widgets.
_RELATED_WIDGET_ANCESTOR_XPATH = (
    "ancestor::*["
    "contains(@class, 'related-post') or contains(@class, 'related_post') or "
    "contains(@class, 'related-project') or contains(@class, 'related_project') or "
    "contains(@class, 'similar-project') or contains(@class, 'similar_project') or "
    "contains(@class, 'recommendation') or contains(@class, 'you-may') or "
    "contains(@class, 'cross-sell') or contains(@class, 'yarpp') or "
    "contains(@id, 'related-') or contains(@id, 'similar-') or "
    "contains(translate(@class,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz'),'more-from')]"
)


def _img_in_excluded_portfolio_region(img, *, related_widgets: bool) -> bool:
    """True if this ``img`` node sits in aside/footer/nav or (optionally) a related-posts widget."""
    if not img:
        return True
    if img.xpath(_STRUCTURAL_ANCESTOR_XPATH):
        return True
    if related_widgets and img.xpath(_RELATED_WIDGET_ANCESTOR_XPATH):
        return True
    return False


def _add_img_urls_from_node(img, base_domain: str, seen: set[str], out: list[str]) -> None:
    att = img.attrib

    def add(u: Optional[str]) -> None:
        if not u or not isinstance(u, str):
            return
        u = u.strip()
        if not u.startswith("http"):
            u = urljoin(base_domain, u)
        if _is_noise_image_website_portfolio(u):
            return
        if u not in seen:
            seen.add(u)
            out.append(u)

    add(att.get("src"))
    for key in ("data-src", "data-lazy-src", "data-original", "data-lazy", "data-full-url"):
        add(att.get(key))
    ss = att.get("srcset") or att.get("data-srcset")
    add(_best_url_from_srcset(ss) if ss else None)


def _collect_image_urls_from_page(
    page,
    base_domain: str,
    *,
    smart_scope: bool = True,
    min_keep_before_relax: int = 2,
) -> list[str]:
    """Collect ``img`` URLs including lazy-load and ``srcset`` (best resolution).

    ``smart_scope`` (default): drop images inside aside/footer/nav and common “related posts”
    widgets. If that yields very few URLs, relax to structural-only exclusion, then to all images
    (noise URL filter still applies). Project detail pages use Playwright-specific JS instead.
    """
    all_imgs = page.css("img")

    def collect_with(related_widgets: bool) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for img in all_imgs:
            if smart_scope and _img_in_excluded_portfolio_region(img, related_widgets=related_widgets):
                continue
            _add_img_urls_from_node(img, base_domain, seen, out)
        for pic in page.css("picture source"):
            ss = pic.attrib.get("srcset")
            u = _best_url_from_srcset(ss) if ss else None
            if not u or not isinstance(u, str):
                continue
            u = u.strip()
            if not u.startswith("http"):
                u = urljoin(base_domain, u)
            if _is_noise_image_website_portfolio(u):
                continue
            if u not in seen:
                seen.add(u)
                out.append(u)
        # CSS background-image: url(...)
        for el in page.css("[style]"):
            style_val = el.attrib.get("style", "")
            for m in re.finditer(r'url\(["\']?([^"\')\s]+)["\']?\)', style_val):
                bg_url = m.group(1).strip()
                if not bg_url.startswith("http"):
                    bg_url = urljoin(base_domain, bg_url)
                if _is_noise_image_website_portfolio(bg_url):
                    continue
                if bg_url not in seen:
                    seen.add(bg_url)
                    out.append(bg_url)
        return out

    if not smart_scope:
        return collect_with(related_widgets=False)

    strict = collect_with(related_widgets=True)
    if len(strict) >= min_keep_before_relax:
        logger.info(
            "Website images: smart_scope strict kept %d (related widgets excluded)", len(strict)
        )
        return strict

    loose = collect_with(related_widgets=False)
    if len(loose) >= min_keep_before_relax or not strict:
        logger.info(
            "Website images: relaxed to structural-only (%d imgs, strict had %d)",
            len(loose),
            len(strict),
        )
        return loose

    def collect_noise_url_only() -> list[str]:
        """No DOM scoping — only ``_is_noise_image_website_portfolio`` filters URLs."""
        out: list[str] = []
        seen: set[str] = set()
        for img in all_imgs:
            _add_img_urls_from_node(img, base_domain, seen, out)
        for pic in page.css("picture source"):
            ss = pic.attrib.get("srcset")
            u = _best_url_from_srcset(ss) if ss else None
            if not u or not isinstance(u, str):
                continue
            u = u.strip()
            if not u.startswith("http"):
                u = urljoin(base_domain, u)
            if _is_noise_image_website_portfolio(u):
                continue
            if u not in seen:
                seen.add(u)
                out.append(u)
    return out

    logger.info(
        "Website images: structural scope still sparse (%d), using no-DOM-scope fallback (noise URLs only)",
        len(loose),
    )
    return collect_noise_url_only()


# Playwright: stop before “related / similar projects” headings — highest-leverage fix on dense pages.
_PROJECT_DETAIL_IMAGES_JS = r"""() => {
  const PRECEDING = 2;
  const STRICT_RELATED = __STRICT__;
  const RELATED_HEADING = /(related|similar|también|tambien|recomend|más proyectos|mas proyectos|you may also|proyectos relacionados|otros proyectos|from the same|more from|see also|customers also|también te puede|from nearby|ideas relacionadas|proyectos similares|trabajos similares|te puede interesar|you might like)/i;
  const RELATED_CLASS = /(^|[\s_-])(related-post|related_post|related-project|related_project|similar-project|similar_project|recommendation|you-may|cross-sell|more-from|also-like|seguros-|carousel|photo-carousel)([\s_-]|$)/i;

  function bestSrc(img) {
    const ss = img.getAttribute('srcset') || img.getAttribute('data-srcset') || '';
    const parts = ss.split(',').map(function(s) { return s.trim().split(/\s+/); });
    var best = '', bestW = 0;
    for (var i = 0; i < parts.length; i++) {
      var p = parts[i];
      if (p.length >= 2 && p[1] && p[1].endsWith('w')) {
        var w = parseInt(p[1], 10);
        if (!isNaN(w) && w >= bestW) { bestW = w; best = p[0]; }
      }
    }
    return best || (img.getAttribute('data-src') || '') || (img.src || '') || '';
  }

  function isExcludedRegion(el) {
    if (!el) return false;
    var n = el;
    while (n && n !== document.documentElement) {
      var tag = n.tagName;
      var cls = (n.className && n.className.toString) ? n.className.toString() : '';
      var id = n.id || '';
      var role = n.getAttribute && n.getAttribute('role');
      if (tag === 'ASIDE' || tag === 'FOOTER' || tag === 'NAV') return true;
      if (role === 'complementary' || role === 'navigation') return true;
      if (RELATED_CLASS.test(cls) || RELATED_CLASS.test(id)) return true;
      if (/\b(footer|nav|sidebar|widget|cookie|newsletter)\b/i.test(cls)) return true;
      n = n.parentElement;
    }
    return false;
  }

  var cutoff = null;
  if (STRICT_RELATED) {
    var headingEls = document.querySelectorAll('h1, h2, h3, h4');
    for (var hi = 0; hi < headingEls.length; hi++) {
      var el = headingEls[hi];
      var t = (el.textContent || '').trim().substring(0, 220);
      if (RELATED_HEADING.test(t)) {
        cutoff = el;
        break;
      }
    }
    if (!cutoff) {
      var sections = document.querySelectorAll('section, article, div');
      for (var si = 0; si < sections.length; si++) {
        var sec = sections[si];
        var scls = (sec.className && sec.className.toString) ? sec.className.toString() : '';
        var sid = sec.id || '';
        if (!RELATED_CLASS.test(scls) && !RELATED_CLASS.test(sid)) continue;
        var ar = (sec.getAttribute('aria-label') || '').trim();
        if (RELATED_HEADING.test(ar) || RELATED_CLASS.test(scls) || RELATED_CLASS.test(sid)) {
          cutoff = sec;
          break;
        }
      }
    }
  }

  var out = [];
  var seen = new Set();
  var imgs = document.querySelectorAll('img');
  for (var ii = 0; ii < imgs.length; ii++) {
    var img = imgs[ii];
    if (isExcludedRegion(img)) continue;
    if (cutoff) {
      var pos = cutoff.compareDocumentPosition(img);
      if (!(pos & PRECEDING)) continue;
    }
    var s = bestSrc(img).trim();
    if (!s || s.indexOf('data:') === 0) continue;
    if (!seen.has(s)) { seen.add(s); out.push(s); }
  }
  return out;
}"""


def _playwright_collect_project_detail_images(page, url_allow: Callable[[str], bool]) -> list[str]:
    """Images for a single project detail URL using heading/section cutoffs + fallbacks.

    ``url_allow`` is a predicate ``str -> bool`` (e.g. only Houzz CDN or Habitissimo cloudfront).
    """
    js = _PROJECT_DETAIL_IMAGES_JS.replace("__STRICT__", "true")
    raw = page.evaluate(js)
    picked: list[str] = []
    seen: set[str] = set()
    for s in raw or []:
        if not s or not isinstance(s, str):
            continue
        if not url_allow(s):
            continue
        if _is_noise_image(s):
            continue
        if s not in seen:
            seen.add(s)
            picked.append(s)
    if len(picked) >= 1:
        return picked[:24]

    logger.info("Project detail images: strict guard returned 0, retrying without related-heading cutoff")
    js_loose = _PROJECT_DETAIL_IMAGES_JS.replace("__STRICT__", "false")
    raw2 = page.evaluate(js_loose)
    for s in raw2 or []:
        if not s or not isinstance(s, str):
            continue
        if not url_allow(s):
            continue
        if _is_noise_image(s):
            continue
        if s not in seen:
            seen.add(s)
            picked.append(s)
    if picked:
        return picked[:24]

    logger.info("Project detail images: JS fallbacks empty, scanning img attributes with allow filter")
    for img in page.query_selector_all("img"):
        for attr in ("src", "data-src", "data-lazy-src", "data-original"):
            src = (img.get_attribute(attr) or "").strip()
            if not src or not url_allow(src):
                continue
            if not _is_noise_image(src) and src not in seen:
                seen.add(src)
                picked.append(src)
    return picked[:24]


def _meta_content(page, *, meta_property: Optional[str] = None, meta_name: Optional[str] = None) -> Optional[str]:
    for m in page.css("meta"):
        a = m.attrib
        if meta_property and a.get("property") == meta_property:
            return (a.get("content") or "").strip() or None
        if meta_name and a.get("name") == meta_name:
            return (a.get("content") or "").strip() or None
    return None


def _extract_jsonld_business_fields(page) -> dict:
    """Pull name / phone / description / logo from JSON-LD Organization/LocalBusiness blocks."""
    found: dict = {}
    for script in page.css('script[type="application/ld+json"]'):
        raw = script.get_all_text(strip=True)
        if not raw:
            continue
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            types = item.get("@type", "")
            if isinstance(types, list):
                t = " ".join(str(x) for x in types).lower()
            else:
                t = str(types).lower()
            if not any(
                x in t
                for x in (
                    "organization",
                    "localbusiness",
                    "roofingcontractor",
                    "homeandconstructionbusiness",
                    "professional",
                )
            ):
                continue
            if item.get("name") and not found.get("name"):
                found["name"] = str(item["name"]).strip()
            if item.get("telephone") and not found.get("phone"):
                found["phone"] = str(item["telephone"]).strip()
            if item.get("description") and not found.get("description"):
                found["description"] = str(item["description"])[:15000]
            logo = item.get("logo")
            if not found.get("logo_url"):
                if isinstance(logo, str):
                    found["logo_url"] = logo
                elif isinstance(logo, dict) and logo.get("url"):
                    found["logo_url"] = str(logo["url"])
            ar = item.get("aggregateRating")
            if ar and isinstance(ar, dict) and not found.get("aggregateRating"):
                found["aggregateRating"] = ar
    return found


_SKIP_PATH_PREFIXES = (
    "/wp-admin",
    "/wp-login",
    "/xmlrpc",
    "/feed",
    "/cart",
    "/checkout",
    "/my-account",
    "/account",
    "/wishlist",
)

# Footer / legal — little value for a tradesperson profile; saves crawl budget
_SKIP_PATH_FRAGMENTS = (
    "aviso-legal",
    "politica-de-cookies",
    "politica-de-privacidad",
    "terminos-y-condiciones",
    "condiciones-de-compra",
    "condiciones-de-venta",
    "privacy-policy",
    "cookie-policy",
)


def _should_skip_internal_path(path: str) -> bool:
    low = (path or "/").lower()
    if any(low.startswith(p) for p in _SKIP_PATH_PREFIXES):
        return True
    if low.endswith((".pdf", ".zip", ".doc", ".docx", ".xls", ".xlsx")):
        return True
    for frag in _SKIP_PATH_FRAGMENTS:
        if frag in low:
            return True
    return False


def _internal_path_priority(path: str) -> int:
    """Higher = crawl first (portfolio / about / services)."""
    low = path.lower()
    score = 0
    boost = (
        ("portfolio", 12),
        ("galer", 12),  # galeria, galería
        ("trabajo", 10),
        ("proyect", 10),
        ("realizacion", 10),
        ("obra", 8),
        ("servicio", 8),
        ("sobre", 6),
        ("nosotr", 6),
        ("about", 6),
        ("equipo", 5),
        ("contact", 4),
        ("instalacion", 4),
    )
    for needle, pts in boost:
        if needle in low:
            score += pts
    penal = (
        ("/blog/", -5),
        ("/tag/", -6),
        ("/category/", -6),
        ("/author/", -8),
    )
    for needle, pts in penal:
        if needle in low:
            score += pts
    return score


def _canonical_internal_url(parsed: urlparse) -> str:
    """Same page identity: scheme + host + path + query, no fragment."""
    scheme = (parsed.scheme or "https").lower()
    netloc = (parsed.hostname or "").lower()
    if parsed.port and parsed.port not in (80, 443):
        netloc = f"{netloc}:{parsed.port}"
    path = parsed.path or "/"
    query = parsed.query or ""
    return urlunparse((scheme, netloc, path, "", query, ""))


def _discover_internal_urls(seed_url: str, page, base_parsed: urlparse) -> list[str]:
    """Collect same-host links, filter junk, sort by relevance."""
    host = (base_parsed.hostname or "").lower()
    if not host:
        return []
    seen: set[str] = set()
    scored: list[tuple[int, str]] = []

    for a in page.css("a[href]"):
        href = (a.attrib.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        if not href.startswith("http"):
            href = urljoin(seed_url, href)
        p = urlparse(href)
        if (p.hostname or "").lower() != host:
            continue
        if _should_skip_internal_path(p.path or ""):
            continue
        canon = _canonical_internal_url(p)
        if canon == _canonical_internal_url(base_parsed):
            continue
        if canon in seen:
            continue
        seen.add(canon)
        pr = _internal_path_priority(p.path or "")
        scored.append((pr, canon))

    scored.sort(key=lambda x: (-x[0], x[1]))
    return [u for _, u in scored]


def _hostname(url: str) -> str:
    try:
        return (urlparse(url).hostname or "").lower()
    except Exception:
        return ""


def _is_noise_external_link(href: str) -> bool:
    h = href.lower()
    if not h.startswith("http"):
        return True
    return any(n in h for n in _SOCIAL_NOISE)


def extract_business_website_from_habitissimo(page, body_text: str) -> str:
    """Find the pro's own website from the Habitissimo profile DOM + text."""
    seen: set[str] = set()
    for a in page.css("a[href]"):
        href = (a.attrib.get("href") or "").strip()
        if not href.startswith("http") or _is_noise_external_link(href):
            continue
        host = _hostname(href)
        if not host or host.endswith("habitissimo.es"):
            continue
        clean = href.split("#")[0].split("?")[0].rstrip("/")
        if clean not in seen:
            seen.add(clean)
            # Prefer links labeled like "Web" / visible business URLs in sidebar
            label = a.get_all_text(strip=True).lower()
            if any(k in label for k in ("web", "www", "http", "sitio", "página", "pagina")):
                return clean
    for a in page.css("a[href]"):
        href = (a.attrib.get("href") or "").strip()
        if not href.startswith("http") or _is_noise_external_link(href):
            continue
        host = _hostname(href)
        if host and "habitissimo" not in host:
            return href.split("#")[0].split("?")[0].rstrip("/")
    for pat in (
        r"(?:Página web|Sitio web|Web|WWW)\s*[:\s]+(https?://[^\s<\"]+)",
        r"(https?://(?:www\.)?[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:es|com|net|org)(?:/[^\s<\"]*)?)",
    ):
        m = re.search(pat, body_text, re.IGNORECASE)
        if m:
            cand = m.group(1).rstrip(".,;)")
            if not _is_noise_external_link(cand):
                return cand.split("#")[0].split("?")[0].rstrip("/")
    return ""


def _parse_habitissimo_reviews_from_text(rev_text: str) -> list[Review]:
    """Parse reviews from the rendered text of a Habitissimo profile page.

    The SPA renders reviews in this pattern:
        <Author Name>
        hace X días/meses/años   OR   <date string>
        <N>/5
        <review text (optional)>
    """
    reviews: list[Review] = []
    lines = [l.strip() for l in rev_text.split("\n") if l.strip()]

    i = 0
    while i < len(lines):
        # Look for a rating line like "4/5" or "5/5"
        rating_m = re.match(r"^(\d(?:\.\d)?)/5$", lines[i])
        if rating_m:
            rating_val = float(rating_m.group(1))
            # Author is 2 lines above (name), date is 1 line above
            author = lines[i - 2] if i >= 2 else ""
            date_str = lines[i - 1] if i >= 1 else ""

            # Validate author isn't a histogram label or section header
            if re.match(r"^\d+$", author):
                author = ""
            if "Opiniones" in author or "opiniones" in date_str.lower() and "hace" not in date_str.lower():
                i += 1
                continue

            # Review text is next line(s) — take until next author or section marker
            text_parts = []
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                # Stop if we hit the next rating or section header
                if re.match(r"^\d(?:\.\d)?/5$", ln):
                    break
                if ln.startswith("Información sobre") or ln.startswith("Empresas de"):
                    break
                if re.match(r"^(hace\s+\d+\s+\w+)$", ln, re.IGNORECASE):
                    break
                text_parts.append(ln)
                j += 1

            review_text = " ".join(text_parts).strip()
            # Skip histogram labels like "0 opiniones", "1 opinión"
            if review_text and re.match(r"^\d+\s+opinion", review_text, re.IGNORECASE):
                review_text = ""

            if author:
                reviews.append(Review(
                    author=author,
                    rating=rating_val,
                    date=date_str,
                    text=review_text[:500],
                ))
            i = j
        else:
            i += 1

    return reviews


def _discover_opinion_urls(base: str, first_page) -> list[str]:
    """Follow pagination / opinion links on the first opinions page."""
    urls: list[str] = []
    seen: set[str] = {base.rstrip("/") + "/opiniones"}
    for a in first_page.css("a[href]"):
        href = (a.attrib.get("href") or "").strip()
        if "opinion" not in href.lower() and "/opiniones" not in href.lower():
            continue
        full = urljoin(base, href)
        p = urlparse(full)
        if not p.path or "opinion" not in p.path.lower():
            continue
        full = full.split("#")[0]
        if full not in seen:
            seen.add(full)
            urls.append(full)
    return urls[:25]


def scrape_habitissimo_reviews(base_url: str, first_opiniones_page) -> list[Review]:
    """Aggregate reviews from first page + linked opinion/pagination pages."""
    all_reviews: list[Review] = []
    key_seen: set[tuple[str, str]] = set()
    fetched_pages: set[str] = set()

    def add_batch(revs: list[Review]) -> None:
        for r in revs:
            k = (r.author or "", (r.text or "")[:100])
            if k in key_seen and k != ("", ""):
                continue
            key_seen.add(k)
            all_reviews.append(r)

    add_batch(_parse_habitissimo_reviews_from_text(
        first_opiniones_page.css("body")[0].get_all_text(strip=True)
    ))

    extra = _discover_opinion_urls(base_url, first_opiniones_page)
    for u in extra:
        if u in fetched_pages:
            continue
        fetched_pages.add(u)
        try:
            rp = fetcher.get(u)
            if rp.status != 200:
                continue
            rt = rp.css("body")[0].get_all_text(strip=True)
            add_batch(_parse_habitissimo_reviews_from_text(rt))
        except Exception as e:
            logger.warning("Failed to fetch extra opinion page %s: %s", u, e)

    # Try common paginated URLs (site varies ?pagina vs ?page)
    for n in range(2, 18):
        got_any_new = False
        for suffix in (f"?pagina={n}", f"?page={n}", f"?p={n}"):
            u = f"{base_url.rstrip('/')}/opiniones{suffix}"
            if u in fetched_pages:
                continue
            fetched_pages.add(u)
            try:
                rp = fetcher.get(u)
                if rp.status != 200:
                    continue
                before = len(all_reviews)
                add_batch(_parse_habitissimo_reviews_from_text(
                    rp.css("body")[0].get_all_text(strip=True)
                ))
                if len(all_reviews) > before:
                    got_any_new = True
            except Exception as e:
                logger.debug("Opinion page %s: %s", u, e)
        if not got_any_new and n > 3:
            break
    return all_reviews


def _parse_habitissimo_project_page(page_url: str) -> Optional[Project]:
    try:
        page = fetcher.get(page_url)
        if page.status != 200:
            return None
    except Exception as e:
        logger.warning("Project page fetch failed %s: %s", page_url, e)
        return None
    title = ""
    h1 = page.css("h1::text")
    if h1:
        title = h1.get().strip()
    desc = ""
    meta_desc = page.css('meta[name="description"]')
    if meta_desc:
        desc = meta_desc[0].attrib.get("content", "")[:2000]
    if not desc:
        body = page.css("body")[0].get_all_text(strip=True)
        desc = body[:1500] if body else ""
    imgs: list[str] = []
    for img in page.css('img[src*="photos/project"], img[src*="photos/business"]'):
        if _img_in_excluded_portfolio_region(img, related_widgets=True):
            continue
        src = img.attrib.get("src", "")
        if src and "blank" not in src and src not in imgs:
            imgs.append(src)
    if not title:
        return None
    return Project(title=title, description=desc.strip(), images=imgs[:12], url=page_url)


def scrape_habitissimo_projects(base_url: str, proj_page) -> list[Project]:
    """Collect project cards + per-project detail pages when links exist."""
    projects: list[Project] = []
    seen_urls: set[str] = set()
    detail_urls: list[str] = []

    for a in proj_page.css("a[href]"):
        href = (a.attrib.get("href") or "").strip()
        if "/proyecto" not in href.lower():
            continue
        full = urljoin(base_url, href).split("#")[0]
        low = full.lower().rstrip("/")
        if low.endswith("/proyectos"):
            continue
        if "habitissimo" not in full.lower():
            continue
        if full not in seen_urls:
            seen_urls.add(full)
            detail_urls.append(full)

    for purl in detail_urls[:18]:
        proj = _parse_habitissimo_project_page(purl)
        if proj:
            projects.append(proj)

    if projects:
        return projects

    proj_headers = proj_page.css("h2")
    proj_page_imgs = proj_page.css('img[src*="photos/project"]')
    all_proj_img_srcs = [
        i.attrib.get("src", "")
        for i in proj_page_imgs
        if i.attrib.get("src") and "blank" not in i.attrib.get("src", "")
    ]
    for ph in proj_headers:
        title = ph.get_all_text(strip=True)
        if title and "Proyectos de" not in title and len(title) > 3:
            projects.append(Project(title=title, images=all_proj_img_srcs[:4], description=""))
    return projects


def merge_website_into_profile(profile: ProfileResult, website_url: str, max_pages: int = 14) -> None:
    """
    Crawl a business website and merge images + text into an existing profile.
    Used after Habitissimo/Houzz when a public website URL is known.
    """
    parsed = urlparse(website_url)
    if not parsed.scheme or not parsed.hostname:
        return
    if "habitissimo" in (parsed.hostname or "") or "houzz" in (parsed.hostname or ""):
        return

    base_domain = f"{parsed.scheme}://{parsed.hostname}"
    start = website_url if website_url.startswith("http") else "https://" + website_url
    logger.info("Merging external website crawl into profile: %s", start)

    try:
        page = fetcher.get(start)
    except Exception as e:
        logger.warning("merge_website: failed to fetch %s: %s", start, e)
        return

    if page.status != 200:
        logger.warning("merge_website: %s returned %s", start, page.status)
        return

    profile.merged_from_websites.append(start)

    body_text = page.css("body")[0].get_all_text(strip=True)
    profile.raw_about += f"\n\n--- Website: {start} ---\n{body_text[:4000]}"

    best_desc = _best_description_from_homepage(page)
    if best_desc:
        cur = (profile.description or "").strip()
        if len(best_desc) > len(cur):
            profile.description = best_desc

    for u in _collect_image_urls_from_page(page, base_domain):
        if u not in profile.portfolio_images:
            profile.portfolio_images.append(u)

    internal_links: set[str] = set()
    for a in page.css("a[href]"):
        href = a.attrib.get("href", "")
        if not href or href.startswith("#") or href.startswith("mailto:") or href.startswith("tel:"):
            continue
        if not href.startswith("http"):
            href = urljoin(base_domain, href)
        link_parsed = urlparse(href)
        if link_parsed.hostname and parsed.hostname and link_parsed.hostname == parsed.hostname:
            clean = f"{link_parsed.scheme}://{link_parsed.hostname}{link_parsed.path}".rstrip("/")
            if clean.rstrip("/") != start.rstrip("/"):
                internal_links.add(clean)

    crawled = 0
    for link in list(internal_links)[:max_pages]:
        try:
            sub_page = fetcher.get(link)
            if sub_page.status != 200:
                continue
            crawled += 1
            sub_text = sub_page.css("body")[0].get_all_text(strip=True)
            profile.raw_about += f"\n\n--- {link} ---\n{sub_text[:3500]}"
            for u in _collect_image_urls_from_page(sub_page, base_domain):
                if u not in profile.portfolio_images:
                    profile.portfolio_images.append(u)
        except Exception as e:
            logger.warning("merge_website: failed subpage %s: %s", link, e)

    profile.cover_images = profile.portfolio_images[:3]
    if not profile.website:
        profile.website = start
    logger.info(
        "merge_website complete: merged %s pages, total images=%s",
        crawled + 1,
        len(profile.portfolio_images),
    )


# ─── Habitissimo Scraper (SPA — needs headless browser) ───────────

def _habi_render_page(ctx, url: str, wait_seconds: int = 5, keep_open: bool = False):
    """Render one Habitissimo page in an existing browser context.

    Returns (text, img_dicts) by default.
    If keep_open=True, returns (text, img_dicts, page) — caller must call page.close().
    """
    page = ctx.new_page()
    try:
        page.goto(url, timeout=30000, wait_until="domcontentloaded")
        import time as _t
        for _ in range(wait_seconds):
            _t.sleep(1)
            t = page.inner_text("body")
            if len(t) > 400:
                break
        text = page.inner_text("body")
        imgs = page.evaluate("""() => {
            return [...document.querySelectorAll('img')].map(i => ({
                src: i.src || i.dataset.src || '',
                alt: i.alt || '',
                cls: i.className || '',
            }));
        }""")
        if keep_open:
            return text, imgs, page
        return text, imgs
    except Exception:
        if not keep_open:
            page.close()
        raise
    finally:
        if not keep_open:
            try:
                page.close()
            except Exception:
                pass


# ── Habitissimo authenticated phone reveal ────────────────────────────────
# Habitissimo hides real phone numbers on public pages, showing a call-tracking
# proxy number instead. When we have a logged-in session, the AJAX endpoint
# /do_ajax/business_modal_contact returns the contractor's real number.
#
# Credentials are stored in .env.local as HABITISSIMO_EMAIL / HABITISSIMO_PASSWORD.
# The JWT (AUTH_HAB_TOKEN) expires every ~2h. We cache it module-level and
# re-login when it expires. Session cookies (AWSALB, HabitissimoSessionRH)
# are refreshed per-context.

import time as _time_module
import threading as _threading_module

_habi_session_lock = _threading_module.Lock()
_habi_session: dict = {"token": "", "awsalb": "", "expires_at": 0.0}
# Proxy phone numbers that Habitissimo shows to unauthenticated visitors
_HABI_PROXY_PHONES = {"796585964", "+34796585964", "34796585964", "999999999", "796585963"}


def _habi_load_env_credentials() -> tuple[str, str]:
    email = os.environ.get("HABITISSIMO_EMAIL", "")
    password = os.environ.get("HABITISSIMO_PASSWORD", "")
    if not email:
        env_path = "/root/leo/.env.local"
        try:
            for line in open(env_path):
                line = line.strip()
                if line.startswith("HABITISSIMO_EMAIL="):
                    email = line.split("=", 1)[1].strip().strip('"')
                elif line.startswith("HABITISSIMO_PASSWORD="):
                    password = line.split("=", 1)[1].strip().strip('"')
        except FileNotFoundError:
            pass
    return email, password


def _habi_refresh_session_if_needed(ctx=None) -> bool:
    """Ensure module-level _habi_session has a valid JWT.

    Check order:
    1. Module-level cache (most frequent path — same process, within 100min)
    2. /tmp/habitissimo_session.json written by the daily cron job
    3. Fresh Playwright login (first run of the day, or after a restart)

    The `ctx` parameter is accepted but ignored (kept for call-site compatibility).
    Returns True if a valid session exists after the call.
    """
    global _habi_session
    email, password = _habi_load_env_credentials()
    if not email or not password:
        logger.warning("Habitissimo credentials not found in env — phone reveal disabled")
        return False

    with _habi_session_lock:
        # 1. Check module-level cache
        if _time_module.time() < _habi_session["expires_at"]:
            logger.debug("Habitissimo session cache hit (expires in %.0fs)", _habi_session["expires_at"] - _time_module.time())
            return True

        # 2. Check session file written by daily cron
        session_file = "/tmp/habitissimo_session.json"
        try:
            import json as _json
            with open(session_file) as f:
                cached = _json.load(f)
            if _time_module.time() < cached.get("expires_at", 0):
                _habi_session = cached
                logger.info("Habitissimo session loaded from cron cache (expires in %.0fs)", cached["expires_at"] - _time_module.time())
                return True
        except (FileNotFoundError, Exception):
            pass

        # 3. Fresh Playwright login
        logger.info("Habitissimo session expired — logging in via Playwright…")
        login_page = None
        try:
            from playwright.sync_api import sync_playwright as _sync_pw_login
            with _sync_pw_login() as pw:
                browser = pw.chromium.launch(headless=True)
                login_ctx = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 900},
                )
                login_page = login_ctx.new_page()
                login_page.goto("https://www.habitissimo.es/usuario/ingresar", timeout=20000, wait_until="domcontentloaded")
                _time_module.sleep(1)

                # Dismiss GDPR/cookie consent popup (Didomi)
                for sel in [
                    "button#didomi-notice-agree-button",
                    'button[data-testid="agree-button"]',
                    'button:has-text("Aceptar")',
                ]:
                    try:
                        el = login_page.query_selector(sel)
                        if el and el.is_visible():
                            el.click(timeout=3000)
                            _time_module.sleep(0.5)
                            break
                    except Exception:
                        pass

                login_page.fill('input[name="email"]', email)
                login_page.fill('input[name="password"]', password)
                login_page.click('input[id="form_submit"]', timeout=8000)
                _time_module.sleep(2)

                all_cookies = login_ctx.cookies("https://www.habitissimo.es")
                token = ""
                awsalb = ""
                session_rh = ""
                for c in all_cookies:
                    if c["name"] == "AUTH_HAB_TOKEN":
                        token = c["value"]
                    elif c["name"] == "AWSALB":
                        awsalb = c["value"]
                    elif c["name"] == "HabitissimoSessionRH":
                        session_rh = c["value"]

                login_page.close()
                login_ctx.close()

            if not token:
                logger.warning("Habitissimo login: no AUTH_HAB_TOKEN in cookies — phone reveal disabled")
                return False

            _habi_session = {
                "token": token,
                "awsalb": awsalb,
                "session_rh": session_rh,
                "expires_at": _time_module.time() + 6000,
            }
            # Also write to session file for other processes / restarts
            try:
                import json as _json
                with open(session_file, "w") as f:
                    _json.dump({**_habi_session, "refreshed_at": _time_module.strftime("%Y-%m-%dT%H:%M:%SZ", _time_module.gmtime())}, f)
            except Exception:
                pass
            logger.info("Habitissimo session refreshed via Playwright (expires in ~100min)")
            return True

        except Exception as e:
            logger.warning("Habitissimo login failed: %s — phone reveal disabled", e)
            if login_page:
                try:
                    login_page.close()
                except Exception:
                    pass
            return False


def _habi_inject_cookies(ctx, token: str, awsalb: str) -> None:
    ctx.add_cookies([
        {"name": "AUTH_HAB_TOKEN", "value": token, "domain": ".habitissimo.es", "path": "/"},
        {"name": "AWSALB", "value": awsalb, "domain": "www.habitissimo.es", "path": "/"},
        {"name": "AWSALBCORS", "value": awsalb, "domain": "www.habitissimo.es", "path": "/", "sameSite": "None", "secure": True},
    ])


_HABI_PHONE_AJAX = """
    async (slug) => {
        const resp = await fetch('/do_ajax/business_modal_contact', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'X-Requested-With': 'XMLHttpRequest',
            },
            body: `normalized_name=${slug}&source_page=view_business_show&g_recaptcha_response=`,
            credentials: 'include',
        });
        return await resp.text();
    }
"""


def _habi_extract_phone_from_modal(html: str) -> str:
    """Parse real phone number from /do_ajax/business_modal_contact response HTML."""
    from core.phone import extract_from_html, normalize

    for phone in extract_from_html(html):
        if phone not in _HABI_PROXY_PHONES:
            return phone
    # data-phone attribute (not a tel: link, so extract_from_html won't catch it)
    data_phones = re.findall(r'data-phone\s*=\s*["\']([0-9 +]+)["\']', html)
    if data_phones:
        p = normalize(data_phones[0])
        if p not in _HABI_PROXY_PHONES:
            return p
    # fallback: any 9-digit Spanish number
    for n in re.findall(r'\+?[0-9]{8,12}', html):
        if n not in _HABI_PROXY_PHONES and len(n) in (9, 11, 12):
            return n
    return ""


def _habi_reveal_phone(page_or_slug, base_url_or_none: str = "") -> str:
    """Reveal the real phone number via Habitissimo's AJAX endpoint.

    Accepts either:
    - (page, base_url) — legacy, uses a Playwright page (kept for compatibility)
    - (slug_str, "") — preferred: uses httpx with cached session cookies

    This avoids loading the profile page in a logged-in browser context, which
    would show the contractor dashboard instead of the public profile.
    """
    # Determine if called with a slug string (preferred) or a Playwright page
    if isinstance(page_or_slug, str):
        slug = page_or_slug.strip("/").split("/")[-1] if "/" in page_or_slug else page_or_slug
        sess = _habi_session
        token = sess.get("token", "")
        awsalb = sess.get("awsalb", "")
        session_rh = sess.get("session_rh", "")
        if not token:
            logger.debug("Habitissimo phone reveal: no cached token — skipping")
            return ""
        return _habi_reveal_phone_httpx(slug, token, awsalb, session_rh)
    else:
        # Legacy Playwright page path
        page = page_or_slug
        if base_url_or_none:
            slug = base_url_or_none.rstrip("/").split("/pro/")[-1] if "/pro/" in base_url_or_none else ""
        else:
            slug = ""
        if not slug:
            return ""
        try:
            modal_html = page.evaluate(_HABI_PHONE_AJAX, slug)
            return _habi_extract_phone_from_modal(modal_html)
        except Exception as e:
            logger.warning("Habitissimo phone reveal (Playwright) failed: %s", e)
            return ""


def _habi_reveal_phone_httpx(slug: str, token: str, awsalb: str, session_rh: str = "") -> str:
    """Fire the Habitissimo AJAX contact endpoint via httpx to get the real phone.

    Does NOT require a Playwright browser context — uses session cookies directly.
    Returns the phone string (e.g. "34951215485") or "" if unavailable.
    """
    from core import http_client_sync
    cookies: dict = {"AUTH_HAB_TOKEN": token}
    if awsalb:
        cookies["AWSALB"] = awsalb
        cookies["AWSALBCORS"] = awsalb
    if session_rh:
        cookies["HabitissimoSessionRH"] = session_rh
    try:
        with http_client_sync(timeout=10, follow_redirects=True, cookies=cookies) as _client:
            resp = _client.post(
                "https://www.habitissimo.es/do_ajax/business_modal_contact",
                data={
                    "normalized_name": slug,
                    "source_page": "view_business_show",
                    "g_recaptcha_response": "",
                },
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest",
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                    "Referer": f"https://www.habitissimo.es/pro/{slug}",
                    "Origin": "https://www.habitissimo.es",
                },
            )
        if resp.status_code != 200:
            logger.warning("Habitissimo AJAX phone reveal: HTTP %d for slug=%s", resp.status_code, slug)
            return ""
        phone = _habi_extract_phone_from_modal(resp.text)
        if phone:
            logger.info("Habitissimo AJAX phone reveal: slug=%s -> %s***", slug, phone[:6])
        else:
            logger.debug("Habitissimo AJAX phone reveal: no phone in response for slug=%s", slug)
        return phone
    except Exception as e:
        logger.warning("Habitissimo AJAX phone reveal failed for slug=%s: %s", slug, e)
        return ""


def scrape_habitissimo(url: str, merge_external_site: bool = True) -> ProfileResult:
    base_url = url.rstrip("/").split("/opiniones")[0].split("/fotos")[0].split("/proyectos")[0]
    slug = base_url.rstrip("/").split("/pro/")[-1] if "/pro/" in base_url else ""
    logger.info("Scraping Habitissimo (headless): %s", base_url)

    profile = ProfileResult(source="habitissimo", source_url=base_url)

    from playwright.sync_api import sync_playwright as _sync_pw

    # ── Phase 1: Ensure session is cached (standalone Playwright login) ──
    # This runs in its own Playwright instance so it never conflicts with the
    # scrape browser. The JWT is cached module-level for ~100min.
    _habi_refresh_session_if_needed()

    # ── Phase 2: Scrape the public profile (unauthenticated) ──────────────
    # We do NOT inject auth cookies here. The profile page would redirect a
    # logged-in contractor to their dashboard (/usuario), not show public content.
    text = ""
    with _sync_pw() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(
            locale="es-ES",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )

        try:
            # ── 1. Main profile page ───────────────────────────────────
            text, imgs_raw = _habi_render_page(ctx, base_url, wait_seconds=7)
            if not text or len(text) < 50:
                raise api_error(502, "Habitissimo page did not render (empty)")

            _parse_habi_main_page(profile, text, imgs_raw)

            if not profile.name or profile.name.startswith("Empresas de"):
                raise api_error(404, "Habitissimo profile not found (404 or no content)")

            # ── 2. /fotos — gallery images ────────────────────────────
            try:
                fotos_text, fotos_imgs = _habi_render_page(ctx, base_url + "/fotos", wait_seconds=4)
                _parse_habi_fotos(profile, fotos_imgs)
                logger.info("Habitissimo /fotos: +%d CDN images", len(fotos_imgs))
            except Exception as e:
                logger.warning("Habitissimo /fotos failed (non-fatal): %s", e)

            # ── 3. /proyectos — project cards + images ────────────────
            try:
                proy_text, proy_imgs = _habi_render_page(ctx, base_url + "/proyectos", wait_seconds=4)
                _parse_habi_proyectos(profile, proy_text, proy_imgs)
                logger.info("Habitissimo /proyectos: %d projects", len(profile.projects))
            except Exception as e:
                logger.warning("Habitissimo /proyectos failed (non-fatal): %s", e)

            # ── 3b. Enrich projects with images from their detail pages ──
            if profile.projects:
                try:
                    _habi_enrich_projects(ctx, profile, base_url)
                except Exception as e:
                    logger.warning("Habitissimo project enrichment failed (non-fatal): %s", e)

            # ── 4. /opiniones page 1 — first batch of review texts ────
            try:
                opin_text, _ = _habi_render_page(ctx, base_url + "/opiniones", wait_seconds=4)
                _parse_habi_opiniones(profile, opin_text)
                logger.info("Habitissimo /opiniones: %d reviews parsed", len(profile.reviews))
            except Exception as e:
                logger.warning("Habitissimo /opiniones failed (non-fatal): %s", e)

        finally:
            ctx.close()

    # ── Phase 3: Authenticated phone reveal via httpx (no browser needed) ─
    # Uses the cached JWT to call Habitissimo's AJAX endpoint directly.
    # Runs after the browser is closed — zero Playwright involved.
    if slug and not profile.phone:
        try:
            real_phone = _habi_reveal_phone(slug)
            if real_phone:
                profile.phone = real_phone
                profile.phone_source = "habitissimo_ajax"
        except Exception as e:
            logger.warning("Habitissimo phone reveal (non-fatal): %s", e)

    if profile.reviews:
        profile.review_count = max(profile.review_count, len(profile.reviews))

    profile.cover_images = profile.portfolio_images[:3]

    # Website link — try to find an external URL in the rendered text
    web_m = re.search(r"(https?://(?:www\.)?[a-zA-Z0-9][-a-zA-Z0-9]*\.(?:es|com|net|org)(?:/[^\s]*)?)", text)
    if web_m:
        cand = web_m.group(1).rstrip(".,;)")
        if not _is_noise_external_link(cand):
            profile.website = cand

    if merge_external_site and profile.website:
        h = _hostname(profile.website)
        if h and "habitissimo" not in h:
            try:
                merge_website_into_profile(profile, profile.website)
            except Exception as e:
                logger.warning("merge_website failed for %s: %s", profile.website, e)

    logger.info(
        "Habitissimo scrape done: name=%s, imgs=%s, projects=%s, reviews=%s, rating=%s (%s total)",
        profile.name, len(profile.portfolio_images), len(profile.projects),
        len(profile.reviews), profile.rating, profile.review_count,
    )
    return profile


def _parse_habi_main_page(profile: ProfileResult, text: str, imgs_raw: list[dict]) -> None:
    """Extract name, trade, location, rating, review count, description, Q&A from main page."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]

    # Name from breadcrumb
    bc_line = ""
    bc_idx = -1
    for i, line in enumerate(lines):
        if line.startswith("Empresas") and len(line) > 20:
            bc_line = line
            bc_idx = i
            break

    if bc_line:
        parts = [p.strip() for p in re.split(r"\s{2,}", bc_line) if p.strip()]
        if parts:
            profile.name = parts[-1]
        if len(parts) > 2:
            profile.trade = parts[1]
        if len(parts) > 2:
            profile.location = parts[-2]

    if (not profile.name or profile.name == "Empresas") and bc_idx >= 0 and bc_idx + 1 < len(lines):
        profile.name = lines[bc_idx + 1]

    # Rating
    rating_m = re.search(r"(\d[.,]\d+)\s*/\s*5", text)
    if rating_m:
        profile.rating = float(rating_m.group(1).replace(",", "."))

    # Review count
    rev_m = re.search(r"(\d+)\s*[Oo]pinion", text)
    if rev_m:
        profile.review_count = int(rev_m.group(1))

    # Years experience — "N años de experiencia"
    exp_m = re.search(r"(\d+)\s*años?\s*de\s*experiencia", text, re.IGNORECASE)
    if exp_m:
        profile.years_experience = int(exp_m.group(1))

    # Description — "Información sobre" section
    about_idx = text.find("Información sobre")
    if about_idx >= 0:
        chunk = text[about_idx:about_idx + 3000]
        first_nl = chunk.find("\n")
        if first_nl > 0:
            chunk = chunk[first_nl:].strip()
        end = re.search(r"(?:Cuéntanos|Fotos y vídeos|Preguntas a la comunidad|Empresas de .* similares)", chunk)
        desc_text = chunk[: end.start() if end else 3000].strip()
        profile.description = desc_text[:3000]
        profile.raw_about = chunk[:8000]

    # Q&A
    info_idx = text.find("Información sobre")
    if info_idx >= 0:
        qa_text = text[info_idx:]
        for stop in ("Fotos de", "Proyectos de", "Sellos de confianza", "Detalles de contacto",
                      "Empresas de", "Zonas de servicio", "Ver todas las fotos",
                      "Ver todos los proyectos"):
            stop_idx = qa_text.find(stop)
            if stop_idx > 0:
                qa_text = qa_text[:stop_idx]
        qa_blocks = re.findall(
            r"([^\n]{10,120}\?)\s*\n\s*(.+?)(?=\n[^\n]{10,120}\?|\Z)",
            qa_text, re.DOTALL,
        )
        for q, a in qa_blocks:
            ans = a.strip().split("\n")[0].strip()[:500]
            if ans and len(ans) > 10:
                profile.qa_pairs.append({"q": q.strip(), "a": ans})

    # Location fallback
    if not profile.location:
        loc_m = re.search(r"Trabaja en\s+(.+?)(?:\n|$)", text)
        if loc_m:
            profile.location = loc_m.group(1).strip()[:80]

    if not profile.location:
        for pat in (
            r"(?:Sevilla|Bormujos|Madrid|Barcelona|Málaga|Marbella|Valencia|Alicante|"
            r"Bilbao|Zaragoza|Murcia|Palma|Cádiz|Granada|Alcorcón|Fuengirola|"
            r"Estepona|Torremolinos|Benalmádena|Nerja|Ronda|Antequera|Blanes|Girona|"
            r"Lleida|Tarragona|Valladolid|Salamanca|Burgos|Vigo|Coruña|Oviedo|Gijón|"
            r"Pamplona|San Sebastián|Vitoria|Logroño|Santander|Toledo|Badajoz|Cáceres)",
        ):
            loc = re.search(pat, text)
            if loc:
                profile.location = loc.group(0)
                break

    # Trade fallback
    if not profile.trade:
        bc_m = re.search(r"Empresas\s+(.+?)(?:\s{2,}|\n)", text)
        if bc_m:
            profile.trade = bc_m.group(1).strip()[:50]

    # Images from main page CDN
    for img in imgs_raw:
        src = img.get("src", "")
        if not src or "data:" in src:
            continue
        low = src.lower()
        if "d1szwdapq2yuw7.cloudfront.net" not in low:
            continue
        if any(n in low for n in ("blank", "spacer", "web-logo", "avatar", "user-avatar")):
            continue
        is_logo = "/logo-" in low or "/logo" in low.split("/")[-1][:5] or "isotipo" in low
        if is_logo and not profile.avatar_url:
            profile.avatar_url = src
        elif src not in profile.portfolio_images:
            profile.portfolio_images.append(src)


def _parse_habi_fotos(profile: ProfileResult, imgs_raw: list[dict]) -> None:
    """Extract gallery images from the /fotos page."""
    for img in imgs_raw:
        src = img.get("src", "")
        if not src or "data:" in src:
            continue
        low = src.lower()
        if "d1szwdapq2yuw7.cloudfront.net" not in low:
            continue
        if any(n in low for n in ("blank", "spacer", "web-logo", "avatar", "user-avatar", "static/img")):
            continue
        if "/gallery/" in low or "/photos/" in low:
            if src not in profile.portfolio_images:
                profile.portfolio_images.append(src)


def _parse_habi_proyectos(profile: ProfileResult, text: str, imgs_raw: list[dict]) -> None:
    """Extract project titles and images from the /proyectos page."""
    proj_img_urls = []
    for img in imgs_raw:
        src = img.get("src", "")
        low = src.lower()
        if "d1szwdapq2yuw7.cloudfront.net" not in low:
            continue
        if any(n in low for n in ("blank", "spacer", "web-logo", "avatar", "user-avatar", "static/img")):
            continue
        if "/project/" in low or "/gallery/" in low:
            if src not in proj_img_urls:
                proj_img_urls.append(src)
            if src not in profile.portfolio_images:
                profile.portfolio_images.append(src)

    proj_section = text.find("Proyectos de")
    if proj_section < 0:
        return

    proj_text = text[proj_section:]
    title_pattern = re.findall(
        r"(?:REFORMAS|CONSTRUCCIÓN|INSTALACIÓN|CAMBIO|REHABILITACIÓN)[^»]*»\s*\n\s*(.+?)(?:\n\s*(?:SOPORTE|Profesional|\d+\s*\n))",
        proj_text, re.IGNORECASE,
    )
    seen_titles: set[str] = set()
    for raw_title in title_pattern:
        title = raw_title.strip()
        if not title or len(title) < 3 or title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())
        profile.projects.append(Project(title=title, description="", images=[], url=""))

    if not profile.projects and proj_img_urls:
        lines = [l.strip() for l in proj_text.split("\n") if l.strip()]
        for line in lines:
            if (len(line) > 8 and len(line) < 80
                    and not line.startswith(("Proyectos de", "Ordenar", "Guardar", "Compartir",
                                             "Me gusta", "Enviar", "Profesional", "Pídele",
                                             "Sellos", "Detalles", "Encuentra", "Categorías"))
                    and "»" not in line
                    and not re.match(r"^\d+$", line)
                    and line not in ("SOPORTE BAÑO SL .", "conducha")):
                if line.lower() not in seen_titles:
                    seen_titles.add(line.lower())
                    profile.projects.append(Project(title=line, description="", images=[], url=""))
                    if len(profile.projects) >= 20:
                        break


def _habi_enrich_projects(ctx, profile: ProfileResult, base_url: str) -> None:
    """Use the already-open Playwright context to fetch each Habi project detail page for its images."""
    import time as _t
    if not profile.projects:
        return

    proj_listing_url = base_url + "/proyectos"
    page = ctx.new_page()
    try:
        page.goto(proj_listing_url, timeout=20000, wait_until="domcontentloaded")
        _t.sleep(2)
        try:
            page.click("#didomi-notice-agree-button, button:has-text('Aceptar')", timeout=3000)
        except Exception:
            pass

        proj_links = page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a[href*="/proyecto/"]'));
            return links.map(a => ({
                href: a.href,
                text: (a.innerText || '').trim().substring(0, 80)
            })).filter(l => l.href && l.text.length > 3);
        }""")
        logger.info("Habi projects: found %d detail links on /proyectos", len(proj_links or []))

        link_map: dict[str, str] = {}
        for lnk in (proj_links or []):
            link_map[lnk["text"].lower().strip()] = lnk["href"]

        for proj in profile.projects[:10]:
            proj_url = link_map.get(proj.title.lower().strip(), "")
            if not proj_url:
                for key, url in link_map.items():
                    if key in proj.title.lower() or proj.title.lower() in key:
                        proj_url = url
                        break
            if not proj_url:
                continue

            proj.url = proj_url
            try:
                page.goto(proj_url, timeout=15000, wait_until="domcontentloaded")
                _t.sleep(1.5)

                def _habi_allow(u: str) -> bool:
                    low = u.lower()
                    return (
                        "cloudfront.net" in low
                        and "avatar" not in low
                        and "static/img" not in low
                    )

                proj_imgs = _playwright_collect_project_detail_images(page, _habi_allow)
                proj.images = proj_imgs[:15]
                logger.info("Habi project '%s': %d images from detail page", proj.title[:40], len(proj.images))
            except Exception as e:
                logger.warning("Habi project detail failed for '%s': %s", proj.title[:40], e)
    except Exception as e:
        logger.warning("Habi project enrichment failed (non-fatal): %s", e)
    finally:
        page.close()


def _parse_habi_opiniones(profile: ProfileResult, text: str) -> None:
    """Parse reviews from the rendered /opiniones page text."""
    rev_start = text.find("Opiniones sobre")
    if rev_start < 0:
        return
    rev_text = text[rev_start:]

    # Skip header noise (sort controls, heading) — start from "Ordenar" or first "hace"
    sort_idx = rev_text.find("Ordenar opiniones")
    if sort_idx > 0:
        after_sort = rev_text[sort_idx + len("Ordenar opiniones"):]
        # Find the next line that isn't a sort option
        lines_after = after_sort.lstrip("\n").split("\n")
        skip_words = {"Mejor valoradas", "Más recientes", "Peor valoradas", ""}
        consumed = 0
        for line in lines_after:
            if line.strip() in skip_words:
                consumed += len(line) + 1
            else:
                break
        rev_text = after_sort[consumed:]

    # Strip company response blocks — "CompanyName, respondió...\n hace N\n...\nLeer más"
    rev_text = re.sub(
        r"[^\n]+,\s*respondió\.\.\.\s*\n.*?(?:Leer más|(?=\n[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ\s\.]{1,40}\n\s*hace\s+\d)|\Z)",
        "", rev_text, flags=re.DOTALL,
    )
    # Clean orphaned response tails (truncated company responses without "respondió" header)
    rev_text = re.sub(r"\n(?:Un saludo[^\n]*\n)?(?:\s*\n)*Leer más", "", rev_text)

    # Pattern: Author\n hace N tiempo\n  N/5\n Optional review text
    blocks = re.finditer(
        r"([A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ\s\.]{1,40})\n\s*hace\s+(\d+\s+\w+)\s*\n\s*(\d)/5\s*\n(.*?)(?=\n[A-ZÁÉÍÓÚÑ][\wáéíóúñÁÉÍÓÚÑ\s\.]{1,40}\n\s*hace\s+\d|Pídele presupuesto|Sellos de confianza|\Z)",
        rev_text, re.DOTALL,
    )

    seen: set[str] = set()
    noise_starts = ("Opiniones sobre", "Ordenar", "Ver todas", "Pídele", "Sellos")
    for m in blocks:
        author = m.group(1).strip()
        date_str = "hace " + m.group(2).strip()
        rating = float(m.group(3))
        body = m.group(4).strip()

        body = re.sub(r"Sobre el trabajo.*?habitissimo", "", body, flags=re.DOTALL).strip()
        body = re.split(r"\nOpina sobre\b|Opina sobre\b|Describe tu experiencia con\b", body, maxsplit=1)[0].strip()
        body = re.sub(r"\s+\d\s*\.\.\.\s*»\s*$", "", body).strip()
        body = re.sub(r"¿Te ha resultado útil\?.*", "", body).strip()
        body = re.sub(r"Leer más\s*", "", body).strip()
        body = re.sub(r"Un saludo\s*$", "", body).strip()
        body = re.sub(r"^\d+\s+\d+\s*$", "", body, flags=re.MULTILINE).strip()
        body_lines = [l.strip() for l in body.split("\n") if l.strip()]
        body = " ".join(body_lines)[:500]

        if not author or len(author) < 2 or any(author.startswith(n) for n in noise_starts):
            continue
        key = (author, body[:50])
        if key in seen:
            continue
        seen.add(key)

        profile.reviews.append(Review(
            author=author,
            rating=rating,
            date=date_str,
            text=body,
        ))


# ─── Houzz Scraper ─────────────────────────────────────────────────


def _extract_houzz_about_from_body(body_text: str) -> str:
    """Extract the 'Sobre nosotros' / 'About Us' blurb from Houzz profile body text."""
    if not body_text or len(body_text) < 20:
        return ""
    for marker in ("Sobre nosotros", "About Us"):
        about_idx = body_text.find(marker)
        if about_idx >= 0:
            second = body_text.find(marker, about_idx + len(marker) + 1)
            if second >= 0:
                about_idx = second
            break
    else:
        about_idx = body_text.find("About")
    if about_idx < 0:
        return ""
    chunk = body_text[about_idx + 15 : about_idx + 60000]
    next_section = re.search(
        r"(?:Servicios prestados|Services Provided|Zonas de trabajo|Service Area|Premios|Awards|"
        r"Categoría|Category|\d+\s*(?:Proyectos|Projects)|"
        r"Detalles de la empresa|Business Details|Detalles|Número de teléfono|Phone Number|"
        r"Página web|Website|Dirección|Address|"
        r"Coste medio|Typical Job Costs|Seguidores|Followers|"
        r"Enlaces a redes|Social Links|Valoraciones|Reviews|"
        r"Información de la empresa|Valoraciones\s+y|EMPRESA\s|DESCUBRE HOUZZ|DISCOVER HOUZZ)",
        chunk,
        re.IGNORECASE,
    )
    if next_section:
        out = chunk[: next_section.start()].strip()
    else:
        out = chunk[:20000].strip()
    # Drop leading UI junk lines
    out = re.sub(r"^\s*(Sobre nosotros|About Us|About)\s*", "", out, flags=re.IGNORECASE)
    return out.strip()


def _houzz_fetch_about_playwright(profile_url: str) -> str:
    """Render the Houzz profile in a browser, open the About tab if needed, read full about text."""
    import time as _t
    extracted = ""
    try:
        browser = _get_playwright_browser()
        ctx = browser.new_context(
            locale="es-ES",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        pw_page = ctx.new_page()
        try:
            pw_page.goto(profile_url, timeout=25000, wait_until="domcontentloaded")
            _t.sleep(2)
            try:
                pw_page.click("button:has-text('Aceptar'), button:has-text('Accept')", timeout=4000)
            except Exception:
                pass
            # Tab is often collapsed in initial HTML; click to expand full about
            for sel in (
                "a:has-text('Sobre nosotros')",
                "button:has-text('Sobre nosotros')",
                "[role='tab']:has-text('Sobre nosotros')",
                "a:has-text('About')",
                "button:has-text('About')",
                "[role='tab']:has-text('About')",
            ):
                try:
                    pw_page.click(sel, timeout=4000)
                    _t.sleep(1.2)
                    break
                except Exception:
                    continue
            _t.sleep(1)
            body = pw_page.inner_text("body")
            extracted = _extract_houzz_about_from_body(body)
            if len(extracted) < 80:
                alt = pw_page.evaluate("""() => {
                    const m = document.querySelector('main, [role="main"], .profile-content, #main');
                    return m ? m.innerText : '';
                }""")
                if alt and len(alt) > len(extracted):
                    extracted = _extract_houzz_about_from_body(alt) or alt[:15000].strip()
        finally:
            pw_page.close()
            ctx.close()
    except Exception as e:
        logger.warning("Houzz Playwright about fetch failed (non-fatal): %s", e)
        return ""
    logger.info("Houzz about Playwright: extracted %d chars", len(extracted))
    return extracted


def _best_description_from_homepage(page) -> str:
    """Pick the longest useful homepage description (meta, og:, JSON-LD)."""
    candidates: list[str] = []
    for m in page.css('meta[name="description"]'):
        c = (m.attrib.get("content") or "").strip()
        if len(c) > 20:
            candidates.append(c)
    og = _meta_content(page, meta_property="og:description")
    if og and len(og) > 20:
        candidates.append(og)
    ld = _extract_jsonld_business_fields(page)
    ld_d = (ld.get("description") or "").strip()
    if len(ld_d) > 20:
        candidates.append(ld_d)
    if not candidates:
        return ""
    return max(candidates, key=len)[:15000]


def _houzz_enrich_projects(profile: ProfileResult, max_projects: int = 8) -> None:
    """Use Playwright to discover project links from the profile page and scrape their images."""
    import time as _t
    if not profile.projects:
        return

    logger.info("Houzz: enriching %d projects with images", len(profile.projects))
    try:
        browser = _get_playwright_browser()
        ctx = browser.new_context(
            locale="es-ES",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        pw_page = ctx.new_page()
        try:
            pw_page.goto(profile.source_url, timeout=20000, wait_until="domcontentloaded")
            _t.sleep(2)
            try:
                pw_page.click("button:has-text('Aceptar'), button:has-text('Accept')", timeout=3000)
            except Exception:
                pass

            # Find all project links on the page
            proj_links = pw_page.evaluate("""() => {
                const links = Array.from(document.querySelectorAll('a'));
                return links
                    .filter(a => a.href && (a.href.includes('/proyectos/') || a.href.includes('/hznb/') || a.href.includes('/projects/')))
                    .map(a => ({
                        href: a.href,
                        text: (a.innerText || '').trim().substring(0, 100)
                    }))
                    .filter(l => l.text.length > 3);
            }""")
            logger.info("Houzz: found %d project links on profile page", len(proj_links or []))

            if not proj_links:
                return

            # Build a lookup: fuzzy match project title → URL
            link_map: dict[str, str] = {}
            for lnk in proj_links:
                link_map[lnk["text"].lower().strip()] = lnk["href"]

            enriched = 0
            for proj in profile.projects[:max_projects]:
                proj_url = ""
                title_low = proj.title.lower().strip()
                # Exact match
                if title_low in link_map:
                    proj_url = link_map[title_low]
                else:
                    # Fuzzy: check if title is contained in any link text or vice versa
                    for key, url in link_map.items():
                        if title_low in key or key in title_low:
                            proj_url = url
                            break
                if not proj_url:
                    continue

                proj.url = proj_url
                try:
                    pw_page.goto(proj_url, timeout=15000, wait_until="domcontentloaded")
                    _t.sleep(1.5)
                    def _houzz_allow(u: str) -> bool:
                        low = u.lower()
                        return "hzcdn.com" in low and "data:" not in low

                    proj_imgs = _playwright_collect_project_detail_images(pw_page, _houzz_allow)
                    proj.images = proj_imgs[:20]

                    desc_text = pw_page.evaluate("""() => {
                        const el = document.querySelector('[data-testid="project-description"], .hz-track-me--project-description, .project-info p, .project-info div');
                        return el ? el.innerText.trim() : '';
                    }""")
                    if desc_text and len(desc_text) > 10:
                        proj.description = desc_text[:500]

                    enriched += 1
                    logger.info("Houzz project '%s': %d images", proj.title[:40], len(proj.images))
                except Exception as e:
                    logger.warning("Houzz project enrich failed for '%s': %s", proj.title[:40], e)

            logger.info("Houzz: enriched %d/%d projects", enriched, len(profile.projects))
        finally:
            pw_page.close()
            ctx.close()
    except Exception as e:
        logger.warning("Houzz project enrichment failed (non-fatal): %s", e)


def _houzz_fetch_page(url: str) -> ScraplingAdaptor:
    """Fetch a Houzz page via curl_cffi (TLS impersonation) — scrapling's Fetcher gets 404'd."""
    from curl_cffi import requests as cffi_req
    resp = cffi_req.get(url, impersonate="chrome", timeout=20)
    if resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Houzz returned {resp.status_code}")
    return ScraplingAdaptor(resp.text, url=url)


def scrape_houzz(url: str) -> ProfileResult:
    base_url = url.split("#")[0].split("?")[0].rstrip("/")
    logger.info(f"Scraping Houzz profile: {base_url}")

    profile = ProfileResult(source="houzz", source_url=base_url)

    page = _houzz_fetch_page(base_url)

    body_text = page.css("body")[0].get_all_text(strip=True)

    # ── Structured data from JSON-LD (most reliable source) ──────
    ld = _extract_jsonld_business_fields(page)
    if ld.get("name"):
        profile.name = ld["name"]
    if ld.get("description"):
        profile.description = ld["description"]
    if ld.get("phone"):
        profile.phone = ld["phone"]
    if ld.get("logo_url"):
        profile.avatar_url = str(ld["logo_url"])
    ld_rating = ld.get("aggregateRating") or {}
    if isinstance(ld_rating, dict):
        try:
            profile.rating = float(ld_rating.get("ratingValue", 0))
        except (ValueError, TypeError):
            pass
        try:
            profile.review_count = int(ld_rating.get("reviewCount", 0))
        except (ValueError, TypeError):
            pass

    # ── Fallback name from <h1> ──
    if not profile.name:
        h1 = page.css("h1::text")
        if h1:
            profile.name = h1.get().strip()

    # ── Rating fallback from body text ──
    if not profile.rating:
        for pat in (
            r"(\d[.,]\d)\s*(?:de 5|de5|/5|estrellas)",
            r"Average rating:\s*(\d[.,]?\d?)\s*out of 5",
            r"Puntuación media:\s*(\d)",
        ):
            rm = re.search(pat, body_text, re.IGNORECASE)
            if rm:
                profile.rating = float(rm.group(1).replace(",", "."))
                break

    # ── Review count fallback ──
    if not profile.review_count:
        rev_match = re.search(r"(\d+)\s*(?:valoracion|comentario|review|Review)", body_text, re.IGNORECASE)
    if rev_match:
        profile.review_count = int(rev_match.group(1))

    # ── Description — JSON-LD first, then body text, then Playwright ──
    about_http = _extract_houzz_about_from_body(body_text)
    if about_http and len(about_http) > len(profile.description or ""):
        profile.description = about_http
    meta_desc = _best_description_from_homepage(page)
    if meta_desc and len(meta_desc) > len(profile.description or ""):
        profile.description = meta_desc
    profile.description = (profile.description or "").strip()

    # Location / trade from URL path
    url_parts = urlparse(base_url).path.lower().split("/")
    _TRADE_MAP = {
        "empresas-de-reformas": "Reformas", "general-contractors": "Reformas",
        "interioristas": "Interiorismo", "arquitectos-de-interiores": "Interiorismo",
        "interior-designers": "Interiorismo", "diseno-de-interiores-y-decoracion": "Interiorismo",
        "arquitectos": "Arquitectura", "architects": "Arquitectura",
        "muebles-y-decoracion": "Muebles y Decoración", "mobiliario": "Muebles y Decoración",
        "albaniles": "Albañilería",
        "instalacion-y-reformas-de-cocinas-y-banos": "Reformas de cocinas y baños",
        "kitchen-and-bath": "Reformas de cocinas y baños",
        "reformas-generales": "Reformas",
    }
    for part in url_parts:
        if part in _TRADE_MAP:
            profile.trade = _TRADE_MAP[part]
            break

    # Location
    for pat in (
        r"Zonas de trabajo\s+(.+?)(?:\n|Premios|Categoría|Información)",
        r"Service Area\s+(.+?)(?:\n|Awards|Cost)",
        r"Dirección\s+(.+?)(?:\n|Coste|Seguidores|Número)",
    ):
        loc_m = re.search(pat, body_text)
        if loc_m:
            profile.location = loc_m.group(1).strip()[:80]
            break
    if not profile.location:
        og_title = _meta_content(page, meta_property="og:title") or ""
        loc_from_title = re.search(r"-\s*([^|]+?),\s*([A-Z]{2})\s+(?:US|UK|ES|DE|FR|IT)\s*\|", og_title)
        if loc_from_title:
            profile.location = f"{loc_from_title.group(1).strip()}, {loc_from_title.group(2)}"

    # Images from Houzz CDN — do not filter by width token; Houzz changes sizes (w592, w1280, etc.)
    seen_hz: set[str] = set()
    for img in page.css("img"):
        src = (img.attrib.get("src") or "").strip()
        ss = img.attrib.get("srcset") or img.attrib.get("data-srcset")
        if ss:
            best = _best_url_from_srcset(ss)
            if best and ("hzcdn.com" in best.lower()):
                src = best
        if not src or "data:" in src:
            continue
        low = src.lower()
        if "hzcdn.com" not in low:
            continue
        if _is_noise_image(src):
            continue
        if src in seen_hz:
            continue
        seen_hz.add(src)
        profile.portfolio_images.append(src)

    # Projects from project headers — only real project links
    HOUZZ_NON_PROJECTS = {
        "Servicios prestados:", "Zonas de trabajo", "Premios:", "Categoría",
        "Nombre de la empresa", "Número de teléfono", "Página web", "Dirección",
        "Coste medio de proyectos", "Seguidores", "Enlaces a redes sociales",
        "EMPRESA", "DESCUBRE HOUZZ", "SÍGUENOS EN", "Service Area",
        "Services Provided", "Areas Served", "Awards", "Category",
        "Business Name", "Phone Number", "Website", "Address",
        "Typical Job Costs", "Typical Job Cost", "Followers", "Social Links", "Socials",
        "Business Details", "Contact", "Cost", "License Number",
        "Número de licencia", "Número de Identificación", "Number of Projects",
    }
    _NON_PROJECT_PATTERNS = re.compile(
        r"^(How is .+ rated\??|What .+ cost\??|Do .+ offer\??|"
        r"¿Cómo está valorad|¿Cuánto cuesta|"
        r"Pregunt|FAQ|Preguntas frecuentes|Questions|"
        r"Professionals in |Profesionales en |"
        r"Sponsored|Patrocinado)$",
        re.IGNORECASE,
    )
    project_headers = page.css(
        "h3 a[href*='/proyectos/'], h3 a[href*='/hznb/'], "
        "h3 a[href*='/projects/'], h3 a[href*='/hznb/projects/']"
    )
    seen_titles = set()
    for a in project_headers:
        title = a.get_all_text(strip=True)
        href = a.attrib.get("href", "")
        if not href.startswith("http"):
            parsed_base = urlparse(base_url)
            href = f"{parsed_base.scheme}://{parsed_base.hostname}{href}"
        if title and len(title) > 3 and len(title) < 100 and title not in seen_titles and title not in HOUZZ_NON_PROJECTS and not _NON_PROJECT_PATTERNS.match(title):
            seen_titles.add(title)
            profile.projects.append(Project(title=title, url=href))
    if not profile.projects:
        proj_h2 = page.css("h2")
        for h in proj_h2:
            t = h.get_all_text(strip=True)
            if re.match(r"(\d+\s*)?(?:Proyectos|Projects)", t):
                all_h3 = page.css("h3")
                for h3 in all_h3:
                    h3t = h3.get_all_text(strip=True)
                    if (h3t and len(h3t) > 5 and len(h3t) < 80
                            and h3t not in HOUZZ_NON_PROJECTS
                            and not _NON_PROJECT_PATTERNS.match(h3t)
                            and not any(kw in h3t for kw in [
                                "cerca de", "profesionales en", "profesionales similares",
                                "near me", "similar professionals",
                            ])):
                        if h3t not in seen_titles:
                            seen_titles.add(h3t)
                            profile.projects.append(Project(title=h3t))
                break

    # Enrich projects by fetching their actual pages for images + description
    if profile.projects:
        _houzz_enrich_projects(profile)

    # Phone fallback
    if not profile.phone:
        phone_match = re.search(r"(?:Número de teléfono|Phone Number)\s*(\+?\d[\d\s\-]{6,})", body_text)
    if phone_match:
        profile.phone = phone_match.group(1).strip()

    web_match = re.search(
        r"(?:Página web|Website)\s*(https?://[^\s]+|www\.[^\s]+|[a-zA-Z0-9][-a-zA-Z0-9]*\.[a-z]{2,6}[^\s]*)",
        body_text,
    )
    if web_match:
        w = web_match.group(1).strip()
        if not w.startswith("http"):
            w = "https://" + w
        profile.website = w

    # Services
    for heading in ("Servicios prestados", "Services Provided"):
        svc_idx = body_text.find(heading)
        if svc_idx < 0:
            continue
        svc_chunk = body_text[svc_idx + len(heading) : svc_idx + len(heading) + 600]
        next_heading = re.search(
            r"(?:Zonas de trabajo|Premios|Categoría|\d+\s*(?:Proyectos|Projects)|Detalles|Service Area|Awards|Cost)",
            svc_chunk,
        )
        svc_text = svc_chunk[: next_heading.start() if next_heading else 400].strip().lstrip(":")
        for item in re.split(r"[,\n]", svc_text):
            item = item.strip()
            if 3 < len(item) < 60:
                profile.services.append(item)
        break

    # Reviews + Business details + Credentials — all via a single Playwright session
    try:
        browser = _get_playwright_browser()
        ctx = browser.new_context(
            locale="en-US",
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 900},
        )
        pw_page = ctx.new_page()
        try:
            import time as _t
            pw_page.goto(base_url, timeout=25000, wait_until="domcontentloaded")
            _t.sleep(2)
            try:
                pw_page.click("button:has-text('Accept'), button:has-text('Aceptar')", timeout=3000)
            except Exception:
                pass

            # ── TAB 0: About / Sobre nosotros (full description) ──
            for sel in (
                "a:has-text('About')", "button:has-text('About')",
                "a:has-text('Sobre nosotros')", "[role='tab']:has-text('About')",
            ):
                try:
                    pw_page.click(sel, timeout=4000)
                    _t.sleep(1.5)
                    break
                except Exception:
                    continue
            about_body = pw_page.inner_text("body")
            about_pw = _extract_houzz_about_from_body(about_body)
            if about_pw and len(about_pw) > len(profile.description or ""):
                profile.description = about_pw.strip()
                logger.info("Houzz About tab: expanded description to %d chars", len(profile.description))

            # ── TAB 1: Business details (license, address, cost) ──
            for sel in (
                "a:has-text('Business')", "button:has-text('Business')",
                "a:has-text('Empresa')", "[role='tab']:has-text('Business')",
            ):
                try:
                    pw_page.click(sel, timeout=4000)
                    _t.sleep(2)
                    break
                except Exception:
                    continue

            biz_body = pw_page.inner_text("body")

            for pat in (
                r"License Number\s*\n\s*(.+)",
                r"Número de licencia\s*\n\s*(.+)",
                r"License\s*#?\s*:?\s*([A-Z0-9#\-]+\d{4,})",
            ):
                lm = re.search(pat, biz_body)
                if lm:
                    val = lm.group(1).strip()
                    if 3 < len(val) < 60:
                        profile.credentials.append(Credential(
                            type="license", label="License Number", value=val, verified=True,
                        ))
                        logger.info("Houzz credential: license = %s", val)
                    break

            if not profile.address:
                for pat in (
                    r"Address\s*\n\s*([\s\S]+?)(?=\n\s*(?:Typical Job|License|Followers|Socials|Back to))",
                    r"Dirección\s*\n\s*([\s\S]+?)(?=\n\s*(?:Coste medio|Número de licencia|Seguidores|Redes|Volver))",
                ):
                    am = re.search(pat, biz_body)
                    if am:
                        addr_lines = [l.strip() for l in am.group(1).strip().split("\n") if l.strip()]
                        if addr_lines:
                            profile.address = ", ".join(addr_lines)
                            logger.info("Houzz address: %s", profile.address[:80])
                        break

            for pat in (
                r"Typical Job Cost\s*\n\s*(.+)",
                r"Coste medio de proyectos\s*\n\s*(.+)",
            ):
                cm = re.search(pat, biz_body)
                if cm:
                    profile.typical_job_cost = cm.group(1).strip()[:100]
                    logger.info("Houzz typical cost: %s", profile.typical_job_cost)
                    break

            if "Verified License" in biz_body or "Licencia verificada" in biz_body:
                profile.credentials.append(Credential(
                    type="badge", label="Verified License", value="Houzz Verified", verified=True,
                ))

            hires_m = re.search(r"(\d+)\s*Hires on Houzz", biz_body)
            if hires_m:
                profile.credentials.append(Credential(
                    type="badge", label="Hires on Houzz", value=hires_m.group(1),
                ))

            # ── TAB 2: Credentials (awards & badges) ──
            for sel in (
                "a:has-text('Credentials')", "button:has-text('Credentials')",
                "a:has-text('Credenciales')", "[role='tab']:has-text('Credentials')",
            ):
                try:
                    pw_page.click(sel, timeout=4000)
                    _t.sleep(1.5)
                    break
                except Exception:
                    continue

            cred_body = pw_page.inner_text("body")
            awards_m = re.search(r"(\d+)\s*Houzz Awards?", cred_body)
            if awards_m:
                profile.credentials.append(Credential(
                    type="award", label="Houzz Awards", value=awards_m.group(1),
                ))
            badges_m = re.search(r"(\d+)\s*Houzz Badges?", cred_body)
            if badges_m:
                profile.credentials.append(Credential(
                    type="badge", label="Houzz Badges", value=badges_m.group(1),
                ))
            boh_m = re.search(r"(\d+)x?\s*Best of Houzz", cred_body, re.IGNORECASE)
            if boh_m:
                profile.credentials.append(Credential(
                    type="award", label="Best of Houzz", value=f"{boh_m.group(1)}x winner",
                ))

            logger.info("Houzz credentials: %d items", len(profile.credentials))

            # ── TAB 3: Reviews ──
            for tab_sel in (
                "a:has-text('Reviews'), button:has-text('Reviews')",
                "a:has-text('Valoraciones'), button:has-text('Valoraciones')",
            ):
                try:
                    pw_page.click(tab_sel, timeout=4000)
                    _t.sleep(2)
                    break
                except Exception:
                    continue
            review_text = pw_page.inner_text("body")
            review_blocks = re.finditer(
                r"(\d)\s*(?:de\s*5\s*estrellas|out of 5 stars)\s*(.*?)(?=\d\s*(?:de\s*5\s*estrellas|out of 5 stars)|Escribe una valoración|Write a Review|$)",
                review_text, re.DOTALL,
            )
            seen_texts: set[str] = set()
            noise_starts = (
                "Sobre nosotros", "Proyectos", "Empresa", "Credenciales",
                "Valoraciones", "Álbum", "Volver", "Escribe una", "Ver todos",
                "Leer más", "Leer valoración", "Servicios prestados", "Zonas de trabajo",
                "About Us", "Projects", "Business", "Credentials",
                "Write a", "See all", "Read more", "Services Provided",
            )
            for m in review_blocks:
                rating = float(m.group(1))
                block = m.group(2).strip()
                lines = [l.strip() for l in block.split("\n") if l.strip() and len(l.strip()) > 3]
                lines = [l for l in lines if not any(l.startswith(n) for n in noise_starts)]
                if any(re.search(r"(\d+\s*(?:valoracion|reviews|Reviews|Hires on Houzz))", l) for l in lines):
                    continue
                if not lines:
                    continue
                author = ""
                date_str = ""
                text_parts = []
                for line in lines:
                    if re.match(r"^\d{1,2}\s+de\s+\w+\s+de\s+\d{4}$", line):
                        date_str = line
                    elif re.match(r"^(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},\s+\d{4}$", line):
                        date_str = line
                    elif not author and len(line) < 40 and not re.search(r"\d", line) and "Responde" not in line and "Leer" not in line and "Read" not in line:
                        author = line
                    elif "Responde" in line or "Response" in line or re.match(r"^\d+\s*(?:valoracion|review)", line, re.IGNORECASE):
                        continue
                    else:
                        text_parts.append(line)
                text = " ".join(text_parts)[:500]
                if not text or text in seen_texts:
                    continue
                seen_texts.add(text)
                profile.reviews.append(Review(author=author, rating=rating, date=date_str, text=text))
            logger.info("Houzz Playwright reviews: %d parsed", len(profile.reviews))
        finally:
            pw_page.close()
            ctx.close()
    except Exception as e:
        logger.warning("Houzz Playwright reviews/credentials failed (non-fatal): %s", e)

    # Cover images
    profile.cover_images = profile.portfolio_images[:3]

    # Avatar fallback
    if not profile.avatar_url:
        avatar_imgs = page.css('img[src*="w240"]')
        if avatar_imgs:
            profile.avatar_url = avatar_imgs[0].attrib.get("src", "")

    # Crawl linked business website (from “Página web”) for extra assets
    if profile.website:
        h = _hostname(profile.website)
        if h and "houzz" not in h and "habitissimo" not in h:
            try:
                merge_website_into_profile(profile, profile.website)
            except Exception as e:
                logger.warning("Houzz merge_website_into_profile: %s", e)

    logger.info(f"Houzz scrape complete: {profile.name}, "
                f"{len(profile.portfolio_images)} photos, "
                f"{len(profile.reviews)} reviews, "
                f"{len(profile.projects)} projects")
    return profile


# ─── CronoShare Scraper — server-rendered HTML, no JS needed ────────

def scrape_cronoshare(url: str) -> ProfileResult:
    """Scrape a CronoShare professional profile (cronoshare.com/croner-*)."""
    base_url = url.rstrip("/")
    logger.info("Scraping CronoShare: %s", base_url)

    profile = ProfileResult(source="cronoshare", source_url=base_url)

    try:
        page = fetcher.get(base_url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CronoShare fetch failed: {e}")

    if page.status != 200:
        raise HTTPException(status_code=502, detail=f"CronoShare returned {page.status}")

    body = page.css("body")
    if not body:
        raise api_error(502, "CronoShare page has no body")

    text = body[0].get_all_text(strip=True) if body else ""
    if len(text) < 50:
        raise api_error(404, "CronoShare profile not found or empty")

    # Name — from <h1> or <h2> at top of profile
    h1_els = page.css("h1")
    if h1_els:
        profile.name = h1_els[0].get_all_text(strip=True)

    # Location — "Es de <City> (<Province>)" pattern
    loc_match = re.search(r'Es de\s+(.+?)(?:\s*\(|$)', text)
    if loc_match:
        profile.location = loc_match.group(1).strip()

    # Registration date
    reg_match = re.search(r'Registrado el\s+([\d-]+)', text)

    # Description — the "Así es <Name>" section
    desc_section = ""
    h2_els = page.css("h2")
    for h2 in h2_els:
        h2_text = h2.get_all_text(strip=True)
        if "Así es" in h2_text:
            sibling = h2.parent
            if sibling:
                desc_section = sibling.get_all_text(strip=True)
                desc_section = desc_section.split("Área de trabajo")[0].strip()
                if "Así es" in desc_section:
                    desc_section = desc_section.split("Así es", 1)[-1]
                    # Remove the name part after "Así es"
                    desc_section = re.sub(r'^[^a-záéíóúñ]*[A-Z][^\n]{0,40}\n?', '', desc_section, count=1).strip()
            break

    if desc_section:
        profile.description = desc_section
        profile.raw_about = desc_section

    # Services — listed under "Servicios" section as "Category: svc1 | svc2 | svc3"
    services_list: list[str] = []
    raw_html = str(page.html_content) if hasattr(page, 'html_content') else ""
    if not raw_html:
        try:
            raw_html = page.body.decode("utf-8", errors="replace") if hasattr(page, 'body') else ""
        except Exception:
            raw_html = ""

    svc_match = re.search(
        r'Servicios\s*</h2>(.*?)(?:<h2|Servicios relacionados)',
        raw_html,
        re.DOTALL | re.IGNORECASE,
    )
    if svc_match:
        svc_html = svc_match.group(1)
        svc_text_clean = re.sub(r'<[^>]+>', ' ', svc_html)
        for line in svc_text_clean.split('\n'):
            line = line.strip()
            if not line:
                continue
            cat_match = re.match(r'(.+?):\s*(.*)', line)
            items_str = cat_match.group(2) if cat_match else line
            for item in items_str.split('|'):
                item = item.strip()
                if item and len(item) > 2:
                    services_list.append(item)
    else:
        svc_text_match = re.search(
            r'Servicios\s+(.*?)(?:Empleos|Estudios|Idiomas|Valoraciones)',
            text,
            re.DOTALL,
        )
        if svc_text_match:
            svc_text = svc_text_match.group(1)
            for piece in re.split(r'\|', svc_text):
                piece = piece.strip()
                piece = re.sub(r'^[^:]+:\s*', '', piece).strip()
                if piece and len(piece) > 2:
                    services_list.append(piece)

    if services_list:
        profile.trade = services_list[0] if len(services_list) == 1 else ", ".join(services_list[:5])
        profile.services = "; ".join(services_list)

    # Employment / Experience
    emp_match = re.search(r'Empleos\s+(.*?)(?:Estudios|Idiomas|Valoraciones|Servicios relacionados|$)', text, re.DOTALL)
    if emp_match:
        emp_text = emp_match.group(1).strip()
        if emp_text and len(emp_text) > 5:
            if profile.description:
                profile.description += f"\n\nExperience: {emp_text}"
            else:
                profile.description = f"Experience: {emp_text}"

    # Education
    edu_match = re.search(r'Estudios\s+(.*?)(?:Idiomas|Valoraciones|Servicios relacionados|$)', text, re.DOTALL)
    if edu_match:
        edu_text = edu_match.group(1).strip()
        if edu_text and len(edu_text) > 2:
            if profile.description:
                profile.description += f"\n\nEducation: {edu_text}"

    # Languages
    lang_match = re.search(r'Idiomas\s+(.*?)(?:Valoraciones|Servicios relacionados|$)', text, re.DOTALL)

    # Reviews
    review_blocks = re.findall(
        r'(\d[,.]?\d?)\s*/\s*10.*?Escribir una valoración',
        text,
        re.DOTALL,
    )

    # Try to parse individual reviews from the page
    _parse_cronoshare_reviews(profile, text, page)

    # Avatar / profile image
    for img in page.css("img"):
        src = img.attrib.get("src", "") or img.attrib.get("data-src", "")
        alt = (img.attrib.get("alt", "") or "").lower()
        if not src or not src.startswith("http"):
            continue
        if profile.name and profile.name.lower().split()[0] in alt:
            profile.avatar_url = src
            break
        if "croner" in src or "profile" in src or "avatar" in src:
            profile.avatar_url = src
            break

    # Portfolio images from the page
    for img in page.css("img"):
        src = img.attrib.get("src", "") or img.attrib.get("data-src", "")
        if not src or not src.startswith("http"):
            continue
        if any(skip in src.lower() for skip in ("icon", "logo", "avatar", "star", "rating", "sprite", "confianza")):
            continue
        if src not in profile.portfolio_images and src != profile.avatar_url:
            profile.portfolio_images.append(src)

    # Validation badges (check raw HTML since badges use img alt text)
    badges: list[str] = []
    if "Email validado" in raw_html or "Email validado" in text:
        badges.append("Email verified")
    if "Teléfono validado" in raw_html or "Teléfono validado" in text:
        badges.append("Phone verified")
    if "Responde rápido" in raw_html or "Responde rápido" in text:
        badges.append("Fast responder")
    hired_match = re.search(r'(\d+)\s*veces?\s*contratado', raw_html + " " + text)
    if hired_match:
        badges.append(f"Hired {hired_match.group(1)} times on CronoShare")
    if badges:
        profile.credentials = badges

    logger.info(
        "CronoShare scrape done: name=%s, location=%s, services=%d, reviews=%d, rating=%s",
        profile.name, profile.location, len(services_list), len(profile.reviews), profile.rating,
    )
    return profile


def _parse_cronoshare_reviews(profile: ProfileResult, text: str, page) -> None:
    """Parse client reviews from a CronoShare profile page."""
    # CronoShare review format:
    #   <rating>/10
    #   <author> opina:
    #   <review text>
    review_pattern = re.compile(
        r'(\d[,.]?\d?)\s*/\s*10\s*'
        r'([A-ZÁÉÍÓÚÑ][a-záéíóúñA-Z ]+?)\s*(?:opina|dice|comenta)\s*:?\s*'
        r'"?([^"]{10,500}?)"?'
        r'(?:\s*(?:Leer más|Escribir|Valoraciones|\d/10|$))',
        re.DOTALL,
    )

    seen_keys: set[tuple] = set()
    for m in review_pattern.finditer(text):
        rating_str, author, body = m.groups()
        rating = float(rating_str.replace(",", "."))
        author = author.strip()
        body = body.strip()
        key = (author.lower(), body[:40].lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        profile.reviews.append(Review(
            author=author,
            rating=rating,
            text=body,
        ))

    # Also try the simpler "opina de <ProName>:" format from listing pages
    simple_pattern = re.compile(
        r'([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)\s+opina de\s+[^:]+:\s*"?([^"]{10,500}?)"?\s*(?:\n|$)',
    )
    for m in simple_pattern.finditer(text):
        author, body = m.groups()
        author = author.strip()
        body = body.strip()
        key = (author.lower(), body[:40].lower())
        if key in seen_keys:
            continue
        seen_keys.add(key)
        profile.reviews.append(Review(
            author=author,
            text=body,
        ))

    # Overall rating from the header
    rating_match = re.search(r'(\d[,.]?\d?)\s*/\s*10', text)
    if rating_match:
        profile.rating = float(rating_match.group(1).replace(",", "."))

    review_count_match = re.search(r'\((\d+)\s*(?:valoracion|opinión|review)', text, re.IGNORECASE)
    if review_count_match:
        profile.review_count = int(review_count_match.group(1))
    elif profile.reviews:
        profile.review_count = len(profile.reviews)

    if not profile.rating and profile.reviews:
        rated = [r.rating for r in profile.reviews if r.rating is not None]
        if rated:
            profile.rating = round(sum(rated) / len(rated), 1)


# ─── Hogami (Leroy Merlin) Scraper — uses their public JSON API ────

_HOGAMI_API_KEY = os.environ.get("HOGAMI_API_KEY", "")


def _hogami_slug_from_url(url: str) -> str:
    path = urlparse(url).path.rstrip("/")
    # e.g. /profesionales/didier-santiago-arazola-martagon
    return path.split("/")[-1]


def scrape_hogami(url: str) -> ProfileResult:
    slug = _hogami_slug_from_url(url)
    logger.info("Scraping Hogami via API: slug=%s", slug)

    profile = ProfileResult(source="hogami", source_url=url)

    from core import http_client_sync
    with http_client_sync(
        timeout=20,
        follow_redirects=True,
        headers={
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
            "Accept": "application/json",
        },
    ) as client:
        # --- Profile ---
        prof_url = f"https://api-client.leroymerlin.es/client/v2/professionals/{slug}/public-profile?key={_HOGAMI_API_KEY}"
        r = client.get(prof_url)
        if r.status_code != 200:
            raise HTTPException(status_code=502, detail=f"Hogami API returned {r.status_code}")

        data = r.json().get("data", {})
        info = data.get("informationPage", {})
        pro_id = info.get("id")

        profile.name = info.get("commercialName") or f"{info.get('name','')} {info.get('lastName','')}".strip()
        profile.description = info.get("description", "")
        profile.avatar_url = info.get("avatar", "")
        profile.raw_about = info.get("slogan", "")

        addrs = info.get("addresses") or []
        if addrs:
            a = addrs[0]
            parts = [a.get("city", ""), a.get("province", "")]
            profile.location = ", ".join(p for p in parts if p)

        provinces = info.get("provincesProfessional") or []
        if provinces and not profile.location:
            profile.location = ", ".join(provinces)

        # Services → trade
        services = data.get("services", {})
        if services:
            top_categories = list(services.keys())[:3]
            profile.trade = ", ".join(top_categories)

        # Portfolio images — Hogami profile doesn't have a gallery, but avatar exists
        if profile.avatar_url:
            profile.portfolio_images.append(profile.avatar_url)

        # --- Reviews ---
        if pro_id:
            rev_url = (
                f"https://api-client.leroymerlin.es/client/v1/professionals/{pro_id}/ratings"
                f"?size=100&page=0&sort=createDate,desc&key={_HOGAMI_API_KEY}"
            )
            r2 = client.get(rev_url)
            if r2.status_code == 200:
                rev_data = r2.json().get("data", {})
                total = rev_data.get("totalElements", 0)
                profile.review_count = total
                for item in rev_data.get("content", []):
                    from datetime import datetime, timezone
                    ts = item.get("createDate")
                    date_str = ""
                    if ts:
                        try:
                            dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc)
                            date_str = dt.strftime("%B %Y")
                        except Exception:
                            pass

                    profile.reviews.append(Review(
                        author=item.get("clientName", ""),
                        rating=item.get("generalRating"),
                        text=item.get("opinion", ""),
                        date=date_str,
                    ))

                # Compute average rating
                ratings = [rv.rating for rv in profile.reviews if rv.rating is not None]
                if ratings:
                    profile.rating = round(sum(ratings) / len(ratings), 1)

        # Services as projects (Hogami doesn't have project pages)
        for cat_name, svc_list in services.items():
            svc_titles = [s.get("title", "") for s in svc_list if s.get("title")]
            if svc_titles:
                profile.projects.append(Project(
                    title=cat_name,
                    description=", ".join(svc_titles),
                    images=[],
                    url="",
                ))

        # Website URL from API — merge external site when available
        website_url = info.get("web") or info.get("website") or info.get("url") or ""
        if not website_url:
            for addr in addrs:
                website_url = addr.get("web") or addr.get("website") or ""
                if website_url:
                    break
        if website_url and not website_url.startswith("http"):
            website_url = "https://" + website_url
        if website_url:
            h = _hostname(website_url)
            if h and "leroymerlin" not in h and "hogami" not in h:
                profile.website = website_url

        profile.cover_images = profile.portfolio_images[:3]

        # Merge external website (photos + richer description) when available
        if profile.website:
            try:
                merge_website_into_profile(profile, profile.website)
            except Exception as e:
                logger.warning("Hogami merge_website failed for %s: %s", profile.website, e)

        logger.info(
            "Hogami scrape done: name=%s, reviews=%s, services=%s",
            profile.name, len(profile.reviews), len(profile.projects),
        )
        return profile


# ─── Generic Website Crawler ───────────────────────────────────────

def _extract_emails_from_page(page) -> list[str]:
    """Pull email addresses from mailto: links and visible text."""
    found: list[str] = []
    for a in page.css("a[href^='mailto:']"):
        addr = (a.attrib.get("href") or "").replace("mailto:", "").split("?")[0].strip()
        if addr and "@" in addr and addr not in found:
            found.append(addr)
    return found


def scrape_website(url: str) -> ProfileResult:
    """Crawl the entry URL plus prioritized same-site pages; store per-page chunks for LLM structuring."""
    parsed = urlparse(url)
    if not parsed.scheme.startswith("http"):
        raise api_error(400, "URL must be http(s)")
    base_domain = f"{parsed.scheme}://{parsed.hostname}"

    MAX_HOME_TEXT = 20_000
    MAX_SUBPAGE_TEXT = 12_000
    MAX_CRAWL_PAGES = 25
    MAX_PORTFOLIO_IMAGES = 120

    logger.info("Website import: seed=%s base=%s", url, base_domain)
    profile = ProfileResult(source="website", source_url=url)
    all_images_seen: set[str] = set()

    def _add_images(urls: list[str]):
        for u in urls:
            if len(profile.portfolio_images) >= MAX_PORTFOLIO_IMAGES:
                return
            if u not in all_images_seen:
                all_images_seen.add(u)
                profile.portfolio_images.append(u)

    # ── Home page ───────────────────────────────────────────────────
    page = fetcher.get(url)
    if page.status != 200:
        raise HTTPException(status_code=502, detail=f"Website returned {page.status}")

    bodies = page.css("body")
    body_text = bodies[0].get_all_text(strip=True) if bodies else ""

    ld = _extract_jsonld_business_fields(page)
    og_title = _meta_content(page, meta_property="og:title")
    og_desc = _meta_content(page, meta_property="og:description")
    og_img = _meta_content(page, meta_property="og:image") or _meta_content(page, meta_name="twitter:image")

    title_el = page.css("title::text")
    h1_el = page.css("h1::text")
    h1_txt = h1_el.get().strip() if h1_el else ""
    title_txt = title_el.get().strip() if title_el else ""

    profile.name = (ld.get("name") or og_title or h1_txt or title_txt or parsed.hostname or "").strip()
    profile.name = re.sub(r"\s*[|\-–—]\s*.*$", "", profile.name).strip() or profile.name

    profile.description = (og_desc or ld.get("description") or "").strip()
    if not profile.description:
        meta_desc = page.css('meta[name="description"]')
        if meta_desc:
            profile.description = (meta_desc[0].attrib.get("content") or "").strip()
    if not profile.description:
        for p in page.css("p"):
            t = p.get_all_text(strip=True)
            if t and len(t) > 50:
                profile.description = t[:3000]
                break

    best_hp = _best_description_from_homepage(page)
    if best_hp and len(best_hp) > len(profile.description or ""):
        profile.description = best_hp

    if ld.get("phone"):
        profile.phone = ld["phone"]
    if not profile.phone:
        phone_links = page.css('a[href^="tel:"]')
        if phone_links:
            profile.phone = phone_links[0].attrib.get("href", "").replace("tel:", "").strip()

    emails = _extract_emails_from_page(page)
    if emails:
        profile.email = emails[0]

    # ── Logo / avatar detection ────────────────────────────────────
    # Priority: JSON-LD logo > apple-touch-icon > shortcut icon > favicon
    if ld.get("logo_url") and str(ld["logo_url"]).startswith("http"):
        profile.avatar_url = str(ld["logo_url"])
    if not profile.avatar_url:
        for sel in (
            'link[rel="apple-touch-icon"]',
            'link[rel="apple-touch-icon-precomposed"]',
            'link[rel="icon"][type="image/png"]',
            'link[rel="shortcut icon"]',
            'link[rel="icon"]',
        ):
            els = page.css(sel)
            if els:
                href = els[0].attrib.get("href", "")
                if href:
                    abs_url = urljoin(url, href)
                    if abs_url.startswith("http") and ".svg" not in abs_url.lower():
                        profile.avatar_url = abs_url
                        break
    if not profile.avatar_url:
        favicon_guess = f"{base_domain}/favicon.ico"
        try:
            resp = fetcher.get(favicon_guess)
            if resp.status == 200:
                profile.avatar_url = favicon_guess
        except Exception:
            pass
    if profile.avatar_url:
        logger.info("Website import: avatar/logo detected — %s", profile.avatar_url)

    # Homepage images
    home_imgs: list[str] = []
    if og_img and og_img.startswith("http") and not _is_noise_image_website_portfolio(og_img):
        home_imgs.append(og_img)
    if ld.get("logo_url") and str(ld["logo_url"]).startswith("http"):
        home_imgs.insert(0, str(ld["logo_url"]))
    home_imgs.extend(_collect_image_urls_from_page(page, base_domain))
    _add_images(home_imgs)

    home_text = body_text[:MAX_HOME_TEXT]
    profile.page_chunks.append(PageChunk(url=url, text=home_text, image_urls=home_imgs[:40]))
    profile.raw_about = f"--- {url} (home) ---\n{home_text}\n"

    # ── Internal pages ──────────────────────────────────────────────
    internal_urls = _discover_internal_urls(url, page, parsed)
    logger.info("Website import: discovered %s internal URLs (first 8): %s",
                len(internal_urls), internal_urls[:8])

    crawled = 0
    for link in internal_urls[:MAX_CRAWL_PAGES]:
        try:
            sub_page = fetcher.get(link)
            if sub_page.status != 200:
                logger.warning("Website crawl skip %s status=%s", link, sub_page.status)
                continue
            crawled += 1

            sb = sub_page.css("body")
            sub_text = sb[0].get_all_text(strip=True) if sb else ""
            sub_text = sub_text[:MAX_SUBPAGE_TEXT]

            sub_imgs = _collect_image_urls_from_page(sub_page, base_domain)
            _add_images(sub_imgs)

            profile.page_chunks.append(PageChunk(url=link, text=sub_text, image_urls=sub_imgs[:40]))
            profile.raw_about += f"\n\n--- {link} ---\n{sub_text}\n"

            if not profile.email:
                sub_emails = _extract_emails_from_page(sub_page)
                if sub_emails:
                    profile.email = sub_emails[0]

        except Exception as e:
            logger.warning("Failed to crawl %s: %s", link, e)

    profile.cover_images = profile.portfolio_images[:3]
    profile.website = url

    logger.info(
        "Website crawl complete: name=%s pages=%s images=%s chunks=%s raw_about_chars=%s",
        profile.name, crawled + 1, len(profile.portfolio_images),
        len(profile.page_chunks), len(profile.raw_about or ""),
    )
    return profile


# ─── LLM structuring (Bedrock → OpenRouter fallback) ────────────────
# Primary: Claude Sonnet 4.6 on Bedrock. Falls back to OpenRouter if
# Bedrock is unavailable (billing, throttling, region issues).

import os
from pathlib import Path
from typing import Any

from core import bootstrap_init as _boot; _boot()
from core import bedrock_client

AWS_REGION = os.getenv("AWS_REGION", "eu-west-3")
STRUCTURE_MODEL = os.getenv("PROFILE_STRUCTURE_MODEL", "us.anthropic.claude-sonnet-4-6")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_MODEL = "anthropic/claude-sonnet-4.6"

def _get_bedrock():
    return bedrock_client(AWS_REGION, read_timeout=120, connect_timeout=10, max_attempts=1)


def _text_from_converse(response: dict[str, Any]) -> str:
    msg = response.get("output", {}).get("message", {})
    parts: list[str] = []
    for block in msg.get("content", []) or []:
        if isinstance(block, dict) and "text" in block:
            parts.append(block["text"])
    return "\n".join(parts).strip()


def _openrouter_chat(system: str, user: str, max_tokens: int = 8192, temperature: float = 0.1) -> str:
    """Fallback LLM call via the ``llm`` package when Bedrock fails."""
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set — cannot fall back")
    from llm import chat_sync
    data = chat_sync(
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        model=OPENROUTER_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=120.0,
    )
    return data["choices"][0]["message"]["content"].strip()


_STRUCTURE_SYSTEM = """\
You are a profile-structuring assistant for a tradesperson marketplace app.
You receive the raw crawled text of a tradesperson or company website, divided
into per-page chunks.  Your job is to extract a structured profile that is
**faithful to the original content** — do not invent information.

Return ONLY valid JSON with exactly these fields (omit any you cannot fill).
No markdown fences, no commentary, no explanation — just the JSON object:

{
  "name": "Business or person name",
  "description": "1-3 sentence summary of who they are and what they do, in the language of the website",
  "location": "City / region if mentioned (look for addresses, service area descriptions, WhatsApp messages mentioning a city)",
  "trade": "Primary trade or industry (e.g. solar installation, plumbing, general construction)",
  "phone": "Phone number if found",
  "email": "Email if found",
  "services": ["list", "of", "services", "they offer"],
  "reviews": [
    {
      "author": "Reviewer name",
      "rating": 5,
      "text": "Full review text as written on the site",
      "date": "Date if shown, else null"
    }
  ],
  "projects": [
    {
      "title": "Project or portfolio item title",
      "description": "Brief description",
      "image_urls": ["urls of images that belong to THIS project"]
    }
  ],
  "people": [
    {
      "name": "Person name",
      "role": "Their role (owner, electrician, project manager...)",
      "bio": "Short bio if available",
      "image_url": "Portrait/avatar URL if found"
    }
  ],
  "years_experience": null,
  "portfolio_image_urls": ["best images that represent their work — max 30, ordered by quality/relevance"],
  "avatar_url": "URL of their logo or team photo if found"
}

Rules:
- Use the SAME LANGUAGE as the website (Spanish site → Spanish output).
- REVIEWS are critical — many websites embed customer reviews/testimonials
  with star ratings and author names. Extract ALL of them. Look for star
  symbols (★), "Valorado con X de 5", rating widgets, testimonial sections.
  Include the full review text, not a summary.
- For companies with multiple team members, list each person.
- For solo tradespeople, still include them in "people".
- "projects" should capture portfolio items, completed works, case studies.
  Attach the right image URLs from the page they appeared on.
- "portfolio_image_urls" = the BEST images representing their work.
  Exclude icons, UI elements, stock photos, logos, social media buttons.
- If you cannot determine a field, omit it entirely from JSON.
- Do NOT make up information. If the website is vague, reflect that.
"""


def _converse_with_fallback(system: str, user: str, *, max_tokens: int = 8192, temperature: float = 0.1, label: str = "call") -> str:
    """Try Bedrock Converse, fall back to OpenRouter on any failure."""
    model_id = STRUCTURE_MODEL
    try:
        client = _get_bedrock()
        kwargs: dict[str, Any] = {
            "modelId": model_id,
            "messages": [{"role": "user", "content": [{"text": user}]}],
            "system": [{"text": system}],
            "inferenceConfig": {"maxTokens": max_tokens, "temperature": temperature},
        }
        logger.info("LLM %s: sending %d chars to Bedrock %s", label, len(user), model_id)
        try:
            response = client.converse(**kwargs)
        except Exception as e:
            err = str(e).lower()
            if "system" in err or "unsupported" in err or "validation" in err:
                combined = system + "\n\n---\n\n" + user
                response = client.converse(
                    modelId=model_id,
                    messages=[{"role": "user", "content": [{"text": combined}]}],
                    inferenceConfig={"maxTokens": max_tokens, "temperature": temperature},
                )
            else:
                raise
        raw_text = _text_from_converse(response)
        usage = response.get("usage", {})
        logger.info("LLM %s OK | model=%s | in=%s | out=%s",
                     label, model_id, usage.get("inputTokens", "?"), usage.get("outputTokens", "?"))
        return raw_text
    except Exception as bedrock_err:
        logger.warning("LLM %s: Bedrock failed (%s), trying OpenRouter…", label, str(bedrock_err)[:120])
        try:
            raw_text = _openrouter_chat(system, user, max_tokens=max_tokens, temperature=temperature)
            logger.info("LLM %s OK via OpenRouter | chars=%d", label, len(raw_text))
            return raw_text
        except Exception as or_err:
            logger.error("LLM %s: OpenRouter also failed: %s", label, str(or_err)[:200])
            raise


def structure_profile_with_llm(profile: ProfileResult) -> ProfileResult:
    """Structure the raw crawl with LLM. Tries Bedrock first, falls back to OpenRouter."""
    MAX_CHUNKS_FOR_LLM = 8
    MAX_CHARS_PER_CHUNK = 3000
    MAX_TOTAL_CHARS = 40_000

    priority_chunks = profile.page_chunks[:MAX_CHUNKS_FOR_LLM]

    chunks_text = ""
    for chunk in priority_chunks:
        truncated = chunk.text[:MAX_CHARS_PER_CHUNK]
        img_list = ", ".join(chunk.image_urls[:10]) if chunk.image_urls else "(none)"
        chunks_text += f"\n\n=== PAGE: {chunk.url} ===\n{truncated}\n\nImages on this page: {img_list}\n"

    if len(chunks_text) > MAX_TOTAL_CHARS:
        chunks_text = chunks_text[:MAX_TOTAL_CHARS] + "\n\n... (truncated)"

    prompt = f"Here is the crawled content of the website {profile.source_url}:\n{chunks_text}"

    raw_text = _converse_with_fallback(_STRUCTURE_SYSTEM, prompt, max_tokens=8192, temperature=0.1, label="structuring")

    try:
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1] if "\n" in raw_text else raw_text[3:]
            if raw_text.endswith("```"):
                raw_text = raw_text[:-3]
        # Handle Qwen's thinking tags if present
        if "<think>" in raw_text:
            think_end = raw_text.find("</think>")
            if think_end != -1:
                raw_text = raw_text[think_end + len("</think>"):].strip()
        # Find the JSON object in the response
        json_start = raw_text.find("{")
        json_end = raw_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            raw_text = raw_text[json_start:json_end]
        data = json.loads(raw_text)
    except (json.JSONDecodeError, ValueError, AttributeError) as e:
        logger.error("LLM structuring: failed to parse JSON: %s — raw: %.500s", e, raw_text[:500])
        return profile

    logger.info("LLM structuring: parsed successfully, keys=%s", list(data.keys()))

    if data.get("name") and len(data["name"]) > 2:
        profile.name = data["name"]
    if data.get("description"):
        profile.description = data["description"]
    if data.get("location"):
        profile.location = data["location"]
    if data.get("trade"):
        profile.trade = data["trade"]
    if data.get("phone") and not profile.phone:
        profile.phone = data["phone"]
    if data.get("email") and not profile.email:
        profile.email = data["email"]
    if data.get("services"):
        profile.services = [s for s in data["services"] if isinstance(s, str)]
    if data.get("years_experience"):
        try:
            profile.years_experience = int(data["years_experience"])
        except (ValueError, TypeError):
            pass
    if data.get("avatar_url") and str(data["avatar_url"]).startswith("http"):
        profile.avatar_url = str(data["avatar_url"])

    if data.get("projects"):
        profile.projects = []
        for p in data["projects"]:
            if not isinstance(p, dict):
                continue
            proj_imgs = [u for u in (p.get("image_urls") or []) if isinstance(u, str) and u.startswith("http")]
            profile.projects.append(Project(
                title=p.get("title", ""),
                description=p.get("description", ""),
                images=proj_imgs,
                url="",
            ))

    if data.get("reviews") and not profile.reviews:
        for r in data["reviews"]:
            if not isinstance(r, dict) or not r.get("text"):
                continue
            profile.reviews.append(Review(
                author=r.get("author", ""),
                rating=float(r["rating"]) if r.get("rating") is not None else None,
                text=r["text"],
                date=r.get("date") or "",
            ))
        if profile.reviews:
            logger.info("LLM extracted %d reviews from website content", len(profile.reviews))

    if data.get("people"):
        profile.people = []
        for person in data["people"]:
            if not isinstance(person, dict):
                continue
            profile.people.append(TeamMember(
                name=person.get("name", ""),
                role=person.get("role", ""),
                bio=person.get("bio", ""),
                image_url=person.get("image_url", ""),
            ))

    if data.get("portfolio_image_urls"):
        curated = [u for u in data["portfolio_image_urls"] if isinstance(u, str) and u.startswith("http")]
        if curated:
            profile.cover_images = curated[:5]

    return profile


_REVIEW_SUMMARY_SYSTEM = """\
You write a short paragraph in the voice of a careful journalist reporting on what customers said—
not marketing copy, not a recommendation, not a hatchet job. Neutral, specific, readable.

Rules:
- SAME LANGUAGE as the review texts (if mixed, use the dominant language).
- Length: about 3–5 sentences, tight. No preamble ("In summary…").
- Be SPECIFIC where the text allows it: mention concrete themes (e.g. type of job, timing, budget
  surprises, mess/cleanliness, how they communicated, follow-up, snags). Pull detail from the reviews
  so this business does not sound interchangeable with every other tradesperson.
- FORBIDDEN: empty praise with no hook—e.g. "clients are satisfied with their work", "high quality
  service", "very professional" as the whole point. If you must use a general phrase, tie it to
  something concrete from the reviews in the same or adjacent sentence.
- If reviews conflict (some praise, some complaints), reflect that proportionally—still no invented facts.
- Do not invent jobs, numbers, or quotes not supported by the texts. If reviews are thin, say what
  little can be said and note that patterns are unclear—do not pad with generics.
- No bullet points, no markdown, no customer names, no "As an AI".
- Output: plain prose only, one paragraph. Aim under ~120 words unless the reviews force a bit more.
"""


def summarize_reviews_with_llm(profile: ProfileResult) -> ProfileResult:
    """Fill ``review_summary`` from ``profile.reviews`` via Bedrock (objective overview)."""
    if not profile.reviews:
        return profile

    chunks: list[str] = []
    for r in profile.reviews[:50]:
        t = (r.text or "").strip()
        if len(t) < 12:
            continue
        chunks.append(t[:800])
    blob = "\n---\n".join(chunks)
    if len(blob) > 14_000:
        blob = blob[:14_000] + "\n…"

    rating_note = ""
    if profile.rating is not None:
        rating_note = f"Listed aggregate rating (from directory): {profile.rating}/5. "
    if profile.review_count:
        rating_note += f"Listed review count: {profile.review_count}. "

    if len(blob) < 30:
        if profile.rating is not None and profile.review_count:
            profile.review_summary = (
                f"{rating_note.strip()}Not enough review text to synthesize themes; see expandable list if present."
            )
        return profile

    user_text = (
        f"{rating_note}\n"
        "Write one paragraph only, per the system instructions (journalistic, specific, not generic praise).\n\n"
        f"Customer review texts:\n{blob}"
    )
    logger.info("Review summary LLM: %d review snippets", len(chunks))
    try:
        out = _converse_with_fallback(
            _REVIEW_SUMMARY_SYSTEM, user_text,
            max_tokens=500, temperature=0.35, label="review_summary",
        )
    except Exception as e:
        logger.warning("Review summary LLM failed: %s", e)
        profile.review_summary = ""
        return profile

    out = out.strip()
    if out.startswith("```"):
        lines = out.split("\n")
        out = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    out = out.strip().strip('"').strip("'")
    if len(out) > 1000:
        out = out[:997] + "…"
    profile.review_summary = out
    logger.info("Review summary OK | chars=%d", len(out))
    return profile


# ─── SSE Streaming Endpoint ────────────────────────────────────────

import asyncio


async def _run_social_proof_background_by_id(contractor_id: str, phone: str) -> None:
    """Run social proof when we have a contractor ID + phone but no ProfileResult in memory.

    Called after the user submits their phone via POST /api/contractor/set-phone.
    Reads the contractor dossier, rebuilds a minimal ProfileResult, runs social proof.
    """
    try:
        from records.dossier import _select, update_trust_signals, save_and_recompute
        from messaging import run_social_proof_checks

        row = await _select("id", contractor_id)
        if not row:
            logger.warning("_run_social_proof_background_by_id: contractor %s not found", contractor_id)
            return

        canvas = row.get("canvas") or {}
        dossier = row.get("dossier") or {}
        sources = dossier.get("sources", [])
        first_source = sources[0] if sources else {}

        # Build a minimal ProfileResult so run_social_proof_checks works
        result = ProfileResult(
            source=first_source.get("source", "website"),
            source_url=first_source.get("source_url", ""),
            name=canvas.get("business_name", ""),
            location=canvas.get("location", ""),
            phone=phone,
        )
        # Carry over existing trust signals so we don't reset the score
        existing_signals = dossier.get("trust_signals")
        if existing_signals:
            result.trust_signals = TrustSignals(**{k: v for k, v in existing_signals.items() if k in TrustSignals.model_fields})

        loop = asyncio.get_event_loop()
        logger.info("Background social proof (by id) starting | contractor=%s phone=%s***",
                    contractor_id, phone[:6])
        await loop.run_in_executor(_executor, run_social_proof_checks, result)

        if result.trust_signals:
            await update_trust_signals(contractor_id, result.trust_signals.model_dump())
            await save_and_recompute(contractor_id)
            logger.info("Background social proof (by id) done | contractor=%s score=%s",
                        contractor_id, result.trust_signals.trust_score)
    except Exception as e:
        logger.warning("Background social proof (by id) failed for %s: %s", contractor_id, e)


async def _run_social_proof_background(result: "ProfileResult", contractor_id: str) -> None:
    """Run the slow social proof search after canvas delivery.

    Fires ~15 SearXNG queries to check if the contractor's phone/name appears
    in Facebook groups, Forocoches, Mediavida, or Reddit ES. Updates the dossier
    trust_signals and recomputes the canvas once results are in.

    Called via asyncio.create_task() so it never blocks the import stream.
    """
    try:
        from messaging import run_social_proof_checks
        from records.dossier import update_trust_signals, save_and_recompute

        loop = asyncio.get_event_loop()
        logger.info("Background social proof starting for contractor=%s name='%s'",
                    contractor_id, result.name[:30])

        await loop.run_in_executor(_executor, run_social_proof_checks, result)

        if result.trust_signals:
            await update_trust_signals(contractor_id, result.trust_signals.model_dump())
            await save_and_recompute(contractor_id)
            logger.info(
                "Background social proof done | contractor=%s fb=%d forum=%d score=%s",
                contractor_id,
                result.trust_signals.fb_mention_count,
                result.trust_signals.forum_mention_count,
                result.trust_signals.trust_score,
            )
    except Exception as e:
        logger.warning("Background social proof failed for %s: %s", contractor_id, e)


async def _stream_scrape(url: str, contractor_id: str = ""):
    """Generator that yields SSE events during scraping.

    If contractor_id is provided, the result is written to the contractors table
    via the contractor_dossier module and the final SSE event returns a
    ProfileUpdate-shaped canvas instead of the raw ProfileResult.
    """
    platform = detect_platform(url)

    yield f"data: {json.dumps({'type': 'status', 'message': f'Detected platform: {platform}', 'platform': platform})}\n\n"
    yield f"data: {json.dumps({'type': 'progress', 'step': 'connecting', 'percent': 10})}\n\n"
    await asyncio.sleep(0.1)

    yield f"data: {json.dumps({'type': 'progress', 'step': 'fetching_profile', 'percent': 20})}\n\n"
    await asyncio.sleep(0.1)

    loop = asyncio.get_event_loop()
    preview_sent = False
    try:
        if platform == "habitissimo":
            result = await loop.run_in_executor(
                _executor,
                lambda u=url: scrape_habitissimo(u, merge_external_site=False),
            )

            # Send preview immediately from the primary platform scrape
            _deduplicate_portfolio(result)
            yield f"data: {json.dumps({'type': 'preview', 'profile': result.model_dump()})}\n\n"
            preview_sent = True
            await asyncio.sleep(0.05)

            wh = _hostname(result.website or "")
            if wh and "habitissimo" not in wh:
                yield f"data: {json.dumps({'type': 'progress', 'step': 'crawling_linked_website', 'percent': 40, 'message': 'Crawling your linked website…'})}\n\n"
                await asyncio.sleep(0.05)
                await loop.run_in_executor(
                    _executor,
                    lambda: merge_website_into_profile(result, result.website),
                )
        elif platform == "houzz":
            result = await loop.run_in_executor(_executor, scrape_houzz, url)
        elif platform == "hogami":
            result = await loop.run_in_executor(_executor, scrape_hogami, url)
        elif platform == "cronoshare":
            result = await loop.run_in_executor(_executor, scrape_cronoshare, url)
        elif platform == "webel":
            msg = (
                "AppWebel (Webel) import is not supported — their API blocks our servers "
                "(datacenter/VPN detection). Paste your details manually or use another source."
            )
            yield f"data: {json.dumps({'type': 'error', 'message': msg})}\n\n"
            return
        else:
            yield f"data: {json.dumps({'type': 'progress', 'step': 'crawling_website', 'percent': 25})}\n\n"
            result = await loop.run_in_executor(_executor, scrape_website, url)

        if not preview_sent:
            _deduplicate_portfolio(result)
            yield f"data: {json.dumps({'type': 'preview', 'profile': result.model_dump()})}\n\n"
            await asyncio.sleep(0.05)

        # Cross-pollination: discover other platform profiles and merge
        yield f"data: {json.dumps({'type': 'progress', 'step': 'discovering_profiles', 'percent': 50, 'message': 'Searching for your other profiles…'})}\n\n"
        await asyncio.sleep(0.05)
        try:
            result = await loop.run_in_executor(_executor, cross_pollinate, result)
        except Exception as e:
            logger.warning("Cross-pollination failed (non-fatal): %s", e)

        # Web credential enrichment (SearXNG)
        yield f"data: {json.dumps({'type': 'progress', 'step': 'checking_credentials', 'percent': 60, 'message': 'Buscando registros y certificaciones…'})}\n\n"
        try:
            await loop.run_in_executor(_executor, enrich_credentials_from_web, result)
        except Exception as e:
            logger.warning("Web credential enrichment failed (non-fatal): %s", e)

        # Verification checks (VIES, NIF, REA, review signals — fast)
        # Social proof (15 SearXNG calls, ~30s) runs as a background task after delivery.
        yield f"data: {json.dumps({'type': 'progress', 'step': 'verifying_trust', 'percent': 75, 'message': 'Verificando registros y reputación…'})}\n\n"
        try:
            await loop.run_in_executor(_executor, run_verification_checks, result)
        except Exception as e:
            logger.warning("Verification checks failed (non-fatal): %s", e)

        # LLM structuring for website-sourced profiles
        if result.page_chunks and result.source == "website":
            yield f"data: {json.dumps({'type': 'progress', 'step': 'structuring_with_ai', 'percent': 70, 'message': 'AI is reading your website…'})}\n\n"
            try:
                result = await loop.run_in_executor(_executor, structure_profile_with_llm, result)
            except Exception as e:
                logger.warning("LLM structuring failed (non-fatal): %s", e)

        yield f"data: {json.dumps({'type': 'progress', 'step': 'processing', 'percent': 90})}\n\n"
        await asyncio.sleep(0.1)
        _deduplicate_portfolio(result)

        yield f"data: {json.dumps({'type': 'progress', 'step': 'summarizing_reviews', 'percent': 94, 'message': 'Summarizing reviews…'})}\n\n"
        try:
            result = await loop.run_in_executor(_executor, summarize_reviews_with_llm, result)
        except Exception as e:
            logger.warning("Review summary failed (non-fatal): %s", e)

        yield f"data: {json.dumps({'type': 'progress', 'step': 'complete', 'percent': 100})}\n\n"

        # Write to dossier if contractor_id provided
        if contractor_id:
            try:
                from records.dossier import (
                    get_or_create, add_source, update_trust_signals, save_and_recompute,
                )
                yield f"data: {json.dumps({'type': 'progress', 'step': 'saving_dossier', 'percent': 98, 'message': 'Saving to your profile…'})}\n\n"

                await get_or_create(contractor_id, name=result.name, phone=result.phone or None)
                await add_source(contractor_id, result.model_dump())
                if result.trust_signals:
                    await update_trust_signals(contractor_id, result.trust_signals.model_dump())
                canvas = await save_and_recompute(contractor_id)

                # Phone discrepancy: if Habitissimo gave us a phone and the contractor
                # has a different phone on record (e.g. the WhatsApp they contacted us on),
                # emit a signal so the agent can ask which one they prefer.
                phone_discrepancy = None
                if result.phone and result.phone_source == "habitissimo_ajax":
                    dossier_phone = canvas.get("phone") or ""
                    incoming_phone = result.phone.lstrip("+").replace(" ", "")
                    stored_phone = dossier_phone.lstrip("+").replace(" ", "")
                    # Normalise: strip leading country code for comparison
                    def _strip_cc(p: str) -> str:
                        return p[2:] if p.startswith("34") and len(p) > 9 else p
                    if stored_phone and _strip_cc(incoming_phone) != _strip_cc(stored_phone):
                        phone_discrepancy = {
                            "habitissimo_phone": result.phone,
                            "known_phone": dossier_phone,
                        }
                        logger.info(
                            "Phone discrepancy for %s: habitissimo=%s known=%s",
                            contractor_id, result.phone[:6] + "***", dossier_phone[:6] + "***",
                        )

                payload: dict = {"type": "result", "profile": canvas, "canvas": True}
                if phone_discrepancy:
                    payload["phone_discrepancy"] = phone_discrepancy

                # If no phone was found during scraping, ask the frontend to collect
                # it before continuing — social proof is unreliable without it.
                # The frontend shows a phone modal; the user submits via
                # POST /api/contractor/set-phone which then kicks social proof.
                has_phone = bool((result.phone or "").strip())
                if not has_phone:
                    payload["needs_phone"] = True
                    logger.info(
                        "No phone found for contractor=%s — emitting needs_phone signal",
                        contractor_id,
                    )

                yield f"data: {json.dumps(payload)}\n\n"

                if has_phone:
                    # Fire social proof search in background — doesn't block canvas delivery.
                    # Runs ~15 SearXNG queries (25-45s) and updates trust_signals when done.
                    asyncio.create_task(
                        _run_social_proof_background(result, contractor_id)
                    )
                # If no phone: social proof is triggered later via POST /api/contractor/set-phone
            except Exception as e:
                logger.exception("Dossier write failed for contractor %s", contractor_id)
                yield f"data: {json.dumps({'type': 'result', 'profile': result.model_dump()})}\n\n"
        else:
            yield f"data: {json.dumps({'type': 'result', 'profile': result.model_dump()})}\n\n"

    except HTTPException as e:
        yield f"data: {json.dumps({'type': 'error', 'message': str(e.detail)})}\n\n"
    except Exception as e:
        logger.exception(f"Scrape failed for {url}")
        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"


@router.post("/profile-import")
async def profile_import(req: ImportRequest):
    """Scrape a tradesperson profile. Returns SSE stream with progress + result."""
    url = req.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    return StreamingResponse(
        _stream_scrape(url, contractor_id=req.contractor_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/profile-import-sync")
async def profile_import_sync(req: ImportRequest):
    """Synchronous version — scrapes and returns profile JSON directly."""
    url = req.url.strip()
    if not url.startswith("http"):
        url = "https://" + url

    platform = detect_platform(url)
    loop = asyncio.get_event_loop()

    if platform == "habitissimo":
        result = await loop.run_in_executor(_executor, scrape_habitissimo, url)
    elif platform == "houzz":
        result = await loop.run_in_executor(_executor, scrape_houzz, url)
    elif platform == "hogami":
        result = await loop.run_in_executor(_executor, scrape_hogami, url)
    elif platform == "cronoshare":
        result = await loop.run_in_executor(_executor, scrape_cronoshare, url)
    elif platform == "webel":
        raise HTTPException(
            status_code=501,
            detail=(
                "AppWebel (Webel) import is not supported — their API blocks our servers "
                "(datacenter/VPN detection). Paste your details manually or use another source."
            ),
        )
    else:
        result = await loop.run_in_executor(_executor, scrape_website, url)

    # Cross-pollination: discover other platform profiles and merge
    try:
        result = await loop.run_in_executor(_executor, cross_pollinate, result)
    except Exception as e:
        logger.warning("Cross-pollination failed (non-fatal, sync): %s", e)

    # Web credential enrichment (SearXNG)
    try:
        await loop.run_in_executor(_executor, enrich_credentials_from_web, result)
    except Exception as e:
        logger.warning("Web credential enrichment failed (non-fatal, sync): %s", e)

    # Verification checks (VIES, NIF, REA, reviews, social proof)
    try:
        await loop.run_in_executor(_executor, run_verification_checks, result)
    except Exception as e:
        logger.warning("Verification checks failed (non-fatal, sync): %s", e)

    # LLM structuring for website-sourced profiles
    if result.page_chunks and result.source == "website":
        try:
            result = await loop.run_in_executor(_executor, structure_profile_with_llm, result)
        except Exception as e:
            logger.warning("LLM structuring failed (non-fatal, sync): %s", e)

    _deduplicate_portfolio(result)
    try:
        result = await loop.run_in_executor(_executor, summarize_reviews_with_llm, result)
    except Exception as e:
        logger.warning("Review summary failed (non-fatal, sync): %s", e)

    # Write to dossier if contractor_id provided
    if req.contractor_id:
        try:
            from records.dossier import (
                get_or_create, add_source, update_trust_signals, save_and_recompute,
            )
            await get_or_create(req.contractor_id, name=result.name, phone=result.phone or None)
            await add_source(req.contractor_id, result.model_dump())
            if result.trust_signals:
                await update_trust_signals(req.contractor_id, result.trust_signals.model_dump())
            canvas = await save_and_recompute(req.contractor_id)
            return {"canvas": True, "profile": canvas, "contractor_id": req.contractor_id}
        except Exception as e:
            logger.exception("Dossier write failed for contractor %s (sync)", req.contractor_id)

    return result.model_dump()
