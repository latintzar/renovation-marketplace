"""
leo_agent/tools/legal.py — Spanish + EU law tools.

Tools: search_spanish_law, get_boe_norm_text, search_eu_law
"""

from __future__ import annotations

import logging

from ..tool_utils import _record_activity, _run_async, _send_searching_indicator

logger = logging.getLogger(__name__)


# ── Handlers ─────────────────────────────────────────────────────────

def _handle_search_spanish_law(args: dict, **kw) -> str:
    _record_activity("search_spanish_law")
    _send_searching_indicator("search_spanish_law")
    from ..legal_tools import search_boe

    query = str(args.get("query", "")).strip()
    limit = int(args.get("limit", 5))
    if not query:
        return "Please provide a search query."
    result = _run_async(search_boe(query, limit=limit))
    return result


def _handle_get_boe_norm_text(args: dict, **kw) -> str:
    _record_activity("get_boe_norm_text")
    from ..legal_tools import get_boe_norm_text

    norm_id = str(args.get("norm_id", "")).strip()
    if not norm_id:
        return "Please provide a BOE norm identifier."
    result = _run_async(get_boe_norm_text(norm_id))
    return result


def _handle_search_eu_law(args: dict, **kw) -> str:
    _record_activity("search_eu_law")
    _send_searching_indicator("search_eu_law")
    from ..legal_tools import search_eu_law

    query = str(args.get("query", "")).strip()
    doc_type = str(args.get("document_type", "")).strip()
    max_results = int(args.get("max_results", 5))
    if not query:
        return "Please provide a search query."
    result = _run_async(search_eu_law(query, document_type=doc_type, max_results=max_results))
    return result


# ── Schemas ───────────────────────────────────────────────────────────

SEARCH_SPANISH_LAW_SCHEMA = {
    "name": "search_spanish_law",
    "description": (
        "Search Spanish consolidated legislation via the official BOE (Boletín Oficial del Estado) API. "
        "Free, no API key. Use for questions about Spanish building codes, construction regulations, "
        "consumer protection, property law, urban planning (LOE, CTE, LPAC, etc.)."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query in Spanish (e.g. 'código técnico edificación', 'ley propiedad horizontal')",
            },
            "limit": {
                "type": "integer",
                "description": "Max results to return (default 5)",
            },
        },
        "required": ["query"],
    },
}

GET_BOE_NORM_SCHEMA = {
    "name": "get_boe_norm_text",
    "description": (
        "Fetch the full text of a specific Spanish law/norm by its BOE identifier. "
        "Use after search_spanish_law finds a relevant norm and you need the actual text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "norm_id": {
                "type": "string",
                "description": "BOE norm identifier (e.g. 'BOE-A-1999-21567')",
            },
        },
        "required": ["norm_id"],
    },
}

SEARCH_EU_LAW_SCHEMA = {
    "name": "search_eu_law",
    "description": (
        "Search European Union legislation and case law via LexAPI. "
        "Use for EU directives, regulations, and court judgments relevant to construction, "
        "consumer rights, energy efficiency, building products (CPR), or cross-border services."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query (e.g. 'construction products regulation', 'energy performance buildings')",
            },
            "document_type": {
                "type": "string",
                "description": "Optional filter. 'legislation' for directives/regulations, 'judgment' for case law, or omit to search all types.",
                "enum": ["legislation", "judgment", "opinion"],
            },
            "max_results": {
                "type": "integer",
                "description": "Max results (default 5)",
            },
        },
        "required": ["query"],
    },
}


# ── Registration ──────────────────────────────────────────────────────

def register(registry) -> None:
    registry.register(
        name="search_spanish_law",
        toolset="leo-quote",
        schema=SEARCH_SPANISH_LAW_SCHEMA,
        handler=_handle_search_spanish_law,
        check_fn=lambda: True,
    )
    registry.register(
        name="get_boe_norm_text",
        toolset="leo-quote",
        schema=GET_BOE_NORM_SCHEMA,
        handler=_handle_get_boe_norm_text,
        check_fn=lambda: True,
    )
    registry.register(
        name="search_eu_law",
        toolset="leo-quote",
        schema=SEARCH_EU_LAW_SCHEMA,
        handler=_handle_search_eu_law,
        check_fn=lambda: True,
    )
    logger.debug("legal tools registered")
