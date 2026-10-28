"""
Copy Utility — Humanized LLM Text for Workflows
================================================

Single-call LLM utilities used by Leo Workflows to produce natural,
human-sounding copy. These are NOT Hermes tools — they are shared
functions any workflow can call directly.

Design principles:
- Each function makes exactly ONE LLM call (Claude Haiku 4.5 via Bedrock).
- No agent loop. No tool dispatch. Input in, text out.
- Always async (workflows are async Python).
- Fail gracefully — return a sensible fallback on any LLM error so
  the workflow can proceed with slightly less polish.

Why Haiku and not a bigger model:
- These are ~200-token generation tasks: summarise a brief, personalise
  an opener. Haiku is fast (~0.5s), cheap (<$0.001 per call), and
  perfectly capable at short naturalistic text.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from typing import Any

from core import bedrock_client

logger = logging.getLogger(__name__)

_HAIKU_MODEL = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
_AWS_REGION = os.getenv("AWS_REGION", "eu-west-1")


def _get_bedrock():
    return bedrock_client(_AWS_REGION, read_timeout=30, connect_timeout=10, max_attempts=1)


def _converse_sync(system: str, user: str, max_tokens: int = 300) -> str:
    """Synchronous Bedrock Converse call. Used inside asyncio.to_thread()."""
    client = _get_bedrock()
    response = client.converse(
        modelId=_HAIKU_MODEL,
        system=[{"text": system}],
        messages=[{"role": "user", "content": [{"text": user}]}],
        inferenceConfig={"maxTokens": max_tokens, "temperature": 0.7},
    )
    msg = response.get("output", {}).get("message", {})
    parts = [
        block["text"]
        for block in msg.get("content", []) or []
        if isinstance(block, dict) and "text" in block
    ]
    return "\n".join(parts).strip()


# ─── humanize_job_summary ─────────────────────────────────────────────

_HUMANIZE_SYSTEM = """\
You write short, natural descriptions of home renovation jobs for WhatsApp messages.
Peter from Leo is reaching out to a tradesperson about a homeowner's project.
The slot you fill ({{2}} in the Meta template) must:
- Be a natural English or Spanish phrase of 5-12 words
- Sound like a human typed it, not a form
- Be lowercase (fits mid-sentence: "There's a [your text] in Palma")
- Be specific to the actual work, not generic ("renovation" is too vague)
- Mention the most distinctive element of the job
- No full stop at the end

Only output the phrase. No explanation, no quotes."""

_HUMANIZE_USER = """\
Brief title: {title}
Full description: {description}
Location: {location}
Trade: {trade}
Language: {language}

Output the phrase in {language}."""


async def humanize_job_summary(brief: dict, language: str = "en") -> str:
    """Turn a homeowner brief into a natural one-liner for WhatsApp template slot {{2}}.

    Example output (EN): "retiling a bathroom and sorting out some dodgy plumbing"
    Example output (ES): "hacer el alicatado del baño y arreglar la fontanería"

    Falls back to a simple "{title} in {location}" on any error.
    """
    title = str(brief.get("title") or brief.get("trade") or "home project").strip()
    description = str(brief.get("description") or "").strip()[:400]
    location = str(brief.get("location") or "").strip()
    trade = str(brief.get("trade") or "").strip()
    lang_label = "Spanish" if language == "es" else "English"

    fallback = f"{title.lower()} in {location}" if location else title.lower()

    if not description and not title:
        return fallback

    user_msg = _HUMANIZE_USER.format(
        title=title,
        description=description or title,
        location=location or "Spain",
        trade=trade or title,
        language=lang_label,
    )

    try:
        result = await asyncio.to_thread(_converse_sync, _HUMANIZE_SYSTEM, user_msg, 60)
        result = result.strip().strip('"').strip("'").rstrip(".")
        if not result or len(result) < 4:
            return fallback
        logger.info("copy.humanize_job_summary | '%s' → '%s'", title[:40], result[:60])
        return result
    except Exception as e:
        logger.warning("copy.humanize_job_summary failed, using fallback: %s", e)
        return fallback


# ─── craft_first_reply ────────────────────────────────────────────────

_FIRST_REPLY_SYSTEM_EN = """\
You are Peter from Leo, a platform that connects homeowners with tradespeople in Spain.
A tradesperson just replied to your outreach WhatsApp message about a job.
Write a warm, personal follow-up message that:
- Opens with something specific from their profile (a project, a location, a skill)
- Briefly describes the homeowner's job in one sentence
- Ends with a simple invitation to learn more ("Happy to send the full details if you're interested")
- Sounds like a real person wrote it — conversational, not corporate
- Is 3-4 sentences max, no bullet points, WhatsApp plain text
- Signs off: "Peter, Leo"

Only output the message text. No explanation."""

_FIRST_REPLY_SYSTEM_ES = """\
Eres Peter de Leo, una plataforma que conecta propietarios con profesionales en España.
Un profesional acaba de responder a tu mensaje de WhatsApp sobre un trabajo.
Escribe un mensaje cercano y personal que:
- Empieza mencionando algo concreto de su perfil (un proyecto, una zona, una especialidad)
- Describe el trabajo del propietario en una frase
- Termina con una invitación sencilla a saber más ("Si te cuadra, te mando todos los detalles")
- Suena como lo escribió una persona real — conversacional, no corporativo
- Máximo 3-4 frases, sin puntos ni listas, texto plano de WhatsApp
- Firma: "Peter, Leo"

Solo escribe el texto del mensaje. Sin explicaciones."""

_FIRST_REPLY_USER = """\
Contractor name: {name}
Their profile / where we found them: {profile_summary}
The homeowner's job: {brief_summary}
Location: {location}"""


async def craft_first_reply(
    brief: dict,
    contractor_profile: dict,
    language: str = "en_US",
) -> str:
    """Write a personal follow-up message when a contractor first replies to outreach.

    Uses the brief + contractor profile data (from Houzz or Facebook snippet) to
    write something that sounds like Peter actually read their profile before reaching out.

    Falls back to a generic but warm message on any error.
    """
    is_es = language in ("es", "es_ES", "es-ES")
    system = _FIRST_REPLY_SYSTEM_ES if is_es else _FIRST_REPLY_SYSTEM_EN

    name = str(contractor_profile.get("name") or "").strip()
    first_name = name.split()[0] if name else ""

    profile_summary = _build_profile_summary(contractor_profile)
    brief_summary = _build_brief_summary(brief)
    location = str(brief.get("location") or "Spain").strip()

    user_msg = _FIRST_REPLY_USER.format(
        name=name or "the contractor",
        profile_summary=profile_summary,
        brief_summary=brief_summary,
        location=location,
    )

    if is_es:
        fallback = (
            f"Buenas{' ' + first_name if first_name else ''},\n\n"
            f"Gracias por contestar. {brief_summary} en {location}. "
            f"Si te cuadra, te mando todos los detalles.\n\n"
            f"Peter, Leo"
        )
    else:
        fallback = (
            f"Hi{' ' + first_name if first_name else ''},\n\n"
            f"Thanks for getting back to me. {brief_summary} in {location}. "
            f"Happy to send the full details if you're interested.\n\n"
            f"Peter, Leo"
        )

    try:
        result = await asyncio.to_thread(_converse_sync, system, user_msg, 300)
        result = result.strip()
        if not result or len(result) < 20:
            return fallback
        logger.info(
            "copy.craft_first_reply | %s | %s chars",
            (name or "unknown")[:30],
            len(result),
        )
        return result
    except Exception as e:
        logger.warning("copy.craft_first_reply failed, using fallback: %s", e)
        return fallback


# ─── helpers ─────────────────────────────────────────────────────────

def _build_profile_summary(profile: dict) -> str:
    """Build a brief human-readable summary of contractor profile data."""
    parts = []
    if profile.get("profile_url"):
        source = profile.get("found_via") or "online"
        parts.append(f"Found on {source}: {profile['profile_url']}")
    if profile.get("trade"):
        parts.append(f"Trade: {profile['trade']}")
    if profile.get("address") or profile.get("location"):
        parts.append(f"Based in: {profile.get('address') or profile.get('location')}")
    if profile.get("area_served"):
        parts.append(f"Serves: {profile['area_served']}")
    if profile.get("fb_post_snippet"):
        parts.append(f"Facebook mention: \"{profile['fb_post_snippet'][:150]}\"")
    if profile.get("fb_group_name"):
        parts.append(f"Found in group: {profile['fb_group_name']}")
    if not parts:
        return "No profile data available — they replied to our outreach message."
    return "\n".join(parts)


def _build_brief_summary(brief: dict) -> str:
    """Build a one-sentence summary of the job brief."""
    title = str(brief.get("title") or "").strip()
    description = str(brief.get("description") or "").strip()[:200]
    if description:
        return description
    return title or "home renovation project"
