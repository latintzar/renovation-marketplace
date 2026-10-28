"""
Contractor Discovery Workflow
==============================

Deterministic pipeline: find contractors on Houzz and Facebook groups for a
homeowner job brief, create HC records with full provenance, send WhatsApp
outreach via approved Meta templates.

This workflow runs entirely without Hermes. It calls existing tool backends
directly (scraper, search, dossier, send_wa). One LLM call (copy.humanize_
job_summary) is used to fill the natural-language slot in the outreach template.

Entry points
------------
run_contractor_discovery(job_id)
    Full pipeline: search Houzz + FB → rank → create HC records → send outreach.
    Returns a WorkflowResult with counts and hc_ids.

on_contractor_reply(phone, job_id)
    Called by the WhatsApp webhook when a contacted contractor first replies.
    Creates/updates HC record as "replied", kicks off Profile Import workflow
    in background, returns provenance dict for ephemeral context injection.

HC record provenance schema
---------------------------
The ``provenance`` jsonb field written to the contractors table at creation:

    {
        "job_id": str,
        "brief_title": str,
        "brief_location": str,
        "brief_summary": str (homeowner description, max 300 chars),
        "found_via": "houzz" | "facebook",
        "profile_url": str | None,      # Houzz profile URL if found on Houzz
        "fb_group_name": str | None,    # Facebook group name if found via FB
        "fb_post_snippet": str | None,  # Excerpt from the FB post mentioning them
        "outreach_at": ISO-8601 str,
        "template_used": str,
        "humanized_summary": str,       # The text inserted into {{2}} of the template
    }

Workflow signal (written to dossier.workflow_signals on completion)
-------------------------------------------------------------------
    {
        "workflow": "contractor_discovery",
        "job_id": str,
        "sent": int,
        "hc_ids": list[str],
        "completed_at": ISO-8601 str,
    }

Hermes reads workflow_signals via ephemeral_context.py and injects them as
notes on the next turn — "Contractor Discovery complete for job X: 8 messages
sent. Awaiting replies."
"""

from __future__ import annotations

import asyncio
import logging
import re
import os
import sys
import time
import uuid as _uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

_PHONE_RE = re.compile(
    r"(?<!\d)"
    r"(\+?\d[\d\s\-\(\)]{6,14}\d)"
    r"(?!\d)"
)


# ─── Result dataclass ─────────────────────────────────────────────────

@dataclass
class WorkflowResult:
    ok: bool
    sent: int = 0
    failed: int = 0
    hc_ids: list[str] = field(default_factory=list)
    candidates_found: int = 0
    wa_filtered: int = 0    # candidates removed by WA presence check
    deferred: int = 0       # sends queued for tomorrow (daily cap reached)
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "sent": self.sent,
            "failed": self.failed,
            "hc_ids": self.hc_ids,
            "candidates_found": self.candidates_found,
            "wa_filtered": self.wa_filtered,
            "deferred": self.deferred,
            "error": self.error,
        }


# ─── Main entry point ─────────────────────────────────────────────────

async def run_contractor_discovery(
    job_id: str,
    max_send: int = 0,
    stagger_seconds: int = 3,
) -> WorkflowResult:
    """Full contractor discovery pipeline for a job.

    Steps:
    1. Flush any deferred sends queued from a previous capped run.
    2. Load the job brief from Supabase (job_inbox).
    3. Search Houzz for contractors matching trade + city.
    4. Search Facebook groups for contractor recommendations.
    5. Merge and deduplicate candidates (phone is required).
    6. WhatsApp presence filter — check each number via VNC browser CDP.
       Over-provisions by 2× target so enough pass the filter.
    7. Humanize the job summary for the template slot.
    8. Request daily send quota (account-wide ticker).
       Approved → send now.  Overflow → queued for tomorrow.
    9. For each approved candidate:
       a. Create HC record in contractors table with provenance.
       b. Send WhatsApp outreach via approved Meta template.
       c. Log send to cold_outreach_log.
    10. Write workflow_signal to dossier (for Hermes notification).
    11. Return WorkflowResult.
    """
    from routes.job_inbox import get_job_by_id, update_job

    job = await get_job_by_id(job_id)
    if not job:
        return WorkflowResult(ok=False, error=f"Job {job_id} not found")

    brief = job.get("brief") or {}
    trade = str(brief.get("trade") or brief.get("title") or "").strip().lower()
    city = str(brief.get("location") or "").strip()

    if not trade or not city:
        return WorkflowResult(
            ok=False,
            error=f"Job brief missing trade or location (trade={trade!r}, city={city!r})",
        )

    logger.info(
        "ContractorDiscovery | job=%s trade=%s city=%s",
        job_id[:8], trade, city,
    )

    # ── Step 1: Search Houzz ──────────────────────────────────────────
    houzz_candidates = await _search_houzz_expanded(trade, city)
    logger.info(
        "ContractorDiscovery | Houzz returned %d candidates", len(houzz_candidates)
    )

    # ── Step 2: Search Facebook groups ───────────────────────────────
    fb_candidates = await _search_facebook(trade, city)
    logger.info(
        "ContractorDiscovery | Facebook returned %d candidates", len(fb_candidates)
    )

    # ── Step 3: Merge, deduplicate, filter valid phones ───────────────
    all_candidates = _merge_and_deduplicate(houzz_candidates, fb_candidates)
    contactable_count = sum(1 for c in all_candidates if c.get("_digits"))
    name_only_count = sum(1 for c in all_candidates if c.get("_name_only"))
    logger.info(
        "ContractorDiscovery | %d contactable + %d name-only leads",
        contactable_count, name_only_count,
    )

    if not all_candidates:
        await update_job(job_id, {
            "houzz_candidates": houzz_candidates,
            "fb_candidates": fb_candidates,
        })
        return WorkflowResult(
            ok=False,
            candidates_found=len(houzz_candidates) + len(fb_candidates),
            error="No candidates with valid phone numbers found",
        )

    # Save candidates back to the job record
    await update_job(job_id, {
        "houzz_candidates": [c for c in all_candidates if c.get("source") == "houzz"],
        "fb_candidates": [c for c in all_candidates if c.get("source") == "facebook" and not c.get("_name_only")],
        "fb_name_only_leads": [c for c in all_candidates if c.get("_name_only")],
    })

    from messaging import detect_whatsapp_language as detect_language
    from config import settings
    from messaging.whatsapp.outreach_budget import (
        request_quota, enqueue_deferred, flush_queue,
    )

    # ── Step 3b: WhatsApp presence filter ────────────────────────────
    # Over-provision: check up to 2× target candidates so enough pass.
    OVERPROVISION_FACTOR = 2
    target = max_send or getattr(settings, "OUTREACH_TARGET_PER_JOB", 10)
    daily_max = getattr(settings, "OUTREACH_MAX_DAILY", 30)
    waba_id = getattr(settings, "OUTREACH_FOUNDER_PHONE", "")

    all_contactable = [c for c in all_candidates if c.get("_digits")]
    name_only_leads = [c for c in all_candidates if c.get("_name_only")]
    wa_pool = all_contactable[: target * OVERPROVISION_FACTOR]

    try:
        from scrapers.whatsapp_checker import check_bulk
        wa_results = await check_bulk([c["_digits"] for c in wa_pool])
        contactable = [c for c in wa_pool if wa_results.get(c["_digits"], True)]
        wa_filtered_count = len(wa_pool) - len(contactable)
        logger.info(
            "ContractorDiscovery | WA filter | %d/%d passed (%d removed)",
            len(contactable), len(wa_pool), wa_filtered_count,
        )
    except Exception as wa_exc:
        # If VNC is down or checker fails, proceed without filtering (safe default)
        logger.warning(
            "ContractorDiscovery | WA presence check failed — skipping filter | %s",
            wa_exc,
        )
        contactable = all_contactable
        wa_filtered_count = 0

    if not contactable:
        logger.warning("ContractorDiscovery | No WA-confirmed candidates after filter")
        return WorkflowResult(
            ok=False,
            candidates_found=len(all_candidates),
            wa_filtered=wa_filtered_count,
            error="All candidates failed WhatsApp presence check",
        )

    # ── Step 4: Humanize job summary for template slot {{2}} ──────────
    first_phone = contactable[0].get("_digits", "") if contactable else ""
    lang = detect_language(first_phone) if first_phone else "en_US"
    humanized = await _humanize_brief(brief, lang)

    if name_only_leads:
        logger.info(
            "ContractorDiscovery | %d name-only leads saved (no phone, not contacted)",
            len(name_only_leads),
        )

    # ── Step 5a: Flush deferred queue from previous capped runs ───────
    queued_rows = await flush_queue(waba_id)
    if queued_rows:
        logger.info(
            "ContractorDiscovery | flushing %d deferred rows from prior run",
            len(queued_rows),
        )

    # ── Step 5b: Request quota for today ──────────────────────────────
    # Account for deferred rows that will consume today's budget too.
    deferred_count_this_flush = len(queued_rows)
    new_candidates = contactable[:target]
    approved, queued_count = await request_quota(
        waba_id, len(new_candidates), daily_max - deferred_count_this_flush
    )
    to_send = new_candidates[:approved]
    to_queue = new_candidates[approved: approved + queued_count]

    # ── Step 5c: Send outreach (approved now) ─────────────────────────
    sent = 0
    failed = 0
    hc_ids: list[str] = []

    # First, send any deferred rows from the queue flush
    for deferred_row in queued_rows:
        candidate = deferred_row.get("candidate_json") or {}
        if not candidate.get("_digits"):
            continue
        h_summary = deferred_row.get("humanized_summary") or humanized
        d_lang = deferred_row.get("lang") or lang
        hc_id, ok = await _send_single_outreach(
            candidate=candidate,
            job_id=deferred_row.get("job_id") or job_id,
            brief=brief,
            humanized_summary=h_summary,
            lang=d_lang,
        )
        if ok:
            sent += 1
            hc_ids.append(hc_id)
        else:
            failed += 1
        if stagger_seconds > 0:
            await asyncio.sleep(stagger_seconds)

    # Then send newly approved candidates
    for i, candidate in enumerate(to_send):
        hc_id, ok = await _send_single_outreach(
            candidate=candidate,
            job_id=job_id,
            brief=brief,
            humanized_summary=humanized,
            lang=lang,
        )
        if ok:
            sent += 1
            hc_ids.append(hc_id)
        else:
            failed += 1

        if i < len(to_send) - 1 and stagger_seconds > 0:
            await asyncio.sleep(stagger_seconds)

    # ── Step 5d: Queue overflow for tomorrow ──────────────────────────
    deferred_queued = 0
    if to_queue:
        deferred_queued = await enqueue_deferred(
            to_queue, waba_id, job_id, humanized, lang
        )
        logger.info(
            "ContractorDiscovery | %d sends deferred to tomorrow (daily cap reached)",
            deferred_queued,
        )

    # ── Step 6: Write workflow signal (Hermes notification) ───────────
    _write_workflow_signal(job_id, sent=sent, hc_ids=hc_ids)

    # ── Step 7: Notify Peter that discovery is complete ─────────────
    try:
        from agent import notify_peter_discovery_complete
        await notify_peter_discovery_complete(
            job_id=job_id,
            trade=trade,
            city=city,
            sent=sent,
            deferred=deferred_queued,
            candidates_found=len(all_candidates),
        )
    except Exception as exc:
        logger.warning("Peter discovery notification failed (non-fatal) | %s", exc)

    logger.info(
        "ContractorDiscovery | job=%s | sent=%d failed=%d deferred=%d "
        "wa_filtered=%d hc_ids=%d",
        job_id[:8], sent, failed, deferred_queued, wa_filtered_count, len(hc_ids),
    )

    return WorkflowResult(
        ok=True,
        sent=sent,
        failed=failed,
        hc_ids=hc_ids,
        candidates_found=len(all_candidates),
        wa_filtered=wa_filtered_count,
        deferred=deferred_queued,
    )


# ─── Reply handler (webhook entry point) ─────────────────────────────

async def on_contractor_reply(phone: str, job_id: Optional[str] = None) -> Optional[dict]:
    """Called by the WhatsApp webhook when a contacted contractor first replies.

    Returns provenance dict for ephemeral context injection into Hermes, or
    None if this phone is not found in the contractors table as an HC record.

    Side effects:
    - Updates outreach_stage from "contacted" to "replied" on the HC record.
    - Kicks off Profile Import workflow in background if Houzz URL in provenance.
    """
    from records.dossier import get_by_phone, _patch

    digits = phone.strip().lstrip("+").replace(" ", "").replace("-", "")
    row = await get_by_phone(digits)

    if not row:
        return None

    contractor_id = row.get("id", "")
    provenance = row.get("provenance") or {}

    if not provenance:
        return None

    # Only act on contractors we reached out to (outreach_stage == "contacted")
    if provenance.get("outreach_stage") not in (None, "contacted"):
        return None

    logger.info(
        "ContractorDiscovery | reply from hc record | id=%s found_via=%s",
        contractor_id[:12],
        provenance.get("found_via", "?"),
    )

    # Mark as replied
    provenance["outreach_stage"] = "replied"
    provenance["replied_at"] = datetime.now(timezone.utc).isoformat()
    await _patch(contractor_id, {"provenance": provenance})

    # Kick off Profile Import in background if Houzz URL is available
    profile_url = provenance.get("profile_url")
    if profile_url:
        asyncio.create_task(
            _background_profile_import(contractor_id, profile_url)
        )
        logger.info(
            "ContractorDiscovery | triggered Profile Import | id=%s url=%s",
            contractor_id[:12],
            profile_url[:60],
        )

    # Send personalised first reply using copy utility
    asyncio.create_task(
        _send_first_reply(digits, contractor_id, provenance)
    )

    return {
        "contractor_id": contractor_id,
        "found_via": provenance.get("found_via"),
        "profile_url": profile_url,
        "job_id": provenance.get("job_id"),
        "brief_title": provenance.get("brief_title"),
        "brief_location": provenance.get("brief_location"),
        "outreach_stage": "replied",
        "profile_import_triggered": bool(profile_url),
    }


# ─── Houzz search ─────────────────────────────────────────────────────

# Nearby cities for Houzz expansion — tradespeople in these areas overlap.
# Keyed by lowercase city name, values are 2-3 nearby cities to also search.
_NEARBY_CITIES: dict[str, list[str]] = {
    "marbella": ["Estepona", "Fuengirola", "Malaga"],
    "estepona": ["Marbella", "Manilva", "Casares"],
    "fuengirola": ["Marbella", "Benalmadena", "Mijas"],
    "benalmadena": ["Fuengirola", "Torremolinos", "Malaga"],
    "torremolinos": ["Benalmadena", "Malaga"],
    "malaga": ["Torremolinos", "Benalmadena", "Fuengirola"],
    "nerja": ["Malaga", "Almunecar", "Torrox"],
    "almunecar": ["Nerja", "Motril", "Granada"],
    "granada": ["Motril", "Almunecar", "Jaen"],
    "seville": ["Cadiz", "Cordoba", "Huelva"],
    "cadiz": ["Seville", "Jerez"],
    "cordoba": ["Seville", "Jaen", "Granada"],
    "almeria": ["Roquetas", "Motril"],
    "alicante": ["Elche", "Benidorm", "Torrevieja"],
    "torrevieja": ["Alicante", "Orihuela", "Elche"],
    "san javier": ["Murcia", "Cartagena", "Los Alcazares"],
    "los alcazares": ["San Javier", "Murcia", "Cartagena"],
    "murcia": ["Cartagena", "San Javier", "Orihuela"],
    "cartagena": ["Murcia", "San Javier", "La Manga"],
    "barcelona": ["Badalona", "Hospitalet", "Terrassa"],
    "valencia": ["Torrent", "Gandia", "Sagunto"],
}


_TRADE_SLUG_MAP: dict[str, list[str]] = {
    "kitchen": ["carpenter", "kitchen-and-bath-designer"],
    "kitchen island": ["carpenter", "kitchen-and-bath-designer"],
    "bathroom": ["plumber", "kitchen-and-bath-designer", "tile-and-stone"],
    "bathroom renovation": ["plumber", "general-contractor", "kitchen-and-bath-designer"],
    "renovation": ["general-contractor", "architect", "interior-designer"],
    "reforma": ["general-contractor", "architect"],
    "full refurb": ["general-contractor", "architect", "interior-designer"],
    "painting": ["painter", "interior-designer"],
    "pintor": ["painter", "interior-designer"],
    "roof": ["roofer", "general-contractor"],
    "floor": ["tile-and-stone", "general-contractor"],
    "garden": ["landscape-architect", "general-contractor"],
    "pool": ["landscape-architect", "general-contractor"],
    "ac": ["hvac-contractor", "electrician"],
    "air conditioning": ["hvac-contractor", "electrician"],
    "heating": ["hvac-contractor", "plumber"],
    "electric": ["electrician"],
    "window": ["general-contractor", "carpenter"],
    "door": ["carpenter", "general-contractor"],
    "handyman": ["handyman", "general-contractor"],
    "lock": ["locksmith"],
}


def _expand_trade_slugs(trade: str, max_slugs: int = 3) -> list[str]:
    """Map a trade/job description to multiple Houzz directory slugs.

    Returns at least the original trade slug, plus related ones (up to max_slugs).
    """
    trade_lower = trade.lower().strip()
    trade_slug = trade_lower.replace(" ", "-")

    for keyword, slugs in _TRADE_SLUG_MAP.items():
        if keyword in trade_lower:
            result = []
            for s in slugs:
                if s not in result:
                    result.append(s)
            if trade_slug not in result:
                result.insert(0, trade_slug)
            return result[:max_slugs]

    return [trade_slug]


async def _search_houzz_expanded(trade: str, city: str) -> list[dict]:
    """Search Houzz for the target city first. Only expand to nearby cities if
    the primary city returns fewer than _SPARSE_THRESHOLD results — because in
    small towns tradespeople often list under the nearest larger city.

    Large cities (Barcelona, Valencia, Malaga, Seville) never expand — a
    plumber in Seville isn't going to Valencia.
    """
    slugs = _expand_trade_slugs(trade)

    # Phase 1: search the primary city with all relevant slugs
    primary_tasks = [_search_houzz(slug, city) for slug in slugs]
    primary_results = await asyncio.gather(*primary_tasks, return_exceptions=True)

    all_candidates: list[dict] = []
    seen_phones: set[str] = set()

    for result in primary_results:
        if isinstance(result, Exception):
            logger.warning("Houzz search failed for primary city %s: %s", city, result)
            continue
        for c in result:
            phone = str(c.get("telephone") or "").replace(" ", "").replace("-", "").lstrip("+")
            if phone and phone in seen_phones:
                continue
            if phone:
                seen_phones.add(phone)
            all_candidates.append(c)

    # Phase 2: only expand to nearby cities if results are sparse
    _SPARSE_THRESHOLD = 5
    nearby = _NEARBY_CITIES.get(city.lower(), [])
    if len(all_candidates) < _SPARSE_THRESHOLD and nearby:
        logger.info(
            "Houzz sparse results (%d) for %s — expanding to nearby: %s",
            len(all_candidates), city, nearby,
        )
        expansion_tasks = [
            _search_houzz(slug, c)
            for slug in slugs
            for c in nearby
        ]
        expansion_results = await asyncio.gather(*expansion_tasks, return_exceptions=True)

        for result in expansion_results:
            if isinstance(result, Exception):
                continue
            for c in result:
                phone = str(c.get("telephone") or "").replace(" ", "").replace("-", "").lstrip("+")
                if phone and phone in seen_phones:
                    continue
                if phone:
                    seen_phones.add(phone)
                all_candidates.append(c)

        logger.info(
            "Houzz expansion | %s + %s → %d total candidates",
            city, nearby, len(all_candidates),
        )

    return all_candidates


async def _search_houzz(trade: str, city: str) -> list[dict]:
    """Scrape Houzz directory for contractors. Returns list of candidate dicts."""
    try:
        from core import bootstrap_init as _boot; _boot()
        sys.path.insert(0, "/root/leo/tools/houzz-south-spain")
        from scrape_houzz import TRADE_SLUGS, listing_url, parse_listing_html
        from scraping import fetch_browser as fetch_url

        trade_slug = trade.replace(" ", "-").lower()
        valid_slugs = [s for s in TRADE_SLUGS if trade_slug in s or s in trade_slug]
        chosen_slug = valid_slugs[0] if valid_slugs else trade_slug

        url = listing_url(chosen_slug, city)
        html = await fetch_url(url, max_chars=500_000, timeout_ms=30_000, raw_html=True)
        if not html:
            logger.warning("Houzz returned empty for %s / %s", trade, city)
            return []

        rows = await asyncio.to_thread(
            parse_listing_html, html, chosen_slug, city, url
        )
        return [
            {
                "name": r.name,
                "telephone": r.telephone,
                "address": r.address,
                "profile_url": r.profile_urls[0] if r.profile_urls else None,
                "area_served": r.area_served,
                "source": "houzz",
            }
            for r in rows
        ]
    except Exception as e:
        logger.warning("Houzz search failed: %s", e)
        return []


# ─── Facebook search ──────────────────────────────────────────────────

async def _search_facebook(trade: str, city: str, days_back: int = 0) -> list[dict]:
    """Search Facebook groups for contractor recommendations via Bright Data.

    Two-phase approach:
    1. Bright Data Web Unlocker finds relevant FB group post URLs via Google index.
       Each search request uses a fresh residential IP — no rate limiting issues.
       Falls back to SearXNG per-query if Bright Data is unavailable.
    2. DynamicFetcher visits each post to read comments (where the real
       phone numbers and business names live).

    Args:
        days_back: If > 0, restrict index search to posts newer than this many days.

    Returns candidates with phone numbers and/or business names.
    """
    from messaging import expand_fb_queries, search_fb_posts

    query = f"{trade} {city}"
    expanded = expand_fb_queries(query)

    posts = await asyncio.to_thread(search_fb_posts, expanded, 30, days_back)

    # Phase 1: Extract phones from SearXNG snippets (quick, shallow)
    candidates = []
    snippet_phones: set[str] = set()
    for post in posts:
        snippet = (post.get("snippet") or "") + " " + (post.get("title") or "")
        phones = _extract_phones_from_text(snippet)
        for ph in phones:
            snippet_phones.add(ph)
            candidates.append({
                "name": "",
                "telephone": ph,
                "address": "",
                "profile_url": None,
                "area_served": "",
                "source": "facebook",
                "fb_group_name": post.get("group_name", ""),
                "fb_post_snippet": snippet[:250],
                "fb_post_url": post.get("url", ""),
            })

    # Phase 2: Visit top FB posts to read comments (deep, rich)
    fb_urls = []
    for post in posts:
        url = post.get("url", "")
        if "facebook.com/groups" in url and url not in fb_urls:
            fb_urls.append(url)
    fb_urls = fb_urls[:8]

    if fb_urls:
        comment_candidates = await _scrape_fb_post_comments(
            fb_urls, city, snippet_phones
        )
        candidates.extend(comment_candidates)
        logger.info(
            "FB comment scrape | %d posts → %d new contacts",
            len(fb_urls), len(comment_candidates),
        )

    return candidates


async def _search_forums(trade: str, city: str, days_back: int = 0) -> list[dict]:
    """Search Spanish forums (Forocoches, Mediavida, Reddit ES) via Bright Data.

    Same pattern as _search_facebook but without the browser comment-scrape phase —
    forum threads are public and readable from search snippets alone.
    Bright Data handles IP rotation; each query gets a fresh residential IP.
    Falls back per-query to SearXNG if Bright Data is unavailable.

    Args:
        days_back: If > 0, restrict index search to posts newer than this many days.

    Returns candidates with phone numbers and/or extracted business names.
    """
    from messaging import expand_fb_queries, search_forum_posts

    query = f"{trade} {city}"
    expanded = expand_fb_queries(query)

    posts = await asyncio.to_thread(search_forum_posts, expanded, 30, days_back)

    candidates = []
    seen_phones: set[str] = set()
    for post in posts:
        snippet = (post.get("snippet") or "") + " " + (post.get("title") or "")
        phones = _extract_phones_from_text(snippet)
        for ph in phones:
            if ph in seen_phones:
                continue
            seen_phones.add(ph)
            candidates.append({
                "name": "",
                "telephone": ph,
                "address": "",
                "profile_url": None,
                "area_served": "",
                "source": "forum",
                "forum_name": post.get("forum_name", ""),
                "forum_post_snippet": snippet[:250],
                "forum_post_url": post.get("url", ""),
            })

        # Capture snippet-only leads (thread with no extracted phone)
        if not phones and snippet.strip():
            candidates.append({
                "name": "",
                "telephone": "",
                "address": "",
                "profile_url": None,
                "area_served": "",
                "source": "forum",
                "forum_name": post.get("forum_name", ""),
                "forum_post_snippet": snippet[:250],
                "forum_post_url": post.get("url", ""),
                "_name_only": True,
            })

    logger.info(
        "Forum search | trade=%s city=%s days_back=%d | %d posts → %d candidates",
        trade, city, days_back, len(posts), len(candidates),
    )
    return candidates


async def _scrape_fb_post_comments(
    urls: list[str],
    city: str,
    already_found: set[str],
) -> list[dict]:
    """Fetch full FB post pages and extract phones + business names from comments."""
    from core import bootstrap_init as _boot; _boot()
    from scraping import fetch_browser as fetch_url
    from scrapers import fb_expand_comments

    async def _fetch_one(url: str) -> list[dict]:
        try:
            content = await fetch_url(
                url,
                max_chars=15000,
                timeout_ms=35000,
                page_action=fb_expand_comments,
            )
            if not content or len(content) < 100:
                return []
        except Exception as exc:
            logger.debug("FB comment fetch failed for %s: %s", url[:60], exc)
            return []

        results = []
        phones = _extract_phones_from_text(content)
        for ph in phones:
            if ph not in already_found:
                already_found.add(ph)
                name = _extract_name_near_phone(content, ph)
                results.append({
                    "name": name,
                    "telephone": ph,
                    "address": "",
                    "profile_url": None,
                    "area_served": city,
                    "source": "facebook",
                    "fb_group_name": "",
                    "fb_post_snippet": "",
                    "fb_post_url": url,
                })

        # Extract standalone business names (no phone, but searchable)
        biz_names = _extract_business_names(content, already_found)
        for biz in biz_names:
            results.append({
                "name": biz["name"],
                "telephone": "",
                "address": "",
                "profile_url": None,
                "area_served": city,
                "source": "facebook",
                "fb_group_name": "",
                "fb_post_snippet": biz.get("context", ""),
                "fb_post_url": url,
                "_name_only": True,
            })
        return results

    tasks = [_fetch_one(u) for u in urls]
    all_results = await asyncio.gather(*tasks, return_exceptions=True)

    combined = []
    for result in all_results:
        if isinstance(result, list):
            combined.extend(result)
    return combined


def _extract_name_near_phone(text: str, phone_digits: str) -> str:
    """Try to find a commenter name near a phone number in FB post text.

    FB comment structure: "Name\\nComment text with phone\\nTimestamp"
    """
    # Find the phone in the text
    phone_variants = [phone_digits, phone_digits[:3] + " " + phone_digits[3:]]
    pos = -1
    for variant in phone_variants:
        pos = text.find(variant)
        if pos >= 0:
            break
    if pos < 0:
        return ""

    # Look backwards for a name-like line (capitalized words on their own line)
    before = text[max(0, pos - 200):pos]
    lines = before.split("\n")
    for line in reversed(lines):
        line = line.strip()
        if not line or len(line) < 3 or len(line) > 60:
            continue
        # Skip common non-name patterns
        if any(skip in line.lower() for skip in [
            "see more", "like", "comment", "share", "reaction",
            "hour", "day", "week", "min", "ago",
        ]):
            continue
        # Name-like: starts with capital, mostly letters
        if line[0].isupper() and sum(c.isalpha() or c == " " for c in line) > len(line) * 0.7:
            return line

    return ""


def _extract_phones_from_text(text: str) -> list[str]:
    """Extract phone numbers from a text snippet."""
    found = []
    seen = set()
    for m in _PHONE_RE.finditer(text):
        raw = m.group(1)
        digits = re.sub(r"[\s\-\(\)]", "", raw).lstrip("+")
        if len(digits) >= 9 and digits not in seen:
            seen.add(digits)
            found.append(digits)
    return found


# Recommendation language patterns across EN/ES FB groups
_RECOMMEND_RE = re.compile(
    r"(?:recommend|recomiendo|try|prueba|contact|contacta|use|usé|used|"
    r"we went with|fuimos con|look up|busca|check out|mira|"
    r"I suggest|sugiero|call|llama|ask for|pregunta por)\s+"
    r"([A-Z][A-Za-zÀ-ÿ0-9&'\- ]{2,40})",
    re.IGNORECASE,
)

_BIZ_SUFFIXES = re.compile(
    r"\b(?:S\.?L\.?|S\.?A\.?|Ltd|LLC|Solutions|Services|Servicios|"
    r"Reformas|Construcciones|Instalaciones|Carpintería|Fontanería|"
    r"Cerrajería|Multiservicios|Home|Homes|Design|Construction|"
    r"Interiors|Maintenance|Mantenimiento)\b",
    re.IGNORECASE,
)

_NOISE_NAMES = {
    "facebook", "messenger", "whatsapp", "instagram", "google", "houzz",
    "the group", "this group", "el grupo", "este grupo", "thank you",
    "gracias", "thanks", "see more", "view more", "ver más",
}


def _extract_business_names(
    text: str, phones_already_found: set[str]
) -> list[dict]:
    """Find business name mentions in FB comments that don't have a phone number.

    Two strategies:
    1. Recommendation patterns: "I recommend MJ Home Solutions" / "Try KitchensPlus1"
    2. Business suffix detection: lines containing SL, Ltd, Reformas, Services, etc.

    Returns list of {"name": str, "context": str} dicts.
    """
    found: list[dict] = []
    seen_names: set[str] = set()

    # Strategy 1: recommendation patterns
    for m in _RECOMMEND_RE.finditer(text):
        name = m.group(1).strip().rstrip(".,;:!?")
        name_lower = name.lower()
        if name_lower in _NOISE_NAMES or len(name) < 4:
            continue
        if name_lower in seen_names:
            continue
        seen_names.add(name_lower)
        ctx_start = max(0, m.start() - 30)
        ctx_end = min(len(text), m.end() + 30)
        found.append({"name": name, "context": text[ctx_start:ctx_end].strip()})

    # Strategy 2: lines with business suffixes (SL, Reformas, Services, etc.)
    for line in text.split("\n"):
        line = line.strip()
        if not line or len(line) < 5 or len(line) > 80:
            continue
        if not _BIZ_SUFFIXES.search(line):
            continue
        # Skip lines that are just timestamp/UI text
        if any(skip in line.lower() for skip in [
            "see more", "like", "comment", "share", "ago", "hour", "day",
        ]):
            continue
        # Must start with a capital letter (business name)
        name = line.strip()
        if not name[0].isupper():
            continue
        name_lower = name.lower()
        if name_lower in seen_names or name_lower in _NOISE_NAMES:
            continue
        seen_names.add(name_lower)
        found.append({"name": name, "context": ""})

    if found:
        logger.info(
            "FB biz name extraction | %d standalone names found", len(found),
        )
    return found


# ─── Merge and deduplicate ────────────────────────────────────────────

def _merge_and_deduplicate(
    houzz: list[dict], facebook: list[dict]
) -> list[dict]:
    """Merge Houzz and Facebook candidates, deduplicate by phone, filter valid.

    Name-only candidates (from FB business name extraction) are preserved at the
    end of the list with _name_only=True. They won't be sent outreach directly
    but are stored on the job record as leads for manual follow-up or Houzz lookup.
    """
    seen_phones: set[str] = set()
    seen_names: set[str] = set()
    with_phone = []
    name_only = []

    for candidate in houzz + facebook:
        if candidate.get("_name_only"):
            name = str(candidate.get("name") or "").strip().lower()
            if name and name not in seen_names:
                seen_names.add(name)
                name_only.append({**candidate, "_digits": ""})
            continue

        phone_raw = str(
            candidate.get("telephone") or candidate.get("phone") or ""
        ).strip()
        digits = phone_raw.lstrip("+").replace(" ", "").replace("-", "")
        if len(digits) < 7:
            continue
        if digits in seen_phones:
            continue
        seen_phones.add(digits)
        with_phone.append({**candidate, "_digits": digits})

    # Houzz first (richer data), then Facebook
    with_phone.sort(
        key=lambda c: (0 if c.get("source") == "houzz" else 1, not bool(c.get("profile_url")))
    )

    if name_only:
        logger.info(
            "Merge | %d with phone + %d name-only leads",
            len(with_phone), len(name_only),
        )

    return with_phone + name_only


# ─── HC record creation + outreach send ──────────────────────────────

async def _send_single_outreach(
    candidate: dict,
    job_id: str,
    brief: dict,
    humanized_summary: str,
    lang: str,
) -> tuple[str, bool]:
    """Create HC record and send one outreach message.

    Returns (hc_id, success_bool).
    """
    from records.dossier import get_or_create, _patch
    from messaging import send_wa_message, detect_whatsapp_language as detect_language
    from routes.job_inbox import add_response

    digits = candidate["_digits"]
    name = str(candidate.get("name") or "").strip()
    source = candidate.get("source", "houzz")
    profile_url = candidate.get("profile_url")
    fb_group_name = candidate.get("fb_group_name", "")
    fb_post_snippet = candidate.get("fb_post_snippet", "")
    now = datetime.now(timezone.utc).isoformat()

    # Detect language per phone (some contractors may have non-Spanish numbers)
    c_lang = detect_language(digits)
    first_name = name.split()[0] if name else ""
    title = str(brief.get("title") or brief.get("trade") or "home project")
    location = str(brief.get("location") or "Spain")
    template_params = [
        first_name or ("ahí" if c_lang == "es" else "there"),
        humanized_summary,
        location,
    ]

    # ── Create HC record in contractors table ─────────────────────────
    hc_id = f"hc-{_uuid.uuid4()}"
    provenance = {
        "job_id": job_id,
        "brief_title": title,
        "brief_location": location,
        "brief_summary": str(brief.get("description") or "")[:300],
        "found_via": source,
        "profile_url": profile_url,
        "fb_group_name": fb_group_name or None,
        "fb_post_snippet": fb_post_snippet[:250] if fb_post_snippet else None,
        "outreach_at": now,
        "outreach_stage": "contacted",
        "humanized_summary": humanized_summary,
    }

    try:
        await get_or_create(hc_id, name=name, phone=digits, provenance=provenance)
        logger.debug("HC record created | id=%s phone=%s", hc_id[:12], digits[:8])
    except Exception as e:
        logger.warning("HC record creation failed for %s: %s", digits[:8], e)
        # Non-fatal — still attempt send

    # Record in job_responses for the inbox view
    try:
        await add_response(job_id, {
            "contractor_phone": digits,
            "contractor_name": name,
            "source": source,
            "houzz_profile_url": profile_url or "",
            "outreach_stage": "contacted",
            "last_outreach_at": now,
            "hc_id": hc_id,
        })
    except Exception as e:
        logger.warning("job_response write failed for %s: %s", digits[:8], e)

    # ── Send WhatsApp outreach template ───────────────────────────────
    try:
        result = await send_wa_message(
            phone=digits,
            text="",  # template send — text unused
            purpose="outreach",
            name=template_params[0],
            template_params=template_params,
        )
        if result.ok:
            logger.info(
                "ContractorDiscovery | sent | id=%s phone=%s via=%s",
                hc_id[:12], digits[:8], result.method,
            )
            # Store template name on provenance
            provenance["template_used"] = result.method
            return hc_id, True
        else:
            logger.warning(
                "ContractorDiscovery | send failed | phone=%s error=%s",
                digits[:8], result.error,
            )
            return hc_id, False
    except Exception as e:
        logger.error("ContractorDiscovery | send error | phone=%s: %s", digits[:8], e)
        return hc_id, False


# ─── Humanize brief ───────────────────────────────────────────────────

async def _humanize_brief(brief: dict, lang: str) -> str:
    """Get a humanized job summary for template slot {{2}}."""
    from workflows.copy import humanize_job_summary
    lang_code = "es" if lang == "es" else "en"
    return await humanize_job_summary(brief, language=lang_code)


# ─── First reply crafting ─────────────────────────────────────────────

async def _send_first_reply(
    phone_digits: str,
    contractor_id: str,
    provenance: dict,
) -> None:
    """Send a personalized follow-up when a contractor first replies."""
    from messaging import send_wa_message, detect_whatsapp_language as detect_language
    from workflows.copy import craft_first_reply

    lang = detect_language(phone_digits)

    brief = {
        "title": provenance.get("brief_title", ""),
        "description": provenance.get("brief_summary", ""),
        "location": provenance.get("brief_location", ""),
    }
    contractor_profile = {
        "found_via": provenance.get("found_via"),
        "profile_url": provenance.get("profile_url"),
        "fb_group_name": provenance.get("fb_group_name"),
        "fb_post_snippet": provenance.get("fb_post_snippet"),
    }

    try:
        message = await craft_first_reply(brief, contractor_profile, language=lang)
        result = await send_wa_message(
            phone=phone_digits,
            text=message,
            purpose="general",
        )
        if result.ok:
            logger.info(
                "ContractorDiscovery | first_reply sent | id=%s", contractor_id[:12]
            )
        else:
            logger.warning(
                "ContractorDiscovery | first_reply failed | id=%s error=%s",
                contractor_id[:12], result.error,
            )
    except Exception as e:
        logger.warning("ContractorDiscovery | first_reply error: %s", e)


# ─── Background Profile Import ────────────────────────────────────────

async def _background_profile_import(contractor_id: str, profile_url: str) -> None:
    """Kick off Profile Import workflow in background after a contractor replies."""
    try:
        from workflows.profile_import import run_profile_import
        result = await run_profile_import(contractor_id, profile_url)
        if result.ok:
            logger.info(
                "ContractorDiscovery | profile_import complete | id=%s score=%s",
                contractor_id[:12], result.trust_score,
            )
        else:
            logger.warning(
                "ContractorDiscovery | profile_import failed | id=%s: %s",
                contractor_id[:12], result.error,
            )
    except Exception as e:
        logger.error(
            "ContractorDiscovery | profile_import error | id=%s: %s",
            contractor_id[:12], e,
        )


# ─── Workflow signal ──────────────────────────────────────────────────

def _write_workflow_signal(job_id: str, sent: int, hc_ids: list[str]) -> None:
    """Write completion signal for Hermes to pick up on next turn.

    The signal is stored on the job record. ephemeral_context.py will
    read it and inject it as a context note for the next Hermes turn
    involving this job.
    """
    import asyncio as _asyncio
    from routes.job_inbox import update_job

    signal = {
        "workflow": "contractor_discovery",
        "job_id": job_id,
        "sent": sent,
        "hc_ids": hc_ids,
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    async def _write():
        try:
            await update_job(job_id, {"last_workflow_signal": signal})
        except Exception as e:
            logger.warning("workflow signal write failed: %s", e)

    try:
        loop = _asyncio.get_event_loop()
        if loop.is_running():
            _asyncio.create_task(_write())
        else:
            loop.run_until_complete(_write())
    except Exception as e:
        logger.warning("workflow signal scheduling failed: %s", e)
