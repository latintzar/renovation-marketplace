"""
leo_agent/tools/canvas.py — Leo document canvas and UI drawer tools.

Tools: update_brief, update_profile, update_quote, set_drawer
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict

from ..tool_utils import (
    _get_ctx_val, _get_state, _record_activity, _run_async, leo_ctx,
)

logger = logging.getLogger(__name__)


def _parse_contingency_drafts(raw: Any) -> list[dict]:
    """Structured 'if we discover X' drafts inserted between quote milestones."""
    out: list[dict] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("after_phase_index", -999))
        except (TypeError, ValueError):
            continue
        title = str(item.get("title", "")).strip()
        reason = str(item.get("reason", "")).strip()
        lis_raw = item.get("line_items", [])
        lis: list[dict] = []
        if isinstance(lis_raw, list):
            for li in lis_raw:
                if isinstance(li, dict):
                    lis.append(
                        {
                            "description": str(li.get("description", "")).strip(),
                            "amount": float(li.get("amount", 0) or 0),
                        }
                    )
        if not title and not reason and not lis:
            continue
        draft: dict = {
            "after_phase_index": idx,
            "title": title,
            "reason": reason,
            "line_items": lis,
        }
        mlow = item.get("market_range_low")
        mhigh = item.get("market_range_high")
        if mlow is not None:
            try:
                draft["market_range_low"] = float(mlow)
            except (TypeError, ValueError):
                pass
        if mhigh is not None:
            try:
                draft["market_range_high"] = float(mhigh)
            except (TypeError, ValueError):
                pass
        out.append(draft)
    return out


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_update_brief(args: dict, **kw) -> str:
    # In quote mode (contractor building a presupuesto), route through update_quote.
    # Hermes sometimes picks update_brief because it's more familiar; this intercept
    # ensures the correct state key gets set regardless of which tool name is used.
    mode = _get_ctx_val("mode") or ""
    if mode == "quote":
        logger.info("update_brief called in quote mode — rerouting to update_quote")
        return _handle_update_quote(args, **kw)

    _record_activity("update_brief")
    brief = {
        "title": str(args.get("title", "")).strip(),
        "description": str(args.get("description", "")).strip(),
        "location": str(args.get("location", "")).strip(),
        "urgency": str(args.get("urgency", "")).strip(),
        "materials_mentioned": str(args.get("materials_mentioned", "")).strip(),
        "measurements": str(args.get("measurements", "")).strip(),
        "budget_indication": str(args.get("budget_indication", "")).strip(),
        "status": str(args.get("status", "needs_more_info")).strip(),
    }
    state = _get_state()
    state["brief_update"] = brief
    if brief["status"] in ("workable", "solid"):
        state["show_drawer"] = True
        if "drawer_state" not in state:
            state["drawer_state"] = {
                "content_type": "brief",
                "auto_open": True,
                "accent": "default",
            }
            if brief["status"] == "solid":
                state["drawer_state"]["status_text"] = "Ready to submit"
                state["drawer_state"]["accent"] = "highlight"

    from ..peter_notify import patch_lead_structured
    phone = _get_ctx_val("lead_phone")
    if phone:
        _run_async(patch_lead_structured(phone=str(phone), brief=brief))
    if brief["status"] in ("workable", "solid"):
        from ..peter_notify import notify_brief_confirmed
        _run_async(notify_brief_confirmed(brief, phone=str(phone) if phone else ""))
    logger.info("Leo update_brief | title=%s status=%s", brief["title"][:60], brief["status"])
    return json.dumps({"ok": True, "saved": "brief"}, ensure_ascii=False)


def _handle_update_profile(args: dict, **kw) -> str:
    _record_activity("update_profile")
    profile = {
        "business_name": str(args.get("business_name", "")).strip(),
        "trade": str(args.get("trade", "")).strip(),
        "location": str(args.get("location", "")).strip(),
        "service_area_km": str(args.get("service_area_km", "")).strip(),
        "services": str(args.get("services", "")).strip(),
        "bio": str(args.get("bio", "")).strip(),
        "years_experience": str(args.get("years_experience", "")).strip(),
        "languages": str(args.get("languages", "")).strip(),
        "certifications": str(args.get("certifications", "")).strip(),
    }
    state = _get_state()
    state["profile_update"] = profile

    from ..peter_notify import patch_lead_structured
    phone = _get_ctx_val("lead_phone")
    if phone:
        _run_async(patch_lead_structured(phone=str(phone), profile=profile))

    cid = _get_ctx_val("contractor_id")
    if cid:
        try:
            from records.dossier import update_identity_overrides, save_and_recompute
            overrides = {k: v for k, v in profile.items() if v}
            _run_async(update_identity_overrides(str(cid), overrides))
            _run_async(save_and_recompute(str(cid)))
            logger.info("Dossier identity overrides updated for %s", cid)
        except Exception as e:
            logger.warning("Dossier update_identity_overrides failed for %s: %s", cid, e)

    logger.info("Leo update_profile | biz=%s", profile["business_name"][:60])
    return json.dumps({"ok": True, "saved": "profile"}, ensure_ascii=False)


def _handle_update_quote(args: dict, **kw) -> str:
    import json as _json

    state = _get_state()
    prev_scope = state.get("quote_update") or {}
    # Context-aware label: first draft vs. subsequent update
    is_first_draft = not bool(prev_scope.get("title") or prev_scope.get("line_items"))
    quote_label = "Creating first scope draft…" if is_first_draft else "Updating quote…"
    _record_activity("update_quote", quote_label)

    line_items_raw = args.get("line_items", [])
    line_items: list[dict] = []
    if isinstance(line_items_raw, list):
        for item in line_items_raw:
            if isinstance(item, dict):
                li: dict = {
                    "description": str(item.get("description", "")).strip(),
                    "amount": float(item.get("amount", 0) or 0),
                }
                if item.get("duration_label"):
                    li["duration_label"] = str(item["duration_label"]).strip()
                line_items.append(li)
            elif isinstance(item, str):
                # Allow "description: amount" shorthand
                parts = item.split(":", 1)
                desc = parts[0].strip()
                try:
                    amount = float(parts[1].strip()) if len(parts) > 1 else 0
                except ValueError:
                    amount = 0
                line_items.append({"description": desc, "amount": amount})

    terms_raw = args.get("terms", [])
    terms = [str(t).strip() for t in terms_raw if t] if isinstance(terms_raw, list) else []

    # materials_upfront — the ONLY advance payment (for purchasing materials)
    materials_upfront_raw = args.get("materials_upfront")
    materials_upfront: float | None = None
    if materials_upfront_raw is not None:
        try:
            materials_upfront = float(materials_upfront_raw)
        except (TypeError, ValueError):
            materials_upfront = None

    # iva_rate — 10 (residential renovation) or 21 (commercial/new build); None = already included
    iva_rate_raw = args.get("iva_rate")
    iva_rate: int | None = None
    if iva_rate_raw is not None:
        try:
            candidate = int(float(iva_rate_raw))
            if candidate in (10, 21):
                iva_rate = candidate
        except (TypeError, ValueError):
            pass

    scope = {
        "title": str(args.get("title", "")).strip(),
        "description": str(args.get("description", "")).strip(),
        "contractor_name": str(args.get("contractor_name", "")).strip(),
        "client_name": str(args.get("client_name", "")).strip(),
        "location": str(args.get("location", "")).strip(),
        "line_items": line_items,
        "service_fee_percent": float(args.get("service_fee_percent", 5) or 5),
        "terms": terms,
        "status": str(args.get("status", "draft")).strip(),
        "created_at": str(args.get("created_at", "")).strip(),
    }
    if materials_upfront is not None:
        scope["materials_upfront"] = materials_upfront
    elif prev_scope.get("materials_upfront") is not None:
        scope["materials_upfront"] = prev_scope["materials_upfront"]

    if iva_rate is not None:
        scope["iva_rate"] = iva_rate
    elif prev_scope.get("iva_rate") is not None:
        scope["iva_rate"] = prev_scope["iva_rate"]

    if "contingency_drafts" in args:
        scope["contingency_drafts"] = _parse_contingency_drafts(args.get("contingency_drafts"))
    else:
        scope["contingency_drafts"] = list(prev_scope.get("contingency_drafts") or [])

    state["quote_update"] = scope

    # Auto-open / refresh the preview as soon as the scope has a title.
    # Even without line items, the contractor wants to see it building live.
    if scope["title"]:
        state["show_drawer"] = True
        ready = scope["status"].lower() == "ready"
        has_items = bool(scope["line_items"])
        state["drawer_state"] = {
            "content_type": "scope",
            "auto_open": True,
            "accent": "highlight" if ready else "default",
            "status_text": (
                "Quote ready — tap Finalize to send"
                if ready
                else ("Building your quote…" if not has_items else "Review quote")
            ),
            "action_label": "Finalize" if ready or has_items else None,
            "action_id": "finalize_quote" if ready or has_items else None,
        }

    logger.info(
        "Leo update_quote | title=%s items=%d status=%s",
        scope["title"][:60],
        len(line_items),
        scope["status"],
    )
    return _json.dumps({"ok": True, "saved": "scope"}, ensure_ascii=False)


def _can_show_drawer() -> bool:
    """check_fn for tools that require the web chat drawer UI."""
    ctx = getattr(leo_ctx, "ctx", {})
    caps = ctx.get("capabilities")
    if caps is None:
        return True  # backwards compat: allow if no capabilities set
    return getattr(caps, "can_show_drawer", False)


def _handle_set_drawer(args: dict, **kw) -> str:
    """Control the action drawer — Hermes's dynamic UI surface. No trace emitted (internal)."""
    content_type = str(args.get("content_type", "reset")).strip()

    drawer_state: Dict[str, Any] = {
        "content_type": content_type,
        "display": str(args.get("display", "inline")).strip(),
        "status_text": str(args.get("status_text", "")).strip() or None,
        "action_label": str(args.get("action_label", "")).strip() or None,
        "action_id": str(args.get("action_id", "")).strip() or None,
        "custom_title": str(args.get("custom_title", "")).strip() or None,
        "custom_body": str(args.get("custom_body", "")).strip() or None,
        "accent": str(args.get("accent", "default")).strip(),
        "auto_open": bool(args.get("auto_open", False)),
    }
    drawer_state = {k: v for k, v in drawer_state.items() if v is not None}
    drawer_state.setdefault("content_type", content_type)

    state = _get_state()
    state["drawer_state"] = drawer_state
    if drawer_state.get("auto_open"):
        state["show_drawer"] = True

    logger.info(
        "set_drawer | type=%s accent=%s auto_open=%s",
        content_type,
        drawer_state.get("accent", "default"),
        drawer_state.get("auto_open", False),
    )
    return json.dumps({"ok": True, "drawer": content_type}, ensure_ascii=False)


# ── Schemas ───────────────────────────────────────────────────────────

UPDATE_BRIEF_SCHEMA = {
    "name": "update_brief",
    "description": (
        "Update the structured homeowner job brief from the conversation. "
        "Call whenever you learn meaningful new facts — even partial updates are valuable. "
        "Title should be short and specific (e.g. 'Upstairs Bathroom Replumb', not 'Plumbing Job'). "
        "Description should be rich structured prose capturing everything the homeowner told you — "
        "wrap key facts in **bold** (model numbers, materials, dimensions, year built, brand names, conditions). "
        "Write it as a professional project brief that gives a tradesperson full context. "
        "Set status: needs_more_info (missing key details), workable (enough to respond), or solid (comprehensive)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short job title"},
            "description": {"type": "string", "description": "Structured description of the work"},
            "location": {"type": "string"},
            "urgency": {"type": "string", "description": "e.g. flexible, soon, urgent"},
            "materials_mentioned": {"type": "string", "description": "Comma-separated or short list"},
            "measurements": {"type": "string", "description": "Sizes, sqm, etc."},
            "budget_indication": {"type": "string"},
            "status": {"type": "string", "description": "needs_more_info | workable | solid"},
        },
        "required": ["title", "description", "status"],
    },
}

UPDATE_PROFILE_SCHEMA = {
    "name": "update_profile",
    "description": (
        "Update the structured tradesperson profile from the conversation. "
        "Call when they confirm or correct details."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "business_name": {"type": "string"},
            "trade": {"type": "string"},
            "location": {"type": "string"},
            "service_area_km": {"type": "string", "description": "Approximate radius or area text"},
            "services": {"type": "string", "description": "Comma-separated services"},
            "bio": {"type": "string"},
            "years_experience": {"type": "string"},
            "languages": {"type": "string"},
            "certifications": {"type": "string"},
        },
        "required": ["business_name", "trade"],
    },
}

UPDATE_SCOPE_SCHEMA = {
    "name": "update_quote",
    "description": (
        "Build or update a structured scope of work (presupuesto) for a contractor. "
        "Call whenever you learn new facts — even partial updates are valuable. "
        "\n\nSCOPE STRUCTURE (four sections in order):\n"
        "1. description — one paragraph overview of the job\n"
        "2. line_items — one per milestone/phase, each with description + amount + duration_label\n"
        "3. materials_upfront — single € amount needed before work starts (materials only)\n"
        "4. iva_rate — 10 (residential renovation) or 21 (commercial/new build), or omit if prices include IVA\n"
        "\nPAYMENT MODEL:\n"
        "- ONLY materials_upfront is paid before work starts.\n"
        "- Every line_item is paid when that milestone is completed (escrow release per milestone).\n"
        "- Do NOT put materials as a line_item — use materials_upfront instead.\n"
        "\nSet status='draft' while building, 'ready' when all milestones have prices + IVA confirmed."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Short job title, e.g. 'Reforma de baño — Calle Mayor 12'"},
            "description": {"type": "string", "description": "One paragraph: plain language overview of all the work"},
            "contractor_name": {"type": "string", "description": "Contractor's business name"},
            "client_name": {"type": "string", "description": "Homeowner's name (if known)"},
            "location": {"type": "string", "description": "Job location / address / neighbourhood"},
            "line_items": {
                "type": "array",
                "description": "Milestones / phases. Each is paid by escrow when completed. Do NOT include materials here.",
                "items": {
                    "type": "object",
                    "properties": {
                        "description": {"type": "string", "description": "What this phase involves"},
                        "amount": {"type": "number", "description": "Cost for this phase in EUR"},
                        "duration_label": {
                            "type": "string",
                            "description": "Rough duration, e.g. '2 días', '1 semana'. Plain language.",
                        },
                    },
                    "required": ["description", "amount"],
                },
            },
            "materials_upfront": {
                "type": "number",
                "description": (
                    "€ amount contractor needs upfront to buy materials before starting. "
                    "This is the ONLY pre-work advance. Set to 0 or omit if no materials advance needed. "
                    "Ask: '¿Necesitas dinero por adelantado para materiales?'"
                ),
            },
            "iva_rate": {
                "type": "integer",
                "enum": [10, 21],
                "description": (
                    "IVA rate: 10 for residential renovation (most common — reformas de vivienda habitual), "
                    "21 for commercial premises, new builds, or general services. "
                    "Omit if the contractor says prices already include IVA."
                ),
            },
            "service_fee_percent": {
                "type": "number",
                "description": "Leo service fee percentage (default 5 — do not change unless instructed)",
            },
            "terms": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Scope terms, e.g. 'Plazo de ejecución: 10 días laborables'",
            },
            "status": {"type": "string", "description": "draft | ready"},
            "created_at": {"type": "string", "description": "ISO date string, e.g. '2026-04-08'"},
            "contingency_drafts": {
                "type": "array",
                "description": (
                    "Optional provisional 'if we discover X' extras (draft change-orders) shown between milestones. "
                    "Lets the client see possible extra cost before work starts (e.g. mold behind tiles → extra €). "
                    "after_phase_index: -1 = before first phase, 0 = after first line item, 1 = after second, etc. "
                    "Omit this field entirely to leave existing drafts unchanged; pass [] to clear all drafts."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "after_phase_index": {
                            "type": "integer",
                            "description": "Insert after this line-item index (-1 = before first phase)",
                        },
                        "title": {"type": "string", "description": "Short label, e.g. 'Hidden damp remediation'"},
                        "reason": {
                            "type": "string",
                            "description": "What would trigger this work (plain language for the homeowner)",
                        },
                        "line_items": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "amount": {"type": "number", "description": "EUR excl. IVA"},
                                },
                                "required": ["description", "amount"],
                            },
                        },
                        "market_range_low": {"type": "number"},
                        "market_range_high": {"type": "number"},
                    },
                    "required": ["after_phase_index", "title", "reason", "line_items"],
                },
            },
        },
        "required": ["title", "description", "line_items", "status"],
    },
}

SET_DRAWER_SCHEMA = {
    "name": "set_drawer",
    "description": (
        "Control the action drawer — the dynamic UI surface the user sees alongside the chat. "
        "This is YOUR interface to the user beyond text messages. You can show content, change "
        "the action button label, set a status nudge, and highlight it to draw attention. "
        "The drawer has: a status line (short nudge text), a preview toggle, and an action button. "
        "Use it to show progress, prompt the user to act, or present structured content. "
        "The default drawer shows the job brief or tradesperson profile — but you can temporarily "
        "override it with custom content for any purpose (e.g. a summary, a comparison, a checklist). "
        "Call with content_type='reset' to return to the default brief/profile view."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "content_type": {
                "type": "string",
                "enum": ["brief", "profile", "custom", "reset"],
                "description": (
                    "What to show: 'brief' (job brief), 'profile' (tradesperson), "
                    "'custom' (your own content), 'reset' (return to default view)"
                ),
            },
            "display": {
                "type": "string",
                "enum": ["inline", "banner", "fullscreen"],
                "description": (
                    "How prominent the drawer should be. "
                    "'inline' (default): normal action bar at bottom of chat. "
                    "'banner': floating card overlaying the chat — noticeable but dismissible. "
                    "'fullscreen': takes over the entire screen with a modal — use when the user "
                    "MUST act and has been ignoring gentler nudges. Use very sparingly."
                ),
            },
            "status_text": {
                "type": "string",
                "description": (
                    "Short status line shown in the action bar (e.g. 'Needs more info', "
                    "'Ready to submit', 'Review this', 'One more detail…'). Max ~40 chars."
                ),
            },
            "action_label": {
                "type": "string",
                "description": (
                    "Label for the action button (e.g. 'Post job', 'Save profile', "
                    "'Confirm', 'Continue', 'Got it'). Omit to hide the button."
                ),
            },
            "action_id": {
                "type": "string",
                "description": (
                    "Identifier for what tapping the button means. Standard: 'confirm_brief', "
                    "'confirm_profile'. Custom: any string — sent back to you as a user signal."
                ),
            },
            "custom_title": {
                "type": "string",
                "description": "Title for custom content (only used when content_type='custom')",
            },
            "custom_body": {
                "type": "string",
                "description": (
                    "Body text for custom content (markdown supported). "
                    "Only used when content_type='custom'."
                ),
            },
            "accent": {
                "type": "string",
                "enum": ["default", "highlight"],
                "description": (
                    "'highlight' gives the drawer border a brand-orange accent to draw attention. "
                    "Use sparingly — for moments that need user action."
                ),
            },
            "auto_open": {
                "type": "boolean",
                "description": "If true, the drawer slides open automatically.",
            },
        },
        "required": ["content_type"],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="update_brief",
        toolset="leo-quote",
        schema=UPDATE_BRIEF_SCHEMA,
        handler=_handle_update_brief,
        check_fn=lambda: True,
    )
    registry.register(
        name="update_profile",
        toolset="leo-quote",
        schema=UPDATE_PROFILE_SCHEMA,
        handler=_handle_update_profile,
        check_fn=lambda: True,
    )
    registry.register(
        name="update_quote",
        toolset="leo-quote",
        schema=UPDATE_SCOPE_SCHEMA,
        handler=_handle_update_quote,
        check_fn=lambda: True,
    )
    registry.register(
        name="set_drawer",
        toolset="leo-quote",
        schema=SET_DRAWER_SCHEMA,
        handler=_handle_set_drawer,
        check_fn=_can_show_drawer,
    )
    logger.debug("canvas tools registered (update_brief, update_profile, update_quote, set_drawer)")
