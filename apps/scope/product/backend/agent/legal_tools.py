"""
BOE (Spanish legislation) and LexAPI (EU law) tools for Hermes.

Registers `search_spanish_law` and `search_eu_law` into the leo-quote toolset.
Both are free APIs — no keys needed for BOE, LexAPI free tier = 50 calls/day.
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, Dict

from core import http_client

logger = logging.getLogger(__name__)

BOE_BASE = "https://boe.es/datosabiertos/api"
LEXAPI_BASE = "https://lex-api.com/api/v1"


# ── BOE: Spanish consolidated legislation ────────────────────────────

async def search_boe(query: str, limit: int = 5) -> str:
    """Search the BOE consolidated legislation API (free, no auth).
    
    The BOE query parameter is a JSON object with structure:
    {"query":{"query_string":{"query":"titulo:keyword OR texto:keyword"}}}
    """
    import urllib.parse

    words = query.strip().split()
    if len(words) > 1:
        boe_query = " AND ".join(f"texto:{w}" for w in words)
    else:
        boe_query = f"texto:{query.strip()}"

    query_json = json.dumps({
        "query": {
            "query_string": {"query": boe_query},
        }
    })

    try:
        url = f"{BOE_BASE}/legislacion-consolidada?query={urllib.parse.quote(query_json)}&limit={limit}"
        async with http_client(timeout=15) as client:
            resp = await client.get(
                url,
                headers={"Accept": "application/json"},
            )
            if resp.status_code != 200:
                logger.warning("BOE search failed | status=%d | query=%s", resp.status_code, query)
                return f"BOE API returned status {resp.status_code}"

            data = resp.json()
            items = data.get("data", [])
            if isinstance(items, dict) and not items:
                return "No results found in BOE for that query."
            if not items:
                return "No results found in BOE for that query."

            results = []
            for item in (items if isinstance(items, list) else [items])[:limit]:
                title = item.get("titulo", "")
                norm_id = item.get("identificador", "")
                dept = item.get("departamento", {})
                dept_text = dept.get("texto", "") if isinstance(dept, dict) else str(dept)
                date = item.get("fecha_publicacion", "")
                url_html = item.get("url_html_consolidada", "")
                rango = item.get("rango", {})
                rango_text = rango.get("texto", "") if isinstance(rango, dict) else str(rango)
                results.append(
                    f"- **{title}**\n  {rango_text} | {dept_text} | Published: {date}\n  ID: {norm_id}\n  URL: {url_html}"
                )
            return "\n".join(results)

    except Exception as exc:
        logger.error("BOE search error | %s", exc, exc_info=True)
        return f"BOE search error: {exc}"


async def get_boe_norm_text(norm_id: str) -> str:
    """Fetch the full text of a specific BOE norm by identifier."""
    try:
        async with http_client(timeout=20) as client:
            resp = await client.get(
                f"{BOE_BASE}/legislacion-consolidada/id/{norm_id}/texto",
                headers={"Accept": "application/xml"},
            )
            if resp.status_code != 200:
                return f"BOE norm {norm_id}: status {resp.status_code}"

            root = ET.fromstring(resp.text)
            texts = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    texts.append(elem.text.strip())
            full = "\n".join(texts)
            if len(full) > 8000:
                full = full[:8000] + "\n... (truncated)"
            return full or "No text content found for this norm."

    except Exception as exc:
        logger.error("BOE norm text error | %s", exc)
        return f"BOE fetch error: {exc}"


# ── LexAPI: EU legislation ───────────────────────────────────────────

_LEXAPI_KEY = ""


def _get_lexapi_key() -> str:
    """Load LexAPI key from env."""
    global _LEXAPI_KEY
    if not _LEXAPI_KEY:
        import os
        _LEXAPI_KEY = os.getenv("LEXAPI_KEY", "")
    return _LEXAPI_KEY


async def search_eu_law(
    query: str,
    document_type: str = "",
    domain: str = "EU_LAW",
    max_results: int = 5,
) -> str:
    """Search EU law via LexAPI (free tier: 50 calls/day).
    
    document_type can be 'legislation', 'judgment', or '' (all types).
    """
    api_key = _get_lexapi_key()
    if not api_key:
        return (
            "LexAPI key not configured. Set LEXAPI_KEY in .env.local to enable EU law search. "
            "Sign up free at https://lex-api.com"
        )

    try:
        body: dict[str, Any] = {"query": query, "domain": domain, "maxPages": 1}
        if document_type:
            body["documentType"] = document_type

        async with http_client(timeout=15) as client:
            resp = await client.post(
                f"{LEXAPI_BASE}/search",
                headers={
                    "x-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json=body,
            )
            if resp.status_code != 200:
                logger.warning("LexAPI search failed | status=%d | query=%s", resp.status_code, query)
                return f"LexAPI returned status {resp.status_code}"

            data = resp.json()
            items = data.get("results", [])[:max_results]
            if not items:
                return "No EU law results found."

            results = []
            for item in items:
                title = item.get("title", "")
                celex = item.get("celexNumber", "")
                form = item.get("form", "")
                date = item.get("dateOfDocument", "")
                links = item.get("documentLinks", {})
                html_link = links.get("html", "")
                results.append(
                    f"- **{title}**\n  {form} | CELEX: {celex} | Date: {date}\n  {html_link}"
                )
            return f"Found {data.get('totalResults', '?')} results.\n\n" + "\n".join(results)

    except Exception as exc:
        logger.error("LexAPI search error | %s", exc)
        return f"LexAPI error: {exc}"
