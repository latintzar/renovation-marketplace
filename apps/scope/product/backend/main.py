"""
Scope Backend
=============

FastAPI server for the Scope platform.
Handles WhatsApp comms, CS chat, transcription, email webhooks, and web scraping.

Run: uvicorn main:app --reload --port 8000
"""

import asyncio
import logging
import sys
import os
from contextlib import asynccontextmanager

# Put the backend dir on sys.path so local modules (``config``, ``routes``,
# ``workflows``, …) import cleanly under uvicorn's ``main:app``.
# The old ``tools.*`` sys.path hack is gone — Phase 4 Wave B moved
# ``unmigrated/tools/`` into ``packages/scraping/`` (library modules) and
# ``scripts/ops/`` (CLIs), so the backend no longer resolves a top-level
# ``tools`` namespace. Vendor's ``tools/`` package is only used by
# Hermes's own internals.
# __file__ is ``apps/scope/product/backend/main.py`` → walk up four dirs
# to reach the repo root where ``vendor/`` lives (for the Hermes
# skill-manager adapter registration further down this file). Was three
# dirs pre-Apr-2026 when backend lived at apps/scope/product/backend/.
_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
_LEO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_BACKEND_DIR))))
if _BACKEND_DIR not in sys.path:
    sys.path.insert(0, _BACKEND_DIR)
_HERMES_ROOT = os.getenv("HERMES_VENDOR_PATH", os.path.join(_LEO_ROOT, "vendor", "hermes-agent"))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config import settings
from core import (
    AppError,
    check_supabase_health as _db_check_health,
    close_supabase_pool as _db_close_pool,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)

from core import log_active_leo_aws_account, validate_leo_aws_for_bedrock

try:
    validate_leo_aws_for_bedrock()
    log_active_leo_aws_account()
except RuntimeError as e:
    logger.critical("Bedrock/AWS blocked startup: %s", e)
    sys.exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Scope Backend...")
    logger.info(f"   Port: {settings.PORT}")

    try:
        db_ok = await _db_check_health()
        if db_ok:
            logger.info("   Database: Connected")
        else:
            logger.error("   Database: Connection failed")
    except Exception as e:
        logger.error(f"   Database: {e}")

    # Retry any WhatsApp messages that were dropped by a server restart
    try:
        from routes.meta_whatsapp import retry_orphaned_messages
        retried = await retry_orphaned_messages()
        if retried:
            logger.info("   Orphan replay: retried %d conversations", retried)
    except Exception as e:
        logger.warning("   Orphan replay check failed (non-fatal): %s", e)

    # Periodic agent pool eviction (every 15 minutes)
    async def _eviction_loop():
        while True:
            await asyncio.sleep(900)
            try:
                from agent import evict_stale_agents
                evict_stale_agents()
            except Exception as e:
                logger.debug("Agent eviction cycle error: %s", e)

    eviction_task = asyncio.create_task(_eviction_loop())

    # Cron tick loop — checks for due jobs every 60 seconds.
    # Hermes's cron scheduler stores jobs in ~/.hermes/cron/jobs.json.
    # The Hermes Gateway normally ticks this, but we run our own backend,
    # so we tick it ourselves and handle WhatsApp delivery directly.
    async def _cron_tick_loop():
        await asyncio.sleep(10)  # let startup finish
        while True:
            try:
                await asyncio.to_thread(_run_cron_tick)
            except Exception as e:
                logger.warning("Cron tick error (non-fatal): %s", e)
            await asyncio.sleep(60)

    cron_task = asyncio.create_task(_cron_tick_loop())

    yield

    eviction_task.cancel()
    cron_task.cancel()
    logger.info("Shutting down...")
    await _db_close_pool()


def _run_cron_tick():
    """Run one cron tick: check due jobs, execute them, deliver via WhatsApp.

    Runs in a thread executor (called from the async cron loop).
    Hermes's gateway-based delivery (_deliver_result) depends on gateway config
    we don't have, so we handle WhatsApp delivery ourselves using the Meta API.
    """
    import sys
    sys.path.insert(0, _HERMES_ROOT)

    from cron.jobs import get_due_jobs, mark_job_run, save_job_output
    from cron.scheduler import run_job, SILENT_MARKER

    due_jobs = get_due_jobs()
    if not due_jobs:
        return

    logger.info("Cron tick: %d job(s) due", len(due_jobs))

    for job in due_jobs:
        try:
            success, output, final_response, error = run_job(job)
            save_job_output(job["id"], output)

            deliver_content = final_response if success else f"Cron job '{job.get('name', job['id'])}' failed:\n{error}"
            should_deliver = bool(deliver_content)
            if should_deliver and success and deliver_content.strip().upper().startswith(SILENT_MARKER):
                logger.info("Cron job '%s': [SILENT] — skipping delivery", job["id"])
                should_deliver = False

            if should_deliver:
                _deliver_cron_whatsapp(job, deliver_content)

            mark_job_run(job["id"], success, error)
            logger.info("Cron job '%s' (%s) executed | success=%s", job.get("name"), job["id"], success)

        except Exception as e:
            logger.error("Cron job '%s' execution error: %s", job.get("id"), e, exc_info=True)
            mark_job_run(job["id"], False, str(e))


def _deliver_cron_whatsapp(job: dict, content: str):
    """Deliver cron job output via WhatsApp using unified send_wa_message.

    Checks job origin for the target phone. Falls back to founder WhatsApp
    if no origin is set (so jobs always deliver somewhere).
    """
    import os

    origin = job.get("origin") or {}
    chat_id = origin.get("chat_id", "")

    if not chat_id:
        chat_id = os.getenv("PETER_WHATSAPP", '')
        logger.debug("Cron job '%s': no origin chat_id, delivering to founder", job.get("name"))

    phone_digits = str(chat_id).lstrip("+").replace(" ", "").replace("-", "")
    if not phone_digits or len(phone_digits) < 7:
        logger.warning("Cron job '%s': invalid delivery phone '%s'", job.get("name"), chat_id)
        return

    task_name = job.get("name", job["id"])
    body = f"*{task_name}*\n\n{content}"

    from messaging import send_wa_message_sync
    try:
        result = send_wa_message_sync(phone_digits, body[:4096], purpose="internal", do_store=False, skip_window_check=True)
        if result.ok:
            logger.info("Cron delivery sent | job=%s to=%s", task_name, phone_digits[:8])
        else:
            logger.warning("Cron delivery failed | job=%s error=%s", task_name, result.error)
    except Exception as exc:
        logger.error("Cron delivery error | job=%s | %s", task_name, exc)


app = FastAPI(
    title="Scope API",
    description="Backend for the Scope platform — clear agreements for every job",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# AppError → JSONResponse global handler
# ---------------------------------------------------------------------------
# The unified error envelope lives in ``packages/core/src/core/errors.py``.
# Auth deps, dep-injected guards, and route handlers raise ``AppError``
# subclasses (Unauthorized, Forbidden, NotFound, …). Without this handler
# FastAPI treats them as unhandled exceptions and returns 500. We convert
# them here to the canonical ``{"ok": false, "error": ..., "code": ...}``
# JSON body with the subclass's ``status`` code.
@app.exception_handler(AppError)
async def _app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content=exc.to_detail())


# ---------------------------------------------------------------------------
# Route imports
# ---------------------------------------------------------------------------
# Public API routes — mounted under /v1/ (and /api/ for backward compat).
# These are the endpoints exposed to contractors, homeowners, and eventually
# third-party integrators (property managers etc. via API key auth).
from routes.canvas import router as canvas_router
from routes.payment import router as payment_router
from routes.stripe_connect import router as stripe_connect_router
from routes.milestone import router as milestone_router
from routes.messages import router as messages_router
from routes.documents import router as documents_router
from routes.job_inbox import router as job_inbox_router
from routes.chat import router as chat_router
from routes.dispute import router as dispute_router

# New resource-oriented routers (Steps 1-3 of architecture refactor)
from routes.projects import router as projects_router
from routes.milestones import router as milestones_router
from routes.variations import router as variations_router
from routes.reviews import router as reviews_router
from routes.notifications import router as notifications_router

# Internal routes — mounted under /api/ only. Never exposed publicly.
# Includes: webhooks (Stripe, Meta, Resend), operator tools, sales ops,
# admin, marketplace, scraping, transcription, and activity telemetry.
from routes.meta_whatsapp import router as meta_whatsapp_router
from routes.transcribe import router as transcribe_router
from routes.transcribe_stream import router as transcribe_stream_router
from routes.landing_leads import router as landing_leads_router
from routes.profile_import import router as profile_import_router
from routes.extract_doc import router as extract_doc_router
from routes.marketplace import router as marketplace_router
from routes.resend_inbound import router as resend_inbound_router
from routes.pages import router as pages_router
from routes.search_instagram import search_instagram_router
# NOTE: sales_tracker lives in a separate backend product since
# Phase 4 Wave D — see apps/leo-internal-sales/product/backend/ (port 8001).
# The Electron sales recorder connects there directly.
from routes.chatwoot import router as chatwoot_router
from routes.events import router as events_router
from routes.admin import router as admin_router

# ---------------------------------------------------------------------------
# Host adapters — register host-owned helpers so the Leo agent tools can call
# them without violating the package → host import ban. The registry lives in
# ``messaging.frameworks.adapters`` (a generic DI mechanism usable by any
# agent framework provider); host code registers the concrete implementations
# below. See the adapter docstring for rationale.
# ---------------------------------------------------------------------------
from messaging.frameworks import register_host_adapter
from routes import job_inbox as _ji
from workflows import brief_intake as _bi
from workflows import contractor_discovery as _cd

register_host_adapter("job_inbox.create_job", _ji.create_job)
register_host_adapter("job_inbox.get_job_by_id", _ji.get_job_by_id)
register_host_adapter("job_inbox.update_job", _ji.update_job)
register_host_adapter("job_inbox.add_response", _ji.add_response)
register_host_adapter("job_inbox.update_response", _ji.update_response)
register_host_adapter("job_inbox.rank_responses", _ji.rank_responses)
register_host_adapter("job_inbox.find_job_for_contractor_phone", _ji.find_job_for_contractor_phone)
register_host_adapter("job_inbox.get_ops_token", _ji._get_ops_token)

register_host_adapter("workflows.run_brief_intake", _bi.run_brief_intake)
register_host_adapter("workflows.run_contractor_discovery", _cd.run_contractor_discovery)
register_host_adapter("workflows.search_houzz_expanded", _cd._search_houzz_expanded)
register_host_adapter("workflows.search_facebook", _cd._search_facebook)
register_host_adapter("workflows.search_forums", _cd._search_forums)
register_host_adapter("workflows.send_single_outreach", _cd._send_single_outreach)
register_host_adapter("workflows.humanize_brief", _cd._humanize_brief)

# Hermes skill_manager adapter: lazy, optional. skill_manage is a
# founder-only gated tool that runs inside a cron context that already
# injects vendor/hermes-agent on sys.path. Inside the main FastAPI
# runtime the tool handler will call get_adapter(..., required=False)
# and gracefully degrade, so we don't need to force-register here.
# The cron handler registers it on-demand when a job actually calls it.
logger.debug("skill_manager adapter registration deferred to cron runtime")

logger.info("host adapters registered (job_inbox + workflows + skill_manager)")


# ---------------------------------------------------------------------------
# Public API — /v1/ (canonical) + /api/ (backward compat, remove after frontend update)
# ---------------------------------------------------------------------------
_PUBLIC_ROUTERS = [
    (canvas_router,         "Canvas"),
    (payment_router,        "Payment"),
    (stripe_connect_router, "Stripe Connect"),
    (milestone_router,      "Milestone (legacy)"),
    (messages_router,       "Messages"),
    (documents_router,      "Documents"),
    (job_inbox_router,      "Job Inbox"),
    (chat_router,           "Chat"),
    (dispute_router,        "Dispute"),
    # New resource-oriented routes (architecture refactor)
    (projects_router,       "Projects"),
    (milestones_router,     "Milestones"),
    (variations_router,     "Variations"),
    (reviews_router,        "Reviews"),
    (notifications_router,  "Notifications"),
]

for _router, _tag in _PUBLIC_ROUTERS:
    app.include_router(_router, prefix="/v1", tags=[_tag])
    # Backward-compat: old /api/X paths still work while frontend migrates to /v1/X
    app.include_router(_router, prefix="/api", tags=[f"{_tag} (legacy /api)"], include_in_schema=False)

# ---------------------------------------------------------------------------
# Internal API — /api/ only
# ---------------------------------------------------------------------------
app.include_router(meta_whatsapp_router, tags=["Meta WhatsApp"])
app.include_router(transcribe_router, tags=["Transcription"])
app.include_router(transcribe_stream_router, tags=["Transcription"])
app.include_router(landing_leads_router, tags=["Landing Leads"])
app.include_router(profile_import_router, tags=["Profile Import"])
app.include_router(extract_doc_router, tags=["Document Extraction"])
app.include_router(marketplace_router, tags=["Marketplace"])
app.include_router(resend_inbound_router, tags=["Resend Inbound Email"])
app.include_router(pages_router, tags=["Generated Pages"])
app.include_router(search_instagram_router, tags=["Search Instagram"])
# sales_tracker_router was moved to apps/leo-internal-sales/product/backend/ (port 8001)
# in Phase 4 Wave D. The /api/sales/* surface now lives there exclusively.
app.include_router(chatwoot_router, tags=["Chatwoot"])
app.include_router(events_router, tags=["Events"])
app.include_router(admin_router, tags=["Admin"])


@app.get("/health")
async def health_check():
    db_ok = await _db_check_health()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected",
        "version": "2.0.0"
    }


@app.get("/")
async def root():
    return {
        "name": "Scope API",
        "version": "2.0.0",
        "docs": "/docs"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
