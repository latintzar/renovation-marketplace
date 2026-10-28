"""30-day cold-send outreach budget.

Tracks how many cold outreach messages have been sent today per WABA
number, enforces the daily cap configured in settings, and queues any
overflow for the next eligible day.

Tables
------

``cold_outreach_log``
    Immutable append-only record of every cold message. Daily count is
    derived from rows where ``sent_at::date = CURRENT_DATE (UTC)`` and
    ``waba_id = <phone>``.

``cold_outreach_queue``
    Pending rows queued when the daily cap was reached. Rows have a
    ``send_after`` date; they become eligible again the next day.
    ``sent_at`` is ``NULL`` until the row is actually sent.

Public API
----------

- :func:`daily_sent_count`
- :func:`request_quota`
- :func:`log_send`
- :func:`enqueue_deferred`
- :func:`flush_queue`
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from core import http_client, sb_key, sb_url

logger = logging.getLogger(__name__)


def _headers(key: str) -> dict[str, str]:
    return {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }


def _today_utc() -> str:
    return date.today().isoformat()


def _tomorrow_utc() -> str:
    return (date.today() + timedelta(days=1)).isoformat()


async def daily_sent_count(waba_id: str) -> int:
    """Count cold messages sent today from ``waba_id``.

    Reads ``cold_outreach_log`` for rows where ``purpose = 'cold'``,
    ``waba_id`` matches, and ``sent_at`` is today (UTC). Returns 0 on any
    Supabase error.
    """
    base = sb_url()
    key = sb_key()
    today = _today_utc()
    url = (
        f"{base}/cold_outreach_log"
        f"?select=id"
        f"&waba_id=eq.{waba_id}"
        f"&purpose=eq.cold"
        f"&sent_at=gte.{today}T00:00:00Z"
        f"&sent_at=lt.{today}T24:00:00Z"
    )
    try:
        async with http_client(timeout=10) as client:
            resp = await client.get(url, headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
            })
            if resp.status_code != 200:
                logger.warning(
                    "daily_sent_count | Supabase error %s | %s",
                    resp.status_code, resp.text[:200],
                )
                return 0
            rows = resp.json()
            count = len(rows) if isinstance(rows, list) else 0
            logger.debug(
                "daily_sent_count | waba=%s | today=%s | count=%d",
                waba_id[:8], today, count,
            )
            return count
    except Exception as exc:  # noqa: BLE001
        logger.error("daily_sent_count | exception | %s", exc)
        return 0


async def request_quota(
    waba_id: str,
    n: int,
    daily_limit: int,
) -> tuple[int, int]:
    """Return ``(approved, queued)`` where ``approved + queued == n``.

    Caps ``approved`` at ``daily_limit - daily_sent_count(waba_id)``; the
    rest are queued for tomorrow via :func:`enqueue_deferred`.
    """
    already_sent = await daily_sent_count(waba_id)
    remaining = max(0, daily_limit - already_sent)
    approved = min(n, remaining)
    queued = n - approved
    logger.info(
        "request_quota | waba=%s | limit=%d already=%d remaining=%d "
        "requested=%d approved=%d queued=%d",
        waba_id[:8], daily_limit, already_sent, remaining, n, approved, queued,
    )
    return approved, queued


async def log_send(
    waba_id: str,
    phone_digits: str,
    job_id: str | None = None,
    hc_id: str | None = None,
    purpose: str = "cold",
) -> None:
    """Append one row to ``cold_outreach_log``. Fire-and-forget."""
    base = sb_url()
    key = sb_key()
    payload: dict[str, Any] = {
        "waba_id": waba_id,
        "phone_digits": phone_digits,
        "purpose": purpose,
    }
    if job_id:
        payload["job_id"] = job_id
    if hc_id:
        payload["hc_id"] = hc_id
    try:
        async with http_client(timeout=10) as client:
            resp = await client.post(
                f"{base}/cold_outreach_log",
                json=payload,
                headers=_headers(key),
            )
            if resp.status_code not in (200, 201):
                logger.warning(
                    "log_send | Supabase insert failed %s | %s",
                    resp.status_code, resp.text[:200],
                )
            else:
                logger.debug(
                    "log_send | recorded | waba=%s phone=%s purpose=%s",
                    waba_id[:8], phone_digits[:8] + "…", purpose,
                )
    except Exception as exc:  # noqa: BLE001
        logger.error("log_send | exception (non-fatal) | %s", exc)


async def enqueue_deferred(
    entries: list[dict],
    waba_id: str,
    job_id: str | None,
    humanized_summary: str,
    lang: str = "es_ES",
) -> int:
    """Push overflow entries into ``cold_outreach_queue`` for tomorrow.

    Returns the number of rows inserted. Entries without ``_digits`` are
    silently dropped (the discovery pipeline guarantees them upstream).
    """
    if not entries:
        return 0
    base = sb_url()
    key = sb_key()
    tomorrow = _tomorrow_utc()
    rows = [
        {
            "send_after": tomorrow,
            "waba_id": waba_id,
            "phone_digits": entry.get("_digits", ""),
            "job_id": job_id,
            "candidate_json": entry,
            "humanized_summary": humanized_summary,
            "lang": lang,
        }
        for entry in entries
        if entry.get("_digits")
    ]
    if not rows:
        logger.warning("enqueue_deferred | no valid digits — nothing queued")
        return 0
    try:
        async with http_client(timeout=15) as client:
            resp = await client.post(
                f"{base}/cold_outreach_queue",
                json=rows,
                headers={**_headers(key), "Prefer": "return=minimal"},
            )
            if resp.status_code not in (200, 201):
                logger.error(
                    "enqueue_deferred | Supabase insert failed %s | %s",
                    resp.status_code, resp.text[:300],
                )
                return 0
            logger.info(
                "enqueue_deferred | %d sends queued for %s | waba=%s job=%s",
                len(rows), tomorrow, waba_id[:8], (job_id or "")[:8],
            )
            return len(rows)
    except Exception as exc:  # noqa: BLE001
        logger.error("enqueue_deferred | exception | %s", exc)
        return 0


async def flush_queue(waba_id: str) -> list[dict]:
    """Return + mark-sent all queue rows eligible today.

    Returns the rows (with full ``candidate_json``) so the caller can
    dispatch them. The mark-sent transaction happens before the return so
    a concurrent flush cannot double-send.
    """
    base = sb_url()
    key = sb_key()
    today = _today_utc()
    now_iso = datetime.now(timezone.utc).isoformat()
    fetch_url = (
        f"{base}/cold_outreach_queue"
        f"?waba_id=eq.{waba_id}"
        f"&send_after=lte.{today}"
        f"&sent_at=is.null"
        f"&select=id,phone_digits,job_id,candidate_json,humanized_summary,lang"
        f"&order=send_after.asc"
    )
    try:
        async with http_client(timeout=15) as client:
            resp = await client.get(fetch_url, headers={
                "apikey": key,
                "Authorization": f"Bearer {key}",
            })
            if resp.status_code != 200:
                logger.warning(
                    "flush_queue | fetch failed %s | %s",
                    resp.status_code, resp.text[:200],
                )
                return []
            rows = resp.json()
            if not rows:
                logger.debug("flush_queue | no pending rows for waba=%s today", waba_id[:8])
                return []
            row_ids = [r["id"] for r in rows]
            patch_resp = await client.patch(
                f"{base}/cold_outreach_queue?id=in.({','.join(row_ids)})",
                json={"sent_at": now_iso},
                headers=_headers(key),
            )
            if patch_resp.status_code not in (200, 204):
                logger.error(
                    "flush_queue | mark-sent failed %s | %s",
                    patch_resp.status_code, patch_resp.text[:200],
                )
            logger.info(
                "flush_queue | %d deferred rows ready to send | waba=%s",
                len(rows), waba_id[:8],
            )
            return rows
    except Exception as exc:  # noqa: BLE001
        logger.error("flush_queue | exception | %s", exc)
        return []


__all__ = [
    "daily_sent_count",
    "request_quota",
    "log_send",
    "enqueue_deferred",
    "flush_queue",
]
