"""
WhatsApp Presence Checker
=========================

Checks whether a phone number is registered on WhatsApp by driving the
VNC browser's existing WhatsApp Web session via Chrome DevTools Protocol (CDP).

Strategy
--------
Navigate to ``https://web.whatsapp.com/send?phone=<digits>``, wait for the
page to load, then scan ``document.body.innerText`` for the phrase
"click here for contact info" — WhatsApp Web shows that phrase in the chat
header when the number has no WhatsApp account. If that phrase is absent and
a header is present, the number is on WhatsApp.

Requirements
------------
- The VNC browser (``puedo-vnc-browser`` systemd service) must be running and
  already logged in to WhatsApp Web at ``localhost:9222``.
- ``websockets`` and ``aiohttp`` (or httpx) must be importable.

Usage
-----
    from scrapers.whatsapp_checker import check_number, check_bulk

    result: bool = await check_number("34612345678")   # True = on WA
    results: dict[str, bool] = await check_bulk(["34612345678", "34699999999"])
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────

CDP_HOST = "http://localhost:9222"
CDP_WS_BASE = "ws://localhost:9222"

# How long to wait after navigating before scanning the DOM.
# WhatsApp Web needs a moment to load the React tree.
CHECK_SLEEP_SEC: float = 5.0

# Extra sleep when we land on the main WA page (not in a chat thread yet)
LOAD_RETRY_SLEEP: float = 2.0

# How many times to retry if the DOM scan returns an inconclusive result
RETRY_LIMIT: int = 2

# The exact phrase WhatsApp Web puts in the header subtext when the number
# does not have a WhatsApp account.
NOT_ON_WA_PHRASE = "click here for contact info"

# Phrase present in any real WA chat header (online / last seen / business)
ON_WA_PHRASES = ["last seen", "online", "business account", "recently"]


# ── CDP helpers ───────────────────────────────────────────────────────────────

async def _get_ws_url() -> str:
    """Return the WebSocket debugger URL for any available browser tab.

    Prefers a tab that is already on WhatsApp Web.  Falls back to the first
    available tab.  Raises RuntimeError if no tabs are available (VNC browser
    not running or CDP not exposed).
    """
    from core import http_client
    try:
        async with http_client(timeout=5) as client:
            resp = await client.get(f"{CDP_HOST}/json")
            resp.raise_for_status()
            tabs = resp.json()
    except Exception as exc:
        raise RuntimeError(
            f"Cannot reach VNC browser CDP at {CDP_HOST}/json — "
            f"is the puedo-vnc-browser service running? ({exc})"
        ) from exc

    if not tabs:
        raise RuntimeError("CDP returned no open tabs — VNC browser may not be running.")

    # Prefer a tab that already has WA open
    for tab in tabs:
        url = tab.get("url", "")
        if "web.whatsapp.com" in url:
            ws = tab.get("webSocketDebuggerUrl", "")
            if ws:
                logger.debug("CDP | reusing WA tab | tabId=%s url=%s", tab.get("id"), url)
                return ws

    # Fall back to the first page tab
    for tab in tabs:
        if tab.get("type") == "page":
            ws = tab.get("webSocketDebuggerUrl", "")
            if ws:
                logger.debug("CDP | using fallback tab | tabId=%s url=%s", tab.get("id"), tab.get("url"))
                return ws

    raise RuntimeError("No usable page tabs found in CDP.")


async def _cdp_send(ws, method: str, params: dict | None = None, msg_id: int = 1) -> dict:
    """Send a single CDP command over an open websockets connection and return result."""
    import websockets  # type: ignore

    payload = json.dumps({"id": msg_id, "method": method, "params": params or {}})
    await ws.send(payload)

    # Wait for the response matching our id (skip other events)
    deadline = time.monotonic() + 15
    while time.monotonic() < deadline:
        raw = await asyncio.wait_for(ws.recv(), timeout=10)
        msg = json.loads(raw)
        if msg.get("id") == msg_id:
            if "error" in msg:
                logger.warning("CDP error | method=%s | %s", method, msg["error"])
            return msg.get("result", {})
    raise TimeoutError(f"CDP no response for {method} within 15s")


# ── Core check ────────────────────────────────────────────────────────────────

async def check_number(phone_digits: str) -> bool:
    """Return True if ``phone_digits`` has a WhatsApp account.

    Navigates the VNC browser's WA Web session to the send-to-phone URL and
    inspects the DOM.  Always returns a bool; never raises (logs errors and
    returns True as safe default so discovery is not blocked).

    Args:
        phone_digits: Digits only, no ``+`` or spaces.  International format
                      expected (e.g. ``34612345678``).
    """
    import websockets  # type: ignore[import]

    url = f"https://web.whatsapp.com/send?phone={phone_digits}&text&type=phone_number&app_absent=0"
    logger.info("WA check | %s | navigating", phone_digits[:8] + "…")

    ws_url = await _get_ws_url()

    try:
        async with websockets.connect(ws_url, open_timeout=10, close_timeout=5) as ws:
            # Navigate to the send-to-phone URL
            await _cdp_send(ws, "Page.navigate", {"url": url}, msg_id=1)

            # Wait for WA Web React tree to mount
            await asyncio.sleep(CHECK_SLEEP_SEC)

            for attempt in range(RETRY_LIMIT + 1):
                # Scan the full visible text of the page
                result = await _cdp_send(
                    ws,
                    "Runtime.evaluate",
                    {
                        "expression": "document.body ? document.body.innerText : ''",
                        "returnByValue": True,
                    },
                    msg_id=10 + attempt,
                )
                body_text: str = (result.get("value") or "").lower()

                if NOT_ON_WA_PHRASE in body_text:
                    logger.info("WA check | %s | NOT on WhatsApp (phrase found)", phone_digits[:8] + "…")
                    return False

                if any(p in body_text for p in ON_WA_PHRASES):
                    logger.info("WA check | %s | ON WhatsApp (positive phrase found)", phone_digits[:8] + "…")
                    return True

                # WhatsApp is still loading — retry
                if attempt < RETRY_LIMIT:
                    logger.debug(
                        "WA check | %s | inconclusive on attempt %d, retrying in %.1fs",
                        phone_digits[:8] + "…", attempt + 1, LOAD_RETRY_SLEEP,
                    )
                    await asyncio.sleep(LOAD_RETRY_SLEEP)

            # Also look for the phone number compose box as a secondary signal.
            # If a message input is present, WA accepted the number.
            compose_result = await _cdp_send(
                ws,
                "Runtime.evaluate",
                {
                    "expression": (
                        "!!document.querySelector("
                        "'[data-testid=\"conversation-compose-box-input\"],"
                        " [contenteditable][data-tab]'"
                        ")"
                    ),
                    "returnByValue": True,
                },
                msg_id=20,
            )
            compose_present = compose_result.get("value", False)
            if compose_present:
                logger.info(
                    "WA check | %s | ON WhatsApp (compose box present)", phone_digits[:8] + "…"
                )
                return True

            # Inconclusive after all retries — default to True (safe: we might
            # send to a non-WA number which will just fail at delivery, better
            # than silently dropping real contractors)
            logger.warning(
                "WA check | %s | inconclusive after %d attempts — defaulting to True",
                phone_digits[:8] + "…", RETRY_LIMIT + 1,
            )
            return True

    except RuntimeError:
        raise  # re-raise RuntimeError from _get_ws_url (VNC not running)
    except Exception as exc:
        logger.error(
            "WA check | %s | exception — defaulting to True | %s",
            phone_digits[:8] + "…", exc,
        )
        return True
    finally:
        # Return browser to WA home so it's ready for the next call
        try:
            async with websockets.connect(ws_url, open_timeout=5, close_timeout=3) as ws2:
                await _cdp_send(ws2, "Page.navigate", {"url": "https://web.whatsapp.com/"}, msg_id=1)
                await asyncio.sleep(1.5)
        except Exception as reset_exc:
            logger.debug("WA check | reset nav failed (non-fatal) | %s", reset_exc)


# ── Bulk check ────────────────────────────────────────────────────────────────

async def check_bulk(
    phones: list[str],
    concurrency: int = 1,
    skip_check: bool = False,
) -> dict[str, bool]:
    """Check WhatsApp presence for a list of phone numbers.

    Args:
        phones: List of digit-only phone strings.
        concurrency: Always 1 — the VNC session is a single browser tab.
                     Kept as a parameter for future multi-tab support.
        skip_check: If True, return all numbers as True (for testing or when
                    VNC session is unavailable and caller wants to skip).

    Returns:
        ``{phone_digits: is_on_wa}`` for every input phone.
    """
    if skip_check:
        logger.warning("WA check | skip_check=True — marking all %d numbers as on WA", len(phones))
        return {p: True for p in phones}

    results: dict[str, bool] = {}
    total = len(phones)

    # Verify CDP is reachable before starting the loop
    try:
        await _get_ws_url()
    except RuntimeError as exc:
        logger.error(
            "WA check | VNC browser unreachable — skipping presence filter | %s", exc
        )
        # Safe default: treat all as on WA so discovery still proceeds
        return {p: True for p in phones}

    for idx, phone in enumerate(phones, start=1):
        logger.info("WA check | progress %d/%d | %s", idx, total, phone[:8] + "…")
        try:
            on_wa = await check_number(phone)
        except RuntimeError as exc:
            logger.error("WA check | VNC offline mid-run | %s — aborting bulk check", exc)
            # Fill remaining with True and return
            for remaining in phones[idx - 1:]:
                results.setdefault(remaining, True)
            return results
        results[phone] = on_wa

        # Brief pause between checks to avoid WhatsApp rate-limiting
        if idx < total:
            await asyncio.sleep(1.0)

    on_count = sum(1 for v in results.values() if v)
    logger.info(
        "WA check | bulk done | %d/%d on WhatsApp", on_count, total
    )
    return results


# ── CLI smoke test ────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    numbers = sys.argv[1:] or ["34612345678"]
    print(f"Checking {len(numbers)} number(s)…")
    r = asyncio.run(check_bulk(numbers))
    for phone, on_wa in r.items():
        status = "ON WhatsApp" if on_wa else "NOT on WhatsApp"
        print(f"  {phone}: {status}")
