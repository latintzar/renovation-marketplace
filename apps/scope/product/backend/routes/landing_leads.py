"""
Landing Page Lead Capture
=========================

POST /api/leads/submit  -- text or audio job description
POST /api/leads/phone   -- add phone number to an existing lead

Saves to Supabase `landing_leads` table. Audio: transcribed via ``packages/voice``
(Groq Whisper → HF → local faster-whisper fallback chain), then optional
**Bedrock** polish (``voice.polish_sync``) runs in a background task so the
HTTP response stays fast.
"""

import asyncio
import logging
import os
import time
import uuid
from pathlib import Path

import httpx
from core import http_client
from fastapi import APIRouter, UploadFile, File, Form, BackgroundTasks, Request
from fastapi.responses import JSONResponse

from config import settings
from voice import polish_sync, transcribe

logger = logging.getLogger(__name__)
router = APIRouter()

UPLOAD_DIR = Path("/root/leo/apps/scope/product/backend/uploads/leads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

PHOTO_DIR = Path("/root/leo/apps/scope/product/backend/uploads/lead-photos")
PHOTO_DIR.mkdir(parents=True, exist_ok=True)


async def _supabase_insert(table: str, data: dict) -> dict:
    """Insert a row via Supabase REST API."""
    import httpx
    from config import settings

    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    url = f"{settings.SUPABASE_URL}/rest/v1/{table}"
    async with http_client(timeout=15) as client:
        resp = await client.post(url, json=data, headers=headers)
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else data


def _normalize_phone_e164(phone: str, require_spanish: bool = True) -> str:
    """Parse and normalise a phone number to E.164.

    Returns the E.164 string on success, empty string on failure.
    When ``require_spanish`` is True (default) only numbers that belong to
    Spain (+34) or that are entered without a country code but are valid
    Spanish mobile/landline formats are accepted.

    Spanish mobile numbers start with 6xx or 7xx (9 digits total).
    Spanish landlines start with 8xx or 9xx (9 digits total).
    We allow both because some homeowners enter a landline for the first contact.
    """
    from core import to_e164
    return to_e164(phone, require_region="ES" if require_spanish else None)


async def _supabase_get_landing_lead(lead_id: str) -> dict | None:
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.SUPABASE_URL}/rest/v1/landing_leads?id=eq.{lead_id}&select=id,job_description,transcript,location"
    async with http_client(timeout=15) as client:
        resp = await client.get(url, headers=headers)
        if resp.status_code != 200:
            return None
        rows = resp.json()
        return rows[0] if rows else None


async def _insert_cs_lead_onboarding(
    *,
    whatsapp: str,
    audience: str,
    name: str,
    location: str,
    chat_summary: str,
    source: str,
) -> None:
    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=minimal",
    }
    row = {
        "whatsapp": whatsapp,
        "audience": audience if audience in ("homeowner", "professional", "agent") else "homeowner",
        "source": source,
        "chat_summary": (chat_summary or "")[:4000] or None,
        "location": location.strip() or None,
        "name": name.strip() or None,
    }
    url = f"{settings.SUPABASE_URL}/rest/v1/cs_leads"
    async with http_client(timeout=15) as client:
        resp = await client.post(url, json=row, headers=headers)
        if resp.status_code not in (200, 201):
            logger.warning(
                "cs_leads insert from landing phone | status=%s | body=%s",
                resp.status_code,
                resp.text[:300],
            )
        else:
            logger.info(
                "cs_leads row created | audience=%s | wa=%s***",
                row["audience"],
                whatsapp[-4:] if len(whatsapp) > 4 else "",
            )


async def _supabase_update(table: str, row_id: str, data: dict) -> dict:
    """Update a row via Supabase REST API."""
    import httpx
    from config import settings

    key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
    headers = {
        "apikey": key,
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }
    url = f"{settings.SUPABASE_URL}/rest/v1/{table}?id=eq.{row_id}"
    async with http_client(timeout=15) as client:
        resp = await client.patch(url, json=data, headers=headers)
        resp.raise_for_status()
        rows = resp.json()
        return rows[0] if rows else data


async def _transcribe_audio(audio_bytes: bytes, content_type: str) -> str:
    """Transcribe audio via ``packages/voice``.

    Polish is deliberately skipped here (``polish=False``); the caller
    schedules :func:`_polish_and_update` as a background task so the HTTP
    response returns as soon as the raw transcript is saved.
    """
    try:
        result = await transcribe(
            audio_bytes,
            content_type=content_type,
            provider="auto",
            polish=False,
        )
        logger.info(
            "Lead audio transcribed via %s | lang=%s | %d chars | %.1fs",
            result.provider,
            result.lang or "?",
            len(result.text),
            result.asr_seconds,
        )
        return result.text
    except ValueError as e:
        logger.error("No cloud STT provider available: %s", e)
        return ""
    except Exception as e:
        logger.error("Cloud STT failed: %s", e, exc_info=True)
        return ""


def _polish_and_update(lead_id: str, raw_text: str):
    """Background: polish transcript with LLM and update the DB row."""
    try:
        polished = polish_sync(raw_text)
        if polished and polished != raw_text:
            import httpx
            from config import settings
            key = settings.SUPABASE_SERVICE_ROLE_KEY or settings.SUPABASE_ANON_KEY
            headers = {
                "apikey": key,
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
                "Prefer": "return=minimal",
            }
            url = f"{settings.SUPABASE_URL}/rest/v1/landing_leads?id=eq.{lead_id}"
            resp = httpx.patch(url, json={"transcript": polished}, headers=headers, timeout=15)
            resp.raise_for_status()
            logger.info("Lead polish updated | id=%s | %d→%d chars", lead_id, len(raw_text), len(polished))
    except Exception as e:
        logger.warning("Background polish failed for lead %s: %s", lead_id, e)


@router.post("/api/leads/submit")
async def submit_lead(
    background_tasks: BackgroundTasks,
    job_text: str = Form(default=""),
    audio: UploadFile = File(default=None),
    transcript_polished: str = Form(
        default="",
        description="If true/1, job_text was already LLM-polished client-side — skip background polish.",
    ),
):
    lead_id = str(uuid.uuid4())
    audio_url = None
    transcript = None

    if audio and audio.size and audio.size > 0:
        content = await audio.read()
        if content:
            ext = "webm"
            ct = audio.content_type or ""
            if "ogg" in ct:
                ext = "ogg"
            elif "mp4" in ct or "m4a" in ct:
                ext = "m4a"
            elif "wav" in ct:
                ext = "wav"

            filename = f"{lead_id}.{ext}"
            filepath = UPLOAD_DIR / filename
            filepath.write_bytes(content)
            audio_url = f"/uploads/leads/{filename}"
            logger.info("Saved lead audio | %s | %d bytes", filename, len(content))

            if job_text:
                transcript = job_text
            else:
                try:
                    transcript = await _transcribe_audio(content, ct)
                except Exception as e:
                    logger.error("Lead transcription failed: %s", e, exc_info=True)
    elif not job_text:
        return JSONResponse({"error": "No job description or audio provided"}, status_code=400)

    try:
        row = await _supabase_insert("landing_leads", {
            "id": lead_id,
            "job_description": job_text or None,
            "audio_url": audio_url,
            "transcript": transcript,
        })
        logger.info("Lead created | id=%s | text=%s | audio=%s",
                     lead_id, bool(job_text), bool(audio_url))
        raw = transcript or job_text
        skip_bg = (transcript_polished or "").strip().lower() in ("1", "true", "yes", "on")
        if raw and not skip_bg:
            background_tasks.add_task(_polish_and_update, lead_id, raw)
        return JSONResponse({"id": lead_id, "ok": True, "transcript": transcript})
    except Exception as e:
        logger.error("Failed to save lead: %s", e, exc_info=True)
        return JSONResponse({"error": "Failed to save"}, status_code=500)


@router.post("/api/leads/phone")
async def add_phone(
    request: Request,
    lead_id: str = Form(default=""),
    phone: str = Form(default=""),
    audience: str = Form(default="homeowner"),
    display_name: str = Form(default=""),
    locale: str = Form(default="en"),
    location: str = Form(
        default="",
        description="Location passed directly from location gate when no lead row exists yet.",
    ),
    job_description: str = Form(
        default="",
        description="Job text passed directly from location gate when no lead row exists yet.",
    ),
    chat_summary_extra: str = Form(
        default="",
        description="Optional summary when lead_id is empty (e.g. imported profile note).",
    ),
    user_id: str = Form(
        default="",
        description="Session/mem0 ID from the React app — used to migrate anonymous memories to phone.",
    ),
):
    # Accept both Form and JSON body
    content_type = request.headers.get("content-type", "")
    if "application/json" in content_type:
        try:
            body = await request.json()
        except Exception:
            return JSONResponse({"error": "invalid json"}, status_code=400)
        phone = body.get("phone", phone) or ""
        lead_id = body.get("lead_id", lead_id) or ""
        audience = body.get("audience", audience) or "homeowner"
        display_name = body.get("display_name", display_name) or ""
        locale = body.get("locale", locale) or "en"
        location = body.get("location", location) or ""
        job_description = body.get("job_description", job_description) or ""
        chat_summary_extra = body.get("chat_summary_extra", chat_summary_extra) or ""
        user_id = body.get("user_id", user_id) or ""
        contractor_id = body.get("contractor_id", "") or ""
    else:
        contractor_id = ""

    if not phone:
        return JSONResponse({"error": "Missing phone"}, status_code=400)

    wa = _normalize_phone_e164(phone, require_spanish=False)
    if not wa:
        return JSONResponse(
            {"error": "Please enter a valid WhatsApp number with country code"},
            status_code=400,
        )

    aud = (audience or "homeowner").strip().lower()
    if aud not in ("homeowner", "professional", "agent"):
        aud = "homeowner"

    try:
        lead_id = (lead_id or "").strip()
        if lead_id:
            await _supabase_update("landing_leads", lead_id, {"phone": wa})
            logger.info("Phone added to lead | id=%s | phone=%s | audience=%s", lead_id, wa[:6] + "***", aud)

        landing = await _supabase_get_landing_lead(lead_id) if lead_id else None
        loc = ""
        summary_bits = []
        if landing:
            loc = (landing.get("location") or "").strip()
            jd = (landing.get("job_description") or "").strip()
            tr = (landing.get("transcript") or "").strip()
            if jd:
                summary_bits.append(jd)
            elif tr:
                summary_bits.append(tr)
        # Fall back to directly-posted params (location gate path — no lead row)
        if not loc:
            loc = (location or "").strip()
        if not summary_bits:
            jd_direct = (job_description or "").strip()
            if jd_direct:
                summary_bits.append(jd_direct)
        extra = (chat_summary_extra or "").strip()
        if extra:
            summary_bits.append(extra)
        if lead_id and not summary_bits:
            chat_summary = f"Landing lead {lead_id} confirmed phone on site."
        elif summary_bits:
            chat_summary = " ".join(summary_bits)[:2000]
        else:
            chat_summary = "Onboarding: phone submitted from leo.casa (no landing_leads row)."
        display = (display_name or "").strip()
        loc_suffix = loc if loc else ""

        src = f"landing_leads:{lead_id}" if lead_id else "onboarding:direct"

        await _insert_cs_lead_onboarding(
            whatsapp=wa,
            audience=aud,
            name=display,
            location=loc,
            chat_summary=chat_summary,
            source=src,
        )

        # Migrate mem0 memories from the anonymous session ID to the phone number
        # so the WhatsApp auto-reply agent has continuity with the web chat session
        uid_to_migrate = (user_id or lead_id or "").strip()
        if uid_to_migrate and uid_to_migrate != wa:
            try:
                from storage import migrate_user as update_user_id, is_mem0_configured as _mem0_key
                if _mem0_key():
                    asyncio.create_task(update_user_id(uid_to_migrate, wa))
                    logger.info("mem0 migration queued | from=%s | to=%s", uid_to_migrate[:8] + "***", wa[:8] + "***")
            except Exception as exc:
                logger.warning("mem0 migration failed (non-fatal) | %s", exc)

        # Link phone to contractor dossier if contractor_id provided
        if contractor_id:
            try:
                from records.dossier import set_phone as dossier_set_phone
                await dossier_set_phone(contractor_id, wa)
                logger.info("Dossier phone linked | contractor=%s phone=%s", contractor_id, wa[:8] + "***")
            except Exception as exc:
                logger.warning("Dossier set_phone failed (non-fatal) | %s", exc)

        # Notify Peter the instant a homeowner confirms their phone — "successful submission" moment.
        # Only fires for homeowners (not tradespeople). Fire-and-forget via asyncio.create_task.
        if aud == "homeowner":
            try:
                from agent import notify_peter_lead_submitted
                asyncio.create_task(notify_peter_lead_submitted(
                    phone=wa,
                    name=display,
                    location=loc,
                    job_text=chat_summary[:400] if chat_summary else "",
                ))
            except Exception as exc:
                logger.warning("Peter lead notification setup failed (non-fatal) | %s", exc)

        try:
            from routes.meta_whatsapp import send_onboarding_wa_message

            wa_aud = "professional" if aud == "professional" else "homeowner"
            ok = await send_onboarding_wa_message(
                phone=wa,
                audience=wa_aud,
                display_name=display,
                locale=(locale or "en")[:12],
                location_suffix=loc_suffix,
            )
            if not ok:
                logger.warning("Onboarding WhatsApp send returned False | lead_id=%s", lead_id)
        except Exception as exc:
            logger.error("Onboarding WhatsApp send failed (non-fatal) | %s", exc, exc_info=True)

        # Auto-kickoff discovery when we have enough info from the hero form
        # (location + job description). Creates a job and fires contractor_discovery
        # in background so Peter gets notified as soon as contractors are found.
        jd_text = (job_description or "").strip()
        if aud == "homeowner" and loc and jd_text:
            try:
                from routes.job_inbox import create_job
                from workflows.contractor_discovery import run_contractor_discovery

                brief = {
                    "title": jd_text[:120],
                    "trade": jd_text[:120],
                    "description": jd_text,
                    "location": loc,
                }
                job_row = await create_job(
                    brief=brief,
                    homeowner_phone=wa,
                )
                new_job_id = job_row.get("id", "")
                if new_job_id:
                    logger.info(
                        "Auto-discovery triggered from hero form | job=%s location=%s",
                        new_job_id[:8], loc,
                    )
                    asyncio.create_task(run_contractor_discovery(new_job_id))
            except Exception as exc:
                logger.warning("Auto-discovery kickoff failed (non-fatal) | %s", exc, exc_info=True)

        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error("Failed to save phone: %s", e, exc_info=True)
        return JSONResponse({"error": "Failed to save phone"}, status_code=500)


@router.post("/api/leads/photos")
async def upload_photos(
    lead_id: str = Form(...),
    photos: list[UploadFile] = File(...),
):
    """Upload one or more photos for a lead. Saves locally, stores URLs in Supabase."""
    if not lead_id:
        return JSONResponse({"error": "Missing lead_id"}, status_code=400)
    if not photos:
        return JSONResponse({"error": "No photos provided"}, status_code=400)

    saved_urls = []
    lead_photo_dir = PHOTO_DIR / lead_id
    lead_photo_dir.mkdir(parents=True, exist_ok=True)

    for i, photo in enumerate(photos[:10]):
        content = await photo.read()
        if not content:
            continue
        ext = "jpg"
        ct = (photo.content_type or "").lower()
        if "png" in ct:
            ext = "png"
        elif "webp" in ct:
            ext = "webp"
        elif "heic" in ct or "heif" in ct:
            ext = "heic"

        filename = f"{i:02d}.{ext}"
        filepath = lead_photo_dir / filename
        filepath.write_bytes(content)
        rel_url = f"/uploads/lead-photos/{lead_id}/{filename}"
        saved_urls.append(rel_url)
        logger.info("Saved lead photo | lead=%s | file=%s | %d bytes", lead_id, filename, len(content))

    if saved_urls:
        try:
            await _supabase_update("landing_leads", lead_id, {"photo_urls": saved_urls})
            logger.info("Updated lead photo_urls | id=%s | count=%d", lead_id, len(saved_urls))
        except Exception as e:
            logger.error("Failed to update photo_urls for lead %s: %s", lead_id, e, exc_info=True)

    return JSONResponse({"ok": True, "urls": saved_urls, "count": len(saved_urls)})


@router.post("/api/leads/update")
async def update_lead(
    lead_id: str = Form(...),
    location: str = Form(default=""),
    chat_history: str = Form(default=""),
    job_description: str = Form(default=""),
):
    """Update a lead with location, chat history, or refined job description."""
    if not lead_id:
        return JSONResponse({"error": "Missing lead_id"}, status_code=400)

    import json as jsonmod
    data = {}
    if location:
        data["location"] = location
    if chat_history:
        try:
            data["chat_history"] = jsonmod.loads(chat_history)
        except Exception:
            data["chat_history"] = [{"text": chat_history}]
    if job_description:
        data["job_description"] = job_description

    if not data:
        return JSONResponse({"error": "Nothing to update"}, status_code=400)

    try:
        await _supabase_update("landing_leads", lead_id, data)
        logger.info("Lead updated | id=%s | fields=%s", lead_id, list(data.keys()))
        return JSONResponse({"ok": True})
    except Exception as e:
        logger.error("Failed to update lead %s: %s", lead_id, e, exc_info=True)
        return JSONResponse({"error": "Failed to update"}, status_code=500)


@router.post("/api/leads/check-wa")
async def check_whatsapp(request: Request):
    """Check whether a phone number is registered on WhatsApp.

    Uses the VNC browser's WhatsApp Web session (CDP). Fast-fails with
    ``{"on_wa": true, "checked": false}`` if the VNC browser is unreachable so
    the caller can still proceed.

    Body (JSON): ``{"phone": "+34612345678"}``
    Response: ``{"on_wa": bool, "checked": bool, "phone": str}``
    """
    try:
        body = await request.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    phone = (body.get("phone") or "").strip()
    if not phone:
        return JSONResponse({"error": "Missing phone"}, status_code=400)

    # Normalise to E.164 (accept any country, no Spanish restriction)
    wa = _normalize_phone_e164(phone, require_spanish=False)
    if not wa:
        return JSONResponse(
            {"error": "Please enter a valid phone number with country code"},
            status_code=400,
        )

    # Strip the leading + for the checker (it expects digits only)
    digits = wa.lstrip("+")

    try:
        from scrapers.whatsapp_checker import check_number
        on_wa = await check_number(digits)
        logger.info("WA check via endpoint | phone=%s | on_wa=%s", digits[:8] + "…", on_wa)
        return JSONResponse({"on_wa": on_wa, "checked": True, "phone": wa})
    except RuntimeError as exc:
        # VNC browser unreachable — let the caller through (don't block submission)
        logger.warning("WA check | VNC unavailable — skipping | %s", exc)
        return JSONResponse({"on_wa": True, "checked": False, "phone": wa})
    except Exception as exc:
        logger.error("WA check | unexpected error | %s", exc, exc_info=True)
        return JSONResponse({"on_wa": True, "checked": False, "phone": wa})
