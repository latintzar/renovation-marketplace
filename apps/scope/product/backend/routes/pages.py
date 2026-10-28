"""
Generated Pages — Ad-hoc branded HTML pages served at /p/<token>
=================================================================

Leo can generate any HTML page (search results, summaries, tables, reports)
and store it here. The agent calls the `create_page` tool, which writes to
Supabase and returns a http://127.0.0.1:18261/p/<token> URL.

No deploy, no Vercel, no rsync — pages are live the moment the tool returns.

Table: generated_pages (token TEXT PK, title TEXT, html_content TEXT,
                         created_at TIMESTAMPTZ, expires_at TIMESTAMPTZ)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from core import sb_url, sb_headers
from core import http_client

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Supabase helpers (same pattern as canvas.py) ──────────────────────────



async def _get_page(token: str) -> Optional[dict[str, Any]]:
    if not sb_url or not sb_key:
        return None
    async with http_client(timeout=10) as client:
        resp = await client.get(
            f"{sb_url()}/generated_pages",
            params={"token": f"eq.{token}", "select": "title,html_content,expires_at", "limit": "1"},
            headers=sb_headers(),
        )
        if resp.status_code == 200:
            rows = resp.json()
            return rows[0] if rows else None
    return None


# ─── 404 page (on-brand) ────────────────────────────────────────────────────

_NOT_FOUND_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Page not found — Leo</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,wght@1,400&family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
  body { margin: 0; background: #FAF8F4; color: #1C1917; font-family: 'Inter', sans-serif;
         display: flex; align-items: center; justify-content: center; min-height: 100vh; }
  .wrap { text-align: center; padding: 2rem; }
  .logo { font-family: 'Source Serif 4', serif; font-style: italic; font-size: 2rem;
          color: #C4602A; margin-bottom: 1.5rem; }
  p { color: #78716C; font-size: 0.95rem; }
</style>
</head>
<body>
<div class="wrap">
  <div class="logo">Leo</div>
  <p>This page doesn't exist or has expired.</p>
</div>
</body>
</html>"""


# ─── Route ──────────────────────────────────────────────────────────────────

@router.get("/p/{token}", response_class=HTMLResponse, include_in_schema=False)
async def serve_generated_page(token: str):
    """Serve a dynamically generated HTML page by token.

    Pages are created by the `create_page` agent tool and stored in Supabase.
    No auth required — anyone with the URL can view the page.
    """
    page = await _get_page(token)
    if not page:
        logger.warning("generated_page not found | token=%s", token)
        return HTMLResponse(content=_NOT_FOUND_HTML, status_code=404)

    # Check expiry
    if page.get("expires_at"):
        from datetime import datetime, timezone
        try:
            expires = datetime.fromisoformat(page["expires_at"].replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > expires:
                logger.info("generated_page expired | token=%s", token)
                return HTMLResponse(content=_NOT_FOUND_HTML, status_code=410)
        except Exception:
            pass

    logger.info("generated_page served | token=%s | title=%s", token, page.get("title", ""))
    return HTMLResponse(content=page["html_content"], status_code=200)
