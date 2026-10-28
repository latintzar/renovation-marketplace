"""records.dossier — ``contractors`` table owner + canvas recomputation.

The contractors table is split into three jsonb columns:

- ``provenance`` — how Leo first learned of this contractor.
- ``dossier`` — the internal record (sources, trust_signals,
  conversation_notes, identity_overrides, work_history_*).
- ``canvas`` — the derived public view surfaced on the shareable URL.

Every write goes through this module; direct table writes from route
handlers are a regression (the ``packages_no_shared`` + layer gates
catch them).

:func:`recompute_canvas` is **pure** — dossier in, canvas dict out,
no I/O. Route handlers use it to rebuild the public view deterministically
from scraped data + conversation corrections.

Two-phase write discipline in :func:`add_contractor_source`: the
``dossier`` column patches alone first (it can never trigger a unique-
constraint violation), and only then does the optional name/phone
patch fire — a 409 on the identity patch never rolls back the dossier
write.

Moved from ``packages/storage/src/storage/dossier.py`` in Phase 5
Wave 3. In Wave 6 the duplicate implementation that lived at
``packages/messaging/src/messaging/dossier/contractor.py`` was
retired and its callers rewritten to import from here; this module
is now the single source of truth for the ``contractors`` table.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Set, Tuple

from core import http_client, sb_headers, sb_key, sb_url

from .types import Contractor

logger = logging.getLogger(__name__)

_UPSERT_TIMEOUT = 15.0
_PATCH_TIMEOUT = 15.0
_SELECT_TIMEOUT = 10.0


async def _upsert(row: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = sb_url()
    key = sb_key()
    if not url or not key:
        logger.error("Supabase credentials not configured")
        return None
    async with http_client(timeout=_UPSERT_TIMEOUT) as client:
        resp = await client.post(
            f"{url}/contractors",
            json=row,
            headers={
                **sb_headers(),
                "Prefer": "resolution=merge-duplicates,return=representation",
            },
        )
        if resp.status_code in (200, 201):
            rows = resp.json()
            return rows[0] if rows else row
        logger.error(
            "Supabase contractors upsert failed | %d %s",
            resp.status_code, resp.text[:300],
        )
        return None


async def _patch(contractor_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    url = sb_url()
    key = sb_key()
    if not url or not key:
        return None
    async with http_client(timeout=_PATCH_TIMEOUT) as client:
        resp = await client.patch(
            f"{url}/contractors",
            params={"id": f"eq.{contractor_id}"},
            json=updates,
            headers={**sb_headers(), "Prefer": "return=representation"},
        )
        if resp.status_code in (200, 204):
            rows = resp.json() if resp.text else []
            return rows[0] if rows else updates
        logger.error(
            "Supabase contractors patch failed | %d %s",
            resp.status_code, resp.text[:300],
        )
        return None


async def _select(column: str, value: str) -> Optional[Dict[str, Any]]:
    url = sb_url()
    key = sb_key()
    if not url or not key:
        return None
    async with http_client(timeout=_SELECT_TIMEOUT) as client:
        resp = await client.get(
            f"{url}/contractors",
            params={column: f"eq.{value}", "select": "*", "limit": "1"},
            headers={"apikey": key, "Authorization": f"Bearer {key}"},
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


async def get_or_create_contractor(
    contractor_id: str,
    *,
    name: str = "",
    phone: Optional[str] = None,
    provenance: Optional[Dict[str, Any]] = None,
) -> Contractor:
    """Idempotent. If a row with this id exists, patch missing fields.
    Otherwise upsert a new row.

    Invariant: ``canvas_token == id`` after this call, unconditionally.
    Fixes historic rows where the invariant was violated.
    """

    row: Dict[str, Any] = {"id": contractor_id, "canvas_token": contractor_id}
    if name:
        row["name"] = name
    if phone:
        row["phone"] = phone
    if provenance:
        row["provenance"] = provenance

    existing = await _select("id", contractor_id)
    if existing:
        if existing.get("canvas_token") != contractor_id:
            await _patch(contractor_id, {"canvas_token": contractor_id})
            existing["canvas_token"] = contractor_id
        if name and not existing.get("name"):
            await _patch(contractor_id, {"name": name})
            existing["name"] = name
        if phone and not existing.get("phone"):
            await _patch(contractor_id, {"phone": phone})
            existing["phone"] = phone
        return _row_to_contractor(existing)

    result = await _upsert(row)
    if result:
        logger.info("Created contractor | id=%s name=%s", contractor_id, name[:40] if name else "")
        return _row_to_contractor(result)
    return _row_to_contractor(row)


async def get_contractor_by_phone(phone: str) -> Optional[Contractor]:
    """Index-hit lookup by unique ``phone`` column. Returns ``None`` if not found."""

    if not phone:
        return None
    row = await _select("phone", phone)
    return _row_to_contractor(row) if row else None


async def get_contractor_by_token(canvas_token: str) -> Optional[Contractor]:
    """Index-hit lookup by ``canvas_token``.

    At creation ``canvas_token == id``, so this resolves both shareable
    URLs (``/canvas/{token}``) and direct ``/canvas/{id}`` paths.
    """

    if not canvas_token:
        return None
    row = await _select("canvas_token", canvas_token)
    return _row_to_contractor(row) if row else None


async def set_contractor_phone(contractor_id: str, phone: str) -> Optional[Contractor]:
    """Set or update the phone column on a contractor row."""

    logger.info(
        "Setting phone | contractor=%s phone=%s",
        contractor_id, (phone or "")[:6] + "***",
    )
    result = await _patch(contractor_id, {"phone": phone})
    return _row_to_contractor(result) if result else None


async def add_contractor_source(
    contractor_id: str,
    source_data: Dict[str, Any],
) -> Optional[Contractor]:
    """Append a scraped profile to ``dossier.sources[]``, deduplicating
    by ``(platform, source_url)``.

    **Two-phase write** (load-bearing invariant): PATCH the ``dossier``
    column alone first, THEN optionally patch name/phone. Never bundle
    identity fields into the dossier PATCH — if the phone/name belongs
    to another contractor, the whole write is rejected with 409 and
    the dossier is lost.
    """

    row = await _select("id", contractor_id)
    if not row:
        created = await get_or_create_contractor(contractor_id)
        row = {
            "id": created.id,
            "canvas_token": created.canvas_token,
            "name": created.name,
            "phone": created.phone,
            "provenance": created.provenance,
            "dossier": dict(created.dossier),
            "canvas": created.canvas,
        }

    dossier = row.get("dossier") or {}
    sources = dossier.get("sources", [])

    platform = source_data.get("source", "")
    source_url = source_data.get("source_url", "")
    source_data = {**source_data, "scraped_at": datetime.now(timezone.utc).isoformat()}

    existing_idx = None
    for i, s in enumerate(sources):
        if s.get("source") == platform and s.get("source_url") == source_url:
            existing_idx = i
            break

    if existing_idx is not None:
        sources[existing_idx] = source_data
        logger.info(
            "Updated source | contractor=%s platform=%s",
            contractor_id, platform,
        )
    else:
        sources.append(source_data)
        logger.info(
            "Added source | contractor=%s platform=%s total=%d",
            contractor_id, platform, len(sources),
        )

    dossier["sources"] = sources

    result = await _patch(contractor_id, {"dossier": dossier})
    if result is None:
        logger.error(
            "add_contractor_source: dossier patch failed for contractor %s",
            contractor_id,
        )
        return None

    name_from_source = source_data.get("name", "")
    phone_from_source = source_data.get("phone", "")
    identity_updates: Dict[str, Any] = {}
    if name_from_source and not row.get("name"):
        identity_updates["name"] = name_from_source
    if phone_from_source and not row.get("phone"):
        identity_updates["phone"] = phone_from_source

    if identity_updates:
        id_result = await _patch(contractor_id, identity_updates)
        if id_result is None:
            logger.warning(
                "add_contractor_source: identity patch failed for %s "
                "(phone/name likely belongs to another contractor — dossier saved OK)",
                contractor_id,
            )

    return _row_to_contractor(result)


async def update_trust_signals(
    contractor_id: str,
    signals: Dict[str, Any],
) -> Optional[Contractor]:
    """Write verification results to ``dossier.trust_signals``.

    Expected keys: ``trust_score`` (int 0-100), ``nif_valid`` (bool),
    ``fb_mentions`` (list), ``forum_mentions`` (list). The merge is
    additive — ``dossier.trust_signals`` becomes ``signals`` (replacing
    prior values, but legacy callers already pass the full expected
    signal dict; preserved verbatim).
    """

    row = await _select("id", contractor_id)
    if not row:
        return None

    dossier = row.get("dossier") or {}
    dossier["trust_signals"] = signals
    logger.info(
        "Updated trust signals | contractor=%s score=%s",
        contractor_id, signals.get("trust_score", "?"),
    )
    result = await _patch(contractor_id, {"dossier": dossier})
    return _row_to_contractor(result) if result else None


async def add_conversation_note(
    contractor_id: str,
    note: str,
) -> Optional[Contractor]:
    """Append ``{text, timestamp}`` to ``dossier.conversation_notes``."""

    row = await _select("id", contractor_id)
    if not row:
        return None

    dossier = row.get("dossier") or {}
    notes = dossier.get("conversation_notes", [])
    notes.append({
        "text": note,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    dossier["conversation_notes"] = notes
    result = await _patch(contractor_id, {"dossier": dossier})
    return _row_to_contractor(result) if result else None


async def update_identity_overrides(
    contractor_id: str,
    overrides: Dict[str, Any],
) -> Optional[Contractor]:
    """Store conversation corrections (business_name, trade, NIF given verbally).

    Overrides take highest priority in :func:`recompute_canvas`.
    ``dossier.identity_overrides.updated_at`` is stamped. If the caller
    provides ``name`` or ``business_name``, the top-level ``name``
    column is patched in the same request.
    """

    row = await _select("id", contractor_id)
    if not row:
        return None

    dossier = row.get("dossier") or {}
    existing = dossier.get("identity_overrides", {}) or {}
    for k, v in overrides.items():
        if v:
            existing[k] = v
    existing["updated_at"] = datetime.now(timezone.utc).isoformat()
    dossier["identity_overrides"] = existing

    updates: Dict[str, Any] = {"dossier": dossier}
    if overrides.get("name") or overrides.get("business_name"):
        updates["name"] = overrides.get("name") or overrides.get("business_name")

    logger.info(
        "Updated identity overrides | contractor=%s keys=%s",
        contractor_id, list(overrides.keys()),
    )
    result = await _patch(contractor_id, updates)
    return _row_to_contractor(result) if result else None


def recompute_canvas(dossier: Dict[str, Any]) -> Dict[str, Any]:
    """Pure function: dossier in, canvas dict out.

    Source priority (highest wins):

    1. **Conversation overrides** (``dossier.identity_overrides``) —
       corrections Leo captured in chat.
    2. **Most-reviewed platform** — ``max(source.review_count)`` across
       ``dossier.sources[]``. Rationale: the platform where the
       contractor invests most effort has the richest data.
    3. **Most recent scrape** — tiebreaker when review counts tie.

    Per-source fields NEVER merge: ``reviews[]``, ``projects[]``,
    ``rating``, ``review_count`` stay attributed per-platform.

    Aggregate fields that ARE merged: ``portfolio_images`` (URL-
    deduped union), ``review_summary`` (first non-empty),
    ``social_mentions`` (``trust_signals.fb_mentions +
    forum_mentions``).

    Returns the canvas dict; never raises (missing fields become
    empty strings / zeros / ``None`` / empty lists).
    """

    sources = dossier.get("sources", []) or []
    overrides = dossier.get("identity_overrides", {}) or {}
    trust = dossier.get("trust_signals", {}) or {}

    def _best_source() -> Dict[str, Any]:
        if not sources:
            return {}
        ranked = sorted(
            sources,
            key=lambda s: (s.get("review_count", 0), s.get("scraped_at", "")),
            reverse=True,
        )
        return ranked[0]

    best = _best_source()

    def _field(key: str, override_key: Optional[str] = None) -> str:
        ok = override_key or key
        if overrides.get(ok):
            return str(overrides[ok])
        if best.get(key):
            return str(best[key])
        for s in sources:
            if s.get(key):
                return str(s[key])
        return ""

    profile_sources: list = []
    for s in sources:
        ps: Dict[str, Any] = {
            "platform": s.get("source", ""),
            "platform_url": s.get("source_url", ""),
            "rating": s.get("rating"),
            "review_count": s.get("review_count", 0),
            "scraped_at": s.get("scraped_at", ""),
        }
        reviews_raw = s.get("reviews", []) or []
        ps["reviews"] = [
            {
                "author": r.get("reviewer_name") or r.get("author", ""),
                "rating": r.get("rating"),
                "date": r.get("date", ""),
                "text": r.get("text", ""),
            }
            for r in reviews_raw
        ]
        projects_raw = s.get("projects", []) or []
        ps["projects"] = [
            {
                "title": p.get("title", ""),
                "description": p.get("description", ""),
                "images": p.get("images", []),
                "url": p.get("url", ""),
                "source": s.get("source", ""),
            }
            for p in projects_raw
        ]
        profile_sources.append(ps)

    seen_imgs: Set[str] = set()
    portfolio: list = []
    for s in sources:
        for img in s.get("portfolio_images", []) or []:
            if img and img not in seen_imgs:
                seen_imgs.add(img)
                portfolio.append(img)
        for proj in s.get("projects", []) or []:
            for img in (proj.get("images") or []):
                if img and img not in seen_imgs:
                    seen_imgs.add(img)
                    portfolio.append(img)

    avatar = overrides.get("avatar_url", "") or ""
    if not avatar:
        for s in sources:
            if s.get("avatar_url"):
                avatar = s["avatar_url"]
                break

    services_raw: Any = _field("services")
    if isinstance(services_raw, list):
        services_str = "\n".join(services_raw)
    elif isinstance(services_raw, str) and "," in services_raw and "\n" not in services_raw:
        services_str = "\n".join(s.strip() for s in services_raw.split(","))
    else:
        services_str = str(services_raw) if services_raw else ""

    review_summary = ""
    for s in sources:
        if s.get("review_summary"):
            review_summary = s["review_summary"]
            break

    social_mentions: list = []
    for m in trust.get("fb_mentions", []) or []:
        social_mentions.append({
            "source_name": m.get("source_name") or m.get("group_name") or "Facebook group",
            "url": m.get("url", ""),
            "snippet": m.get("snippet", ""),
            "author_name": m.get("author_name"),
            "author_url": m.get("author_url"),
            "author_avatar": m.get("author_avatar"),
            "date": m.get("date"),
        })
    for m in trust.get("forum_mentions", []) or []:
        social_mentions.append({
            "source_name": m.get("source_name") or m.get("forum_name") or "Forum",
            "url": m.get("url", ""),
            "snippet": m.get("snippet", ""),
            "date": m.get("date"),
        })

    canvas: Dict[str, Any] = {
        "business_name": _field("name", "business_name"),
        "trade": _field("trade"),
        "location": _field("location"),
        "service_area_km": _field("service_area_km") or "",
        "services": services_str,
        "bio": _field("description", "bio") or _field("raw_about", "bio"),
        "years_experience": _field("years_experience"),
        "languages": _field("languages") or "",
        "certifications": _field("certifications") or "",
        "avatar_url": avatar,
        "website": _field("website"),
        "portfolio_images": portfolio[:50],
        "sources": profile_sources,
        "review_summary": review_summary,
        "verified": (trust.get("trust_score") or 0) >= 60,
        "trust_score": trust.get("trust_score"),
        "nif_verified": trust.get("nif_valid"),
        "leo_jobs_completed": dossier.get("work_history_count", 0),
        "leo_rating": dossier.get("work_history_avg_rating"),
        "social_mentions": social_mentions if social_mentions else None,
    }

    return canvas


async def save_and_recompute(contractor_id: str) -> Dict[str, Any]:
    """Read dossier, compute canvas, write canvas back, return canvas.

    **Not transactional** — if the PATCH fails between compute and write,
    the canvas column is stale. Mitigated by deterministic recompute:
    the canvas is rebuildable from dossier at any time.
    """

    row = await _select("id", contractor_id)
    if not row:
        logger.warning("save_and_recompute: contractor %s not found", contractor_id)
        return {}

    dossier = row.get("dossier") or {}
    canvas = recompute_canvas(dossier)

    await _patch(contractor_id, {"canvas": canvas})
    logger.info(
        "Canvas recomputed | contractor=%s business=%s score=%s",
        contractor_id,
        (canvas.get("business_name") or "")[:30],
        canvas.get("trust_score", "?"),
    )
    return canvas


save_and_recompute_canvas = save_and_recompute  # back-compat alias


# ── Short-form aliases (used by scope routes and agent tools) ────────
# The canonical names are the long forms (``get_or_create_contractor``,
# etc.) but historically scope code also used shorter names that the
# old ``messaging.dossier.contractor`` module exposed. Aliased here to
# avoid a sweeping caller-rewrite during Wave 6.
get_or_create = get_or_create_contractor
get_by_phone = get_contractor_by_phone
get_by_token = get_contractor_by_token
set_phone = set_contractor_phone
add_source = add_contractor_source


def _row_to_contractor(row: Optional[Dict[str, Any]]) -> Contractor:
    row = row or {}
    return Contractor(
        id=str(row.get("id") or ""),
        canvas_token=str(row.get("canvas_token") or row.get("id") or ""),
        name=row.get("name"),
        phone=row.get("phone"),
        provenance=row.get("provenance"),
        dossier=row.get("dossier") or {},
        canvas=row.get("canvas"),
        created_at=_parse_ts(row.get("created_at")),
        updated_at=_parse_ts(row.get("updated_at")),
    )


def _parse_ts(raw: Any) -> Optional[datetime]:
    if not raw:
        return None
    if isinstance(raw, datetime):
        return raw
    try:
        return datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


__all__ = [
    # Canonical long-form names.
    "get_or_create_contractor",
    "get_contractor_by_phone",
    "get_contractor_by_token",
    "set_contractor_phone",
    "add_contractor_source",
    "update_trust_signals",
    "add_conversation_note",
    "update_identity_overrides",
    "recompute_canvas",
    "save_and_recompute",
    "save_and_recompute_canvas",
    # Short-form aliases (back-compat with the retired
    # messaging.dossier.contractor module).
    "get_or_create",
    "get_by_phone",
    "get_by_token",
    "set_phone",
    "add_source",
]
