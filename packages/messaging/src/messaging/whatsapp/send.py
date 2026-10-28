"""Unified WhatsApp send — the ONE function all senders call.

Every code path that sends a WhatsApp message (agent tools, route-level
auto-reply, onboarding, follow-up, founder notifications, cron delivery)
delegates to :func:`send_wa_message`. It owns:

1. 24-hour conversation window check (via :mod:`messaging.whatsapp.session`).
2. Template vs text routing (via :mod:`messaging.whatsapp.templates`).
3. Language detection (``+34`` → ``es``, else ``en_US``).
4. Meta Cloud API call (single ``httpx`` callsite).
5. Optional message storage in ``whatsapp_messages`` (via :mod:`~.storage`).
6. Cold-send budget counter (via :mod:`~.outreach_budget`).
7. Structured return contract (:class:`SendResult`).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, Optional

from core import http_client, run_sync
from messaging.constants import META_API_BASE

from .outreach_budget import log_send as _log_send
from .session import check_24h_window
from .storage import SendResult, store_message
from .templates import detect_language, get_template_name

logger = logging.getLogger(__name__)


def _wa_token() -> str:
    return os.getenv("WHATSAPP_TOKEN", "")


def _wa_phone_id() -> str:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")


_COUNTED_PURPOSES = {"outreach", "followup_1", "followup_final", "general"}


def _record_cold_send(purpose: str, phone_digits: str, job_id: str | None = None) -> None:
    """Fire-and-forget: log a cold send to ``cold_outreach_log``.

    Non-fatal — any exception is swallowed with a warning. Only counted
    purposes (outreach / followup / general) touch the ledger.
    """
    if purpose not in _COUNTED_PURPOSES:
        return
    try:
        asyncio.create_task(
            _log_send(
                waba_id=_wa_phone_id(),
                phone_digits=phone_digits,
                purpose=purpose,
                job_id=job_id,
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("_record_cold_send fire-and-forget failed (non-fatal) | %s", exc)


async def send_wa_message(
    phone: str,
    text: str,
    purpose: str = "general",
    name: str = "",
    template_params: Optional[list[str]] = None,
    do_store: bool = True,
    skip_window_check: bool = False,
) -> SendResult:
    """Send a WhatsApp message — the canonical entry point.

    Args:
        phone: recipient phone (with or without ``+``, spaces, dashes).
        text: message body (plain text for text sends, fallback for
            template sends when the user must see the intended copy).
        purpose: routing key; one of ``general``, ``outreach``,
            ``followup_1``, ``followup_final``, ``referral_pro``,
            ``referral_ho``, ``onboarding``, ``handoff``, ``internal``.
        name: recipient name for template personalisation.
        template_params: override for auto-generated template params.
        do_store: persist the outbound row to ``whatsapp_messages``.
        skip_window_check: skip the 24h window query (for internal /
            founder notifications where we always have an open window).

    Returns:
        :class:`SendResult` — never raises.
    """
    token = _wa_token()
    phone_id = _wa_phone_id()
    if not token or not phone_id:
        return SendResult(ok=False, error="WhatsApp not configured (missing token or phone_id)")

    phone_digits = phone.replace("whatsapp:", "").lstrip("+").replace(" ", "").replace("-", "")
    if not phone_digits or len(phone_digits) < 7:
        return SendResult(ok=False, error=f"Invalid phone number: {phone}")

    window_open = True
    if not skip_window_check and purpose != "internal":
        window_open = await check_24h_window(phone_digits)

    lang = detect_language(phone_digits)
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{META_API_BASE}/{phone_id}/messages"
    store_phone = f"+{phone_digits}"

    try:
        async with http_client(timeout=15) as client:
            if window_open or purpose == "internal":
                has_url = ("http://" in text or "https://" in text)
                text_payload: Dict[str, Any] = {"body": text[:4096]}
                if has_url:
                    text_payload["preview_url"] = True

                resp = await client.post(url, headers=headers, json={
                    "messaging_product": "whatsapp",
                    "to": phone_digits,
                    "type": "text",
                    "text": text_payload,
                })
                data = resp.json()
                if resp.status_code in (200, 201):
                    wa_msg_id = data.get("messages", [{}])[0].get("id", "")
                    if do_store:
                        try:
                            await store_message(
                                phone_number=store_phone,
                                role="assistant",
                                text=text[:4096],
                                wa_message_id=wa_msg_id,
                            )
                        except Exception as store_exc:  # noqa: BLE001
                            logger.warning("store_message failed (non-fatal) | %s", store_exc)
                    logger.info(
                        "send_wa | text | to=%s | purpose=%s | chars=%d | wamid=%s",
                        phone_digits[:8], purpose, len(text), wa_msg_id[:16] if wa_msg_id else "?",
                    )
                    _record_cold_send(purpose, phone_digits)
                    return SendResult(
                        ok=True,
                        method="text",
                        window_was_open=window_open,
                        wa_message_id=wa_msg_id,
                        note="Message delivered",
                    )
                logger.warning(
                    "send_wa | text failed | to=%s | status=%s | body=%s",
                    phone_digits[:8], resp.status_code, str(data)[:300],
                )
                if purpose == "internal":
                    return SendResult(
                        ok=False,
                        method="text",
                        window_was_open=window_open,
                        error=f"Meta API returned {resp.status_code}",
                    )

            template_name = get_template_name(purpose, lang)
            if not template_name:
                return SendResult(
                    ok=False,
                    error=f"No template for purpose={purpose} lang={lang}. Cannot reach cold number.",
                    window_was_open=False,
                )

            params = template_params or [name or "there"]
            tpl_payload = {
                "messaging_product": "whatsapp",
                "to": phone_digits,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {"code": lang},
                    "components": [{
                        "type": "body",
                        "parameters": [{"type": "text", "text": p} for p in params],
                    }],
                },
            }

            resp = await client.post(url, headers=headers, json=tpl_payload)
            data = resp.json()
            if resp.status_code in (200, 201):
                wa_msg_id = data.get("messages", [{}])[0].get("id", "")
                method = "template"
                note = "Template sent."
                if purpose == "general":
                    method = "template_door_opener"
                    note = (
                        "Template sent. The recipient must reply before the full message "
                        "can be delivered. Do NOT retry — tell the user to wait for a reply."
                    )
                if do_store:
                    try:
                        await store_message(
                            phone_number=store_phone,
                            role="assistant",
                            text=f"[Template: {template_name}] {text[:200]}",
                            message_type="template",
                            wa_message_id=wa_msg_id,
                        )
                    except Exception as store_exc:  # noqa: BLE001
                        logger.warning("store_message failed (non-fatal) | %s", store_exc)
                logger.info(
                    "send_wa | template | to=%s | purpose=%s | tpl=%s | wamid=%s",
                    phone_digits[:8], purpose, template_name, wa_msg_id[:16] if wa_msg_id else "?",
                )
                _record_cold_send(purpose, phone_digits)
                return SendResult(
                    ok=True,
                    method=method,
                    window_was_open=False,
                    wa_message_id=wa_msg_id,
                    note=note,
                )
            logger.warning(
                "send_wa | template failed | to=%s | tpl=%s | status=%s | body=%s",
                phone_digits[:8], template_name, resp.status_code, str(data)[:300],
            )
            # Last-ditch: plain text fallback. May silently fail on cold numbers.
            resp = await client.post(url, headers=headers, json={
                "messaging_product": "whatsapp",
                "to": phone_digits,
                "type": "text",
                "text": {"body": text[:4096]},
            })
            data = resp.json()
            if resp.status_code in (200, 201):
                wa_msg_id = data.get("messages", [{}])[0].get("id", "")
                if do_store:
                    try:
                        await store_message(
                            phone_number=store_phone,
                            role="assistant",
                            text=text[:4096],
                            wa_message_id=wa_msg_id,
                        )
                    except Exception as store_exc:  # noqa: BLE001
                        logger.warning("store_message failed (non-fatal) | %s", store_exc)
                logger.info(
                    "send_wa | text fallback | to=%s | purpose=%s | wamid=%s",
                    phone_digits[:8], purpose, wa_msg_id[:16] if wa_msg_id else "?",
                )
                _record_cold_send(purpose, phone_digits)
                return SendResult(
                    ok=True,
                    method="text",
                    window_was_open=False,
                    wa_message_id=wa_msg_id,
                    note="Sent as plain text (template failed). May not deliver to cold numbers.",
                )
            return SendResult(
                ok=False,
                error=f"Both template ({template_name}) and text fallback failed.",
                window_was_open=False,
            )

    except Exception as exc:  # noqa: BLE001
        logger.error("send_wa | exception | to=%s | purpose=%s | %s", phone_digits[:8], purpose, exc)
        return SendResult(ok=False, error=str(exc))


def send_wa_message_sync(
    phone: str,
    text: str,
    purpose: str = "general",
    name: str = "",
    template_params: Optional[list[str]] = None,
    do_store: bool = True,
    skip_window_check: bool = False,
) -> SendResult:
    """Sync wrapper for hermes tool handlers running in a thread executor.

    Delegates to :func:`core.run_sync` with a 30s timeout.
    """
    return run_sync(
        send_wa_message(phone, text, purpose, name, template_params, do_store, skip_window_check),
        timeout=30,
    )


__all__ = ["send_wa_message", "send_wa_message_sync"]
