"""
leo_agent/tools/discovery.py — Contractor and market discovery tools.

Tools: find_houzz_contractors, search_fb_groups, search_forums, enrich_contractor
"""

from __future__ import annotations

import json
import logging

from ..tool_utils import (
    _compact_tool_result, _get_ctx_val, _record_activity, _run_async,
    _send_indicator, _update_job_async,
)

logger = logging.getLogger(__name__)


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_find_houzz_contractors(args: dict, **kw) -> str:
    """Search Houzz directory for contractors matching a trade and city."""
    _record_activity("find_houzz_contractors", "Searching Houzz…")
    trade = str(args.get("trade", "")).strip().lower()
    city = str(args.get("city", "")).strip()
    job_id = str(args.get("job_id", "")).strip()

    if not trade or not city:
        return json.dumps({"ok": False, "error": "trade and city are required"})

    _record_activity("find_houzz_contractors", f"Searching Houzz: {trade} in {city}…")
    _send_indicator("find_houzz_contractors", f"_Searching Houzz for {trade} in {city}…_")

    try:
        from messaging.frameworks import get_adapter
        _search_houzz_expanded = get_adapter("workflows.search_houzz_expanded")
        candidates = _run_async(_search_houzz_expanded(trade, city))
    except Exception as e:
        logger.error("find_houzz_contractors failed: %s", e, exc_info=True)
        return json.dumps({"ok": False, "error": str(e)})

    if job_id:
        _run_async(_update_job_async(job_id, {"houzz_candidates": candidates}))

    return json.dumps(_compact_tool_result("find_houzz_contractors", {
        "ok": True,
        "trade": trade,
        "city": city,
        "count": len(candidates),
        "candidates": candidates[:20],
    }), ensure_ascii=False)


def _handle_search_fb_groups(args: dict, **kw) -> str:
    """Search Facebook groups for contractor recommendations."""
    _record_activity("search_fb_groups", "Searching Facebook groups…")
    query = str(args.get("query", "")).strip()
    max_results = int(args.get("max_results", 10))
    job_id = str(args.get("job_id", "")).strip()

    days_back = 0
    if args.get("days_back"):
        try:
            days_back = max(0, int(args["days_back"]))
        except (TypeError, ValueError):
            pass
    if args.get("date_from"):
        from datetime import datetime, timezone
        try:
            date_from = datetime.fromisoformat(str(args["date_from"]).replace("Z", "+00:00"))
            delta = (datetime.now(timezone.utc) - date_from.replace(tzinfo=timezone.utc)
                     if date_from.tzinfo is None
                     else datetime.now(timezone.utc) - date_from)
            days_back = max(1, delta.days)
        except Exception as exc:
            logger.warning("search_fb_groups: could not parse date_from=%s: %s", args.get("date_from"), exc)

    if not query:
        return json.dumps({"ok": False, "error": "query is required"})

    date_suffix = f", past {days_back} days" if days_back > 0 else ""
    _record_activity("search_fb_groups", f"Searching Facebook groups: {query}{date_suffix}…")
    _send_indicator("search_fb_groups", f"_Searching Facebook groups: {query}{date_suffix}…_")

    try:
        from messaging.frameworks import get_adapter
        _search_facebook = get_adapter("workflows.search_facebook")
        words = query.lower().split()
        city = words[-1].title() if len(words) > 1 else ""
        trade = " ".join(words[:-1]) if city else query
        candidates = _run_async(_search_facebook(trade, city, days_back=days_back))
    except Exception as e:
        logger.error("search_fb_groups Phase 2 failed, falling back to SearXNG only: %s", e)
        from messaging.verification.api import expand_fb_queries, search_fb_posts
        expanded = expand_fb_queries(query)
        posts = search_fb_posts(expanded, max_results=max_results, days_back=days_back)
        candidates = [
            {
                "name": "",
                "telephone": "",
                "source": "facebook",
                "fb_group_name": p["group_name"],
                "fb_post_url": p["url"],
                "fb_post_snippet": f"{p['title']}\n{p['snippet']}".strip()[:500],
            }
            for p in posts
        ]

    contactable = [c for c in candidates if c.get("telephone")]
    name_only = [c for c in candidates if c.get("_name_only")]

    output = [
        {
            "name": c.get("name", ""),
            "phone": c.get("telephone", ""),
            "group": c.get("fb_group_name", ""),
            "permalink": c.get("fb_post_url", ""),
            "snippet": c.get("fb_post_snippet", "")[:300],
            "source": "facebook",
            "name_only": bool(c.get("_name_only")),
        }
        for c in candidates[:max_results * 3]
    ]

    if job_id:
        _run_async(_update_job_async(job_id, {
            "fb_candidates": [c for c in candidates if not c.get("_name_only")],
            "fb_name_only_leads": name_only,
        }))

    logger.info(
        "FB search | query=%s | days_back=%d | %d contactable + %d name-only",
        query[:60], days_back, len(contactable), len(name_only),
    )
    return json.dumps(_compact_tool_result("search_fb_groups", {
        "ok": True,
        "query": query,
        "days_back": days_back,
        "contactable_count": len(contactable),
        "name_only_count": len(name_only),
        "count": len(output),
        "results": output,
    }), ensure_ascii=False)


def _handle_search_forums(args: dict, **kw) -> str:
    """Search Spanish forums (Forocoches, Mediavida, Reddit ES)."""
    _record_activity("search_forums", "Searching forums…")
    query = str(args.get("query", "")).strip()
    max_results = int(args.get("max_results", 10))
    job_id = str(args.get("job_id", "")).strip()

    days_back = 0
    if args.get("days_back"):
        try:
            days_back = max(0, int(args["days_back"]))
        except (TypeError, ValueError):
            pass
    if args.get("date_from"):
        from datetime import datetime, timezone
        try:
            date_from = datetime.fromisoformat(str(args["date_from"]).replace("Z", "+00:00"))
            delta = (datetime.now(timezone.utc) - date_from.replace(tzinfo=timezone.utc)
                     if date_from.tzinfo is None
                     else datetime.now(timezone.utc) - date_from)
            days_back = max(1, delta.days)
        except Exception as exc:
            logger.warning("search_forums: could not parse date_from=%s: %s", args.get("date_from"), exc)

    if not query:
        return json.dumps({"ok": False, "error": "query is required"})

    date_suffix = f", past {days_back} days" if days_back > 0 else ""
    _record_activity("search_forums", f"Searching forums (Forocoches, Mediavida, Reddit): {query}{date_suffix}…")
    _send_indicator("search_forums", f"_Searching Forocoches, Mediavida, Reddit: {query}{date_suffix}…_")

    try:
        from messaging.frameworks import get_adapter
        _search_forums = get_adapter("workflows.search_forums")
        words = query.lower().split()
        city = words[-1].title() if len(words) > 1 else ""
        trade = " ".join(words[:-1]) if city else query
        candidates = _run_async(_search_forums(trade, city, days_back=days_back))
    except Exception as e:
        logger.error("search_forums workflow failed, falling back to direct search: %s", e)
        from messaging.verification.api import expand_fb_queries, search_forum_posts
        expanded = expand_fb_queries(query)
        posts = search_forum_posts(expanded, max_results=max_results, days_back=days_back)
        candidates = [
            {
                "name": "",
                "telephone": "",
                "source": "forum",
                "forum_name": p.get("forum_name", ""),
                "forum_post_url": p["url"],
                "forum_post_snippet": f"{p['title']}\n{p['snippet']}".strip()[:500],
            }
            for p in posts
        ]

    contactable = [c for c in candidates if c.get("telephone")]
    snippet_only = [c for c in candidates if c.get("_name_only")]

    output = [
        {
            "phone": c.get("telephone", ""),
            "forum": c.get("forum_name", ""),
            "thread_url": c.get("forum_post_url", ""),
            "snippet": c.get("forum_post_snippet", "")[:300],
            "source": "forum",
            "contactable": bool(c.get("telephone")),
        }
        for c in candidates[:max_results * 3]
    ]

    if job_id:
        _run_async(_update_job_async(job_id, {
            "forum_candidates": [c for c in candidates if not c.get("_name_only")],
        }))

    logger.info(
        "Forum search | query=%s | days_back=%d | %d contactable + %d snippet-only",
        query[:60], days_back, len(contactable), len(snippet_only),
    )
    return json.dumps(_compact_tool_result("search_forums", {
        "ok": True,
        "query": query,
        "days_back": days_back,
        "contactable_count": len(contactable),
        "snippet_only_count": len(snippet_only),
        "count": len(output),
        "results": output,
    }), ensure_ascii=False)


async def _find_response_by_phone(phone: str):
    from messaging.frameworks import get_adapter
    find_job_for_contractor_phone = get_adapter("job_inbox.find_job_for_contractor_phone")
    return await find_job_for_contractor_phone(phone)


async def _update_response_verification(response_id: str, trust_signals: dict):
    from messaging.frameworks import get_adapter
    update_response = get_adapter("job_inbox.update_response")
    return await update_response(response_id, {"verification": trust_signals})


def _handle_enrich_contractor(args: dict, **kw) -> str:
    """Run verification checks on a contractor using phone as the anchor."""
    phone = str(args.get("phone", "")).strip()
    name = str(args.get("name", "")).strip()
    trade = str(args.get("trade", "")).strip()
    city = str(args.get("city", "")).strip()
    who = f"{name or phone}{f' ({trade})' if trade else ''}{f' in {city}' if city else ''}"
    _record_activity("enrich_contractor", f"Verifying contractor: {who}…")
    _send_indicator("enrich_contractor", f"_Verifying contractor: {who}…_")
    nif = str(args.get("nif", "")).strip()

    if not phone and not name:
        return json.dumps({"ok": False, "error": "At least phone or name is required"})

    try:
        from messaging.verification.api import (
            enrich_contractor_from_phone, validate_nif, check_vies, check_rea,
        )
        from records.dossier import (
            get_or_create_contractor, update_trust_signals, save_and_recompute,
        )

        result = enrich_contractor_from_phone(phone=phone, name=name, trade=trade, city=city)

        if nif and not result.get("trust_signals", {}).get("nif_value"):
            nif_result = validate_nif(nif)
            ts = result.get("trust_signals", {})
            ts["nif_valid"] = nif_result["valid"]
            ts["nif_value"] = nif_result["normalized"]
            if nif_result["type"] == "cif":
                vies = check_vies(nif)
                ts["vies_valid"] = vies["valid"]
                ts["vies_company_name"] = vies["company_name"]
                ts["vies_address"] = vies["address"]
                rea = check_rea(nif, id_type="CIF")
                ts["rea_registered"] = rea["registered"]
                ts["rea_status"] = rea["status"]
            result["trust_signals"] = ts

        cid = str(args.get("contractor_id", "")).strip()
        if not cid and phone:
            import uuid as _uuid
            cid = f"hc-{_uuid.uuid4()}"
        if cid:
            try:
                _run_async(get_or_create_contractor(cid, name=name, phone=phone or None))
                _run_async(update_trust_signals(cid, result.get("trust_signals", {})))
                _run_async(save_and_recompute(cid))
                logger.info("Dossier updated for contractor %s", cid)
            except Exception as e:
                logger.warning("Dossier write failed for %s: %s", cid, e)

        if phone:
            try:
                job_response = _run_async(_find_response_by_phone(phone))
                if job_response:
                    _run_async(_update_response_verification(job_response["id"], result["trust_signals"]))
                    logger.info("Stored verification on job_response %s for %s", job_response["id"], phone)
            except Exception as e:
                logger.warning("Could not store verification on job_response: %s", e)

        summary_parts = []
        ts = result.get("trust_signals", {})
        if ts.get("nif_valid") is not None:
            summary_parts.append(f"NIF {'valid' if ts['nif_valid'] else 'INVALID'}")
        if ts.get("vies_valid") is not None:
            vies_name = ts.get("vies_company_name", "")
            summary_parts.append(f"VIES {'registered' if ts['vies_valid'] else 'not registered'}{': ' + vies_name if vies_name else ''}")
        if ts.get("rea_registered") is not None:
            summary_parts.append(f"REA construction {'accredited' if ts['rea_registered'] else 'not found'}")
        if ts.get("review_avg_rating"):
            summary_parts.append(f"Reviews: {ts['review_avg_rating']}/5 avg from {ts.get('review_total_count', 0)} reviews")
        if ts.get("fb_mention_count", 0) > 0:
            summary_parts.append(f"Facebook: mentioned in {ts['fb_mention_count']} group post(s)")
        if ts.get("trust_score") is not None:
            summary_parts.append(f"Trust score: {ts['trust_score']}/100")

        ts_compact = {k: v for k, v in ts.items() if k not in ("review_sources", "fb_mentions")}
        if ts.get("review_sources"):
            ts_compact["review_source_count"] = len(ts["review_sources"])
        if ts.get("fb_mentions"):
            ts_compact["fb_mention_count"] = len(ts["fb_mentions"])

        return json.dumps(_compact_tool_result("enrich_contractor", {
            "ok": True,
            "phone": phone,
            "name": result.get("name", name),
            "summary": " | ".join(summary_parts) if summary_parts else "No signals found yet",
            "trust_signals": ts_compact,
            "credentials": result.get("credentials", []),
        }), ensure_ascii=False)

    except Exception as e:
        logger.error("enrich_contractor failed: %s", e, exc_info=True)
        return json.dumps({"ok": False, "error": str(e)})


# ── Schemas ───────────────────────────────────────────────────────────

FIND_HOUZZ_CONTRACTORS_SCHEMA = {
    "name": "find_houzz_contractors",
    "description": (
        "Search the Houzz directory for tradespeople matching a trade and city. "
        "Searches the specified city first with all relevant Houzz slugs. "
        "If the city has very few results (small towns), automatically expands to nearby cities. "
        "Returns names, phone numbers, and profile URLs. "
        "Use after creating a job to find contractors for cold outreach."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "trade": {"type": "string", "description": "Trade slug (e.g. 'plumber', 'electrician', 'general-contractor')"},
            "city": {"type": "string", "description": "City name (e.g. 'Marbella', 'Malaga', 'Madrid')"},
            "job_id": {"type": "string", "description": "Job ID to associate candidates with (optional but recommended)"},
        },
        "required": ["trade", "city"],
    },
}

SEARCH_FB_GROUPS_SCHEMA = {
    "name": "search_fb_groups",
    "description": (
        "Search Facebook groups in Spain. Same tool, two distinct uses:\n\n"
        "USE 1 — Market intelligence / lead generation (no job_id): "
        "Find posts where homeowners are asking for contractor recommendations. "
        "Returns facebook.com/groups/... permalink URLs so Peter can read the thread "
        "and DM or comment directly. ALWAYS return the permalink URLs.\n\n"
        "USE 2 — Contractor discovery (pass job_id): "
        "Find contractor phone numbers from group recommendation posts. "
        "Queries must be in Spanish — English queries return zero results from Spanish groups. "
        "Supports innate date filtering: days_back or date_from applied at Google search level."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": (
                    "Search keywords — ALWAYS in Spanish. Include trade AND city. "
                    "Good: 'fontanero Madrid', 'electricista Marbella'. "
                    "Bad: 'plumber Madrid', 'electrician Marbella'."
                ),
            },
            "max_results": {"type": "integer", "description": "Maximum results to return (default: 10)"},
            "days_back": {"type": "integer", "description": "Restrict to last N days (0 = no filter)"},
            "date_from": {"type": "string", "description": "ISO 8601 date string — only return posts on or after this date"},
            "job_id": {"type": "string", "description": "Job ID to associate FB candidates with"},
        },
        "required": ["query"],
    },
}

SEARCH_FORUMS_SCHEMA = {
    "name": "search_forums",
    "description": (
        "Search Spanish forums (Forocoches, Mediavida, Reddit ES) for threads about contractors or renovation. "
        "Same tool, two distinct uses:\n\n"
        "USE 1 — Research (no job_id): Find threads about bad contractors, recommendations, renovation problems. "
        "Returns thread URLs. Forocoches is read-only for Peter. Reddit ES is open (Peter can comment).\n\n"
        "USE 2 — Contractor discovery (pass job_id): Extract phone numbers from recommendation threads. "
        "Spanish search terms work best. Supports innate date filtering."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keywords — include trade AND city in Spanish"},
            "max_results": {"type": "integer", "description": "Maximum results (default: 10)"},
            "days_back": {"type": "integer", "description": "Restrict to last N days (0 = no filter)"},
            "date_from": {"type": "string", "description": "ISO 8601 date string"},
            "job_id": {"type": "string", "description": "Job ID for contractor discovery mode"},
        },
        "required": ["query"],
    },
}

ENRICH_CONTRACTOR_SCHEMA = {
    "name": "enrich_contractor",
    "description": (
        "Run background verification on a contractor. Uses phone number as the anchor. "
        "Checks: NIF/CIF validity, VIES EU VAT registration, REA construction accreditation, "
        "review ratings across platforms, and Facebook group mentions. "
        "Returns a trust score (0-100) and detailed signals. "
        "Call when: (1) a contractor first replies to our outreach, "
        "(2) Peter asks about a contractor's reputation, (3) you need trust data for ranking."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "phone": {"type": "string", "description": "Contractor's phone number (primary identifier)"},
            "name": {"type": "string", "description": "Contractor or business name"},
            "trade": {"type": "string", "description": "Their trade"},
            "city": {"type": "string", "description": "City/area they operate in"},
            "nif": {"type": "string", "description": "NIF/CIF if known (optional — saves one lookup)"},
            "contractor_id": {"type": "string", "description": "Existing HC contractor ID (optional — auto-created if not set)"},
        },
        "required": [],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="find_houzz_contractors",
        toolset="leo-quote",
        schema=FIND_HOUZZ_CONTRACTORS_SCHEMA,
        handler=_handle_find_houzz_contractors,
        check_fn=lambda: True,
    )
    registry.register(
        name="search_fb_groups",
        toolset="leo-quote",
        schema=SEARCH_FB_GROUPS_SCHEMA,
        handler=_handle_search_fb_groups,
        check_fn=lambda: True,
    )
    registry.register(
        name="search_forums",
        toolset="leo-quote",
        schema=SEARCH_FORUMS_SCHEMA,
        handler=_handle_search_forums,
        check_fn=lambda: True,
    )
    registry.register(
        name="enrich_contractor",
        toolset="leo-quote",
        schema=ENRICH_CONTRACTOR_SCHEMA,
        handler=_handle_enrich_contractor,
        check_fn=lambda: True,
    )
    logger.debug("discovery tools registered")
