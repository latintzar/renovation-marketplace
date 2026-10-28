"""
Leo Marketplace — founder-only dashboard for Hermes capabilities.

Two views:
  1. Leo's Kit  — what's currently active
  2. Discover   — everything available + community, with real popularity data

No toolset/skill distinction exposed to the user. Just things Leo can do.
"""

import json
import logging
import os
import shutil
from pathlib import Path
from typing import Any, Dict, List

from core import http_client
from core import api_error
import yaml
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, JSONResponse

logger = logging.getLogger(__name__)
router = APIRouter()

HERMES_HOME = Path(os.getenv("HERMES_HOME", Path.home() / ".hermes"))
HERMES_SKILLS_DIR = HERMES_HOME / "skills"
HERMES_AGENT_ROOT = Path("/root/leo/tools/hermes-agent")
BUNDLED_SKILLS_DIR = HERMES_AGENT_ROOT / "skills"
OPTIONAL_SKILLS_DIR = HERMES_AGENT_ROOT / "optional-skills"
FOUNDER_TOKEN = os.getenv("MARKETPLACE_TOKEN", '')
SKILLS_SH_API = "https://skills.sh/api/search"


def _check_token(token: str) -> None:
    if token != FOUNDER_TOKEN:
        raise api_error(403, "Founder access only")


# ── What Leo ACTUALLY has active right now ────────────────────────────
# These are the tools registered in leo-quote + the included toolsets
# (web, skills, memory) + native multimodal image support.

CORE = [
    {"id": "update_brief", "name": "Job Brief Builder", "desc": "Builds structured job scopes from homeowner conversations — title, description, location, urgency, materials, budget.", "icon": "📋"},
    {"id": "update_profile", "name": "Profile Builder", "desc": "Builds tradesperson profiles from onboarding chats — business name, trade, services, bio, certifications.", "icon": "👤"},
    {"id": "save_signup", "name": "Signup Capture", "desc": "Saves early access signups — name, WhatsApp, location. Stores in Supabase.", "icon": "💾"},
    {"id": "send_whatsapp", "name": "WhatsApp Send", "desc": "Sends a WhatsApp message to any phone number. Auto-detects 24h window: sends plain text if open, Meta template if not. Handles referrals, onboarding, and general messaging.", "icon": "📱"},
    {"id": "set_drawer", "name": "UI Drawer Control", "desc": "Controls the action drawer — inline nudges, banners, fullscreen prompts. The visual surface beyond chat.", "icon": "🎛️"},
    {"id": "search_spanish_law", "name": "Spanish Law Search", "desc": "Searches consolidated Spanish legislation via the official BOE API. Building codes, property law, consumer protection.", "icon": "⚖️"},
    {"id": "get_boe_norm_text", "name": "BOE Full Text", "desc": "Fetches the complete text of a specific Spanish law by its BOE identifier.", "icon": "📜"},
    {"id": "search_eu_law", "name": "EU Law Search", "desc": "Searches EU legislation and case law via LexAPI. Construction directives, energy efficiency, consumer rights.", "icon": "🇪🇺"},
    {"id": "propose_skill_change", "name": "Skill Proposals", "desc": "Proposes new capabilities — you approve via WhatsApp before they're applied.", "icon": "💡"},
    {"id": "web_search", "name": "Web Search", "desc": "Searches the web for real-time information. Included via the 'web' toolset.", "icon": "🔍"},
    {"id": "web_extract", "name": "Page Reader", "desc": "Reads and extracts content from any URL. Included via the 'web' toolset.", "icon": "📄"},
    {"id": "memory", "name": "Persistent Memory", "desc": "mem0-based cross-session memory. Renovation prices, building codes, user preferences — remembered forever.", "icon": "🧠"},
    {"id": "skill_manage", "name": "Skill Manager", "desc": "Creates, edits, deletes Hermes skills. Gated — goes through your WhatsApp approval.", "icon": "🔧"},
    {"id": "photo_analysis", "name": "Photo Analysis", "desc": "Analyses photos sent by users — damage assessment, material identification, measurements. Works natively via multimodal messages (no extra toolset needed).", "icon": "📸"},
]

# ── What's available but NOT enabled ──────────────────────────────────
# These are real Hermes toolsets that can be turned on.
# Each has a "rec" field: "high" (Leo Scope would clearly benefit),
# "medium" (useful but not urgent), "low" (niche or risky).
# And a "why" field explaining the Leo Scope angle.

ADDONS = [
    {"id": "code_execution", "name": "Calculator & Code", "desc": "Run Python in a sandbox. Price calculations ('12m² × €35/m² + 10% waste'), unit conversions, mortgage estimates, data processing. Leo can compute instead of just describing math.", "icon": "⚡", "tools": 1, "rec": "high", "why": "Scope pricing — Leo could verify estimates, compute totals, compare quotes"},
    {"id": "cronjob", "name": "Scheduled Tasks & Reminders", "desc": "Schedule follow-ups, reminders, deadline alerts. Delivers to WhatsApp, Telegram, email, SMS. Cron-based — survives restarts. 'Remind the homeowner in 3 days to check if the work was done.'", "icon": "⏰", "tools": 1, "rec": "high", "why": "Job lifecycle — automatic follow-ups, payment reminders, scope expiry alerts"},
    {"id": "delegation", "name": "Parallel Research", "desc": "Spawn sub-agents to research multiple things simultaneously. 'Compare plumber prices in Madrid vs Barcelona' — researches both at once.", "icon": "🔀", "tools": 1, "rec": "high", "why": "Multi-city price research, comparing multiple contractors, parallel quote analysis", "note": "2-3× LLM cost per use"},
    {"id": "session_search", "name": "Conversation History", "desc": "Search past conversations — 'what did we discuss about the kitchen?' Searches the Hermes session database by topic.", "icon": "🏛️", "tools": 1, "rec": "high", "why": "Continuity — homeowners return weeks later, Leo can recall the full history"},
    {"id": "vision", "name": "URL Image Analysis", "desc": "Fetch and analyse images from URLs (not user photos — those already work). Useful for analysing product photos from supplier websites, reference images from links.", "icon": "👁️", "tools": 1, "rec": "medium", "why": "Analyse materials on supplier websites, compare finishes from reference URLs"},
    {"id": "tts", "name": "Voice Replies", "desc": "Generate spoken audio — reply with voice notes instead of text. WhatsApp voice bubbles, Telegram voice messages.", "icon": "🔊", "tools": 1, "rec": "medium", "why": "WhatsApp-native — tradespeople prefer voice over reading long scopes"},
    {"id": "image_gen", "name": "Image Generation", "desc": "Create images from text — before/after visualisations, mood boards, floor plan sketches. Uses the configured image model.", "icon": "🎨", "tools": 1, "rec": "medium", "why": "Scope visualisation — help homeowners picture what the finished job looks like"},
    {"id": "browser", "name": "Full Web Browser", "desc": "Navigate pages, click buttons, fill forms, take screenshots. 11 tools for complete browser automation.", "icon": "🌐", "tools": 11, "rec": "low", "why": "Could scrape supplier prices from JS-heavy sites, but heavy and slow", "note": "Needs headless Chrome"},
    {"id": "terminal", "name": "Server Shell", "desc": "Run commands directly on the server. Very powerful — and very dangerous in a customer-facing agent.", "icon": "💻", "tools": 2, "rec": "low", "warn": "Full server access — dangerous for customer-facing use"},
    {"id": "file", "name": "File System", "desc": "Read, write, search files on the server. Useful for internal ops, risky for customer-facing.", "icon": "📁", "tools": 4, "rec": "low", "warn": "Full disk access — dangerous for customer-facing use"},
]

# ── What Leo covers mapped to common community skill keywords ─────────
# Used to show "you already have this" when browsing community

LEO_COVERAGE = {
    "web-search": "web_search",
    "web-scraper": "web_extract",
    "web-extract": "web_extract",
    "web-design": None,
    "search": "web_search",
    "research": "web_search",
    "memory": "memory",
    "memory-merger": "memory",
    "agent-browser": "browser",
    "browser-use": "browser",
    "browser": "browser",
    "code": "code_execution",
    "calculator": "code_execution",
    "agent-tools": None,
    "stitch": None,
    "pdf": None,
    "git-commit": None,
    "github": None,
}


def _parse_skill(path: Path) -> Dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {"name": path.parent.name, "desc": ""}
    name = path.parent.name
    desc = ""
    tags = []
    version = ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            try:
                fm = yaml.safe_load(parts[1])
                if isinstance(fm, dict):
                    name = fm.get("name", name)
                    desc = fm.get("description", "")
                    version = fm.get("version", "")
                    meta = fm.get("metadata", {})
                    if isinstance(meta, dict):
                        h = meta.get("hermes", {})
                        if isinstance(h, dict):
                            tags = h.get("tags", [])
            except yaml.YAMLError:
                pass
    if not desc:
        for line in text.split("\n"):
            s = line.strip()
            if s and not s.startswith("#") and not s.startswith("---"):
                desc = s[:200]
                break
    return {"name": name, "desc": str(desc)[:300], "tags": tags or [], "version": str(version)}


def _scan_skills(base: Path, source: str) -> List[Dict[str, Any]]:
    results = []
    if not base.exists():
        return results
    for md in sorted(base.rglob("SKILL.md")):
        rel = md.parent.relative_to(base)
        parts = rel.parts
        cat = parts[0] if len(parts) > 1 else "general"
        info = _parse_skill(md)
        results.append({
            "id": f"skill:{rel}", "dir": str(rel), "name": info["name"],
            "desc": info["desc"], "category": cat, "tags": info["tags"],
            "version": info["version"], "icon": "📦", "source": source,
        })
    return results


def _enabled_skill_dirs() -> set:
    s = set()
    if HERMES_SKILLS_DIR.exists():
        for md in HERMES_SKILLS_DIR.rglob("SKILL.md"):
            s.add(str(md.parent.relative_to(HERMES_SKILLS_DIR)))
    return s


def _toolset_config() -> List[str]:
    p = Path(__file__).parent.parent / "marketplace_config.json"
    if p.exists():
        try:
            return json.loads(p.read_text()).get("enabled_toolsets", [])
        except Exception:
            pass
    return []


def _leo_overlap(name: str) -> str | None:
    """Return the Leo capability ID that covers this community skill, if any."""
    name_lower = name.lower().replace("_", "-")
    for keyword, leo_id in LEO_COVERAGE.items():
        if keyword in name_lower:
            return leo_id
    return None


# ── Routes ────────────────────────────────────────────────────────────

@router.get("/marketplace", response_class=HTMLResponse)
async def marketplace_page(token: str = Query(default="")):
    _check_token(token)
    p = Path(__file__).parent.parent / "marketplace.html"
    if not p.exists():
        raise api_error(500, "HTML not found")
    return HTMLResponse(p.read_text(encoding="utf-8"))


@router.get("/api/marketplace/state")
async def marketplace_state(token: str = Query(default="")):
    _check_token(token)
    en_skills = _enabled_skill_dirs()
    en_toolsets = _toolset_config()

    kit = []
    for c in CORE:
        kit.append({**c, "enabled": True, "locked": True, "kind": "core"})
    for a in ADDONS:
        if a["id"] in en_toolsets:
            kit.append({**a, "enabled": True, "locked": False, "kind": "addon"})

    discover = []
    for a in ADDONS:
        if a["id"] not in en_toolsets:
            discover.append({**a, "enabled": False, "locked": False, "kind": "addon"})

    bundled = _scan_skills(BUNDLED_SKILLS_DIR, "bundled")
    optional = _scan_skills(OPTIONAL_SKILLS_DIR, "community")
    all_skills = bundled + optional

    for s in all_skills:
        s["enabled"] = s.get("dir", "") in en_skills
        s["locked"] = False
        s["kind"] = "skill"
        if s["enabled"]:
            kit.append(s)
        else:
            discover.append(s)

    # Build a set of capability names for overlap detection
    all_ids = {c["id"] for c in CORE} | {a["id"] for a in ADDONS}

    return JSONResponse({
        "kit": kit,
        "discover": discover,
        "stats": {
            "active": len(kit),
            "available": len(discover),
            "total_skills": len(all_skills),
        },
        "leo_ids": sorted(all_ids),
    })


@router.get("/api/marketplace/community")
async def marketplace_community(
    token: str = Query(default=""),
    q: str = Query(default="popular"),
    limit: int = Query(default=30, le=50),
):
    """Search community skills via skills.sh with real install counts + Leo overlap info."""
    _check_token(token)
    results = []

    if q and q != "popular":
        queries = [q]
    else:
        queries = ["web", "agent", "code", "pdf", "github", "search",
                    "browser", "productivity", "research", "memory"]

    try:
        async with http_client(timeout=8) as client:
            for query in queries:
                if len(query) < 2:
                    continue
                per = max(3, limit // len(queries))
                resp = await client.get(SKILLS_SH_API, params={"q": query, "limit": per})
                if resp.status_code == 200:
                    data = resp.json()
                    items = data.get("skills", data.get("results", []))
                    for item in items:
                        if not isinstance(item, dict):
                            continue
                        name = item.get("name", item.get("skillId", ""))
                        if any(r["name"] == name for r in results):
                            continue
                        overlap = _leo_overlap(name)
                        results.append({
                            "name": name,
                            "desc": item.get("description", ""),
                            "installs": item.get("installs", 0),
                            "source": item.get("source", item.get("id", "").rsplit("/", 1)[0] if "/" in item.get("id", "") else ""),
                            "id": item.get("id", ""),
                            "leo_overlap": overlap,
                        })
    except Exception as e:
        logger.warning("skills.sh error: %s", e)

    results.sort(key=lambda x: x.get("installs", 0), reverse=True)
    return JSONResponse({"results": results[:limit], "source": "skills.sh"})


@router.post("/api/marketplace/toggle")
async def toggle_capability(token: str = Query(default=""), id: str = Query(...)):
    _check_token(token)
    if id.startswith("skill:"):
        return _toggle_skill(id[6:])
    return _toggle_toolset(id)


def _toggle_skill(skill_dir: str) -> JSONResponse:
    target = HERMES_SKILLS_DIR / skill_dir
    src_b = BUNDLED_SKILLS_DIR / skill_dir
    src_o = OPTIONAL_SKILLS_DIR / skill_dir
    if target.exists():
        shutil.rmtree(target)
        p = target.parent
        if p != HERMES_SKILLS_DIR and p.exists() and not any(p.iterdir()):
            p.rmdir()
        logger.info("Marketplace: disabled skill %s", skill_dir)
        return JSONResponse({"ok": True, "action": "disabled", "id": f"skill:{skill_dir}"})
    src = src_b if src_b.exists() else src_o
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"Not found: {skill_dir}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(src, target)
    logger.info("Marketplace: enabled skill %s", skill_dir)
    return JSONResponse({"ok": True, "action": "enabled", "id": f"skill:{skill_dir}"})


def _toggle_toolset(tid: str) -> JSONResponse:
    if not any(a["id"] == tid for a in ADDONS):
        raise HTTPException(status_code=404, detail=f"Unknown: {tid}")
    cfg_path = Path(__file__).parent.parent / "marketplace_config.json"
    cfg = {}
    if cfg_path.exists():
        try:
            cfg = json.loads(cfg_path.read_text())
        except Exception:
            pass
    enabled = cfg.get("enabled_toolsets", [])
    if tid in enabled:
        enabled.remove(tid)
        action = "disabled"
    else:
        enabled.append(tid)
        action = "enabled"
    cfg["enabled_toolsets"] = enabled
    cfg_path.write_text(json.dumps(cfg, indent=2))
    logger.info("Marketplace: %s %s", action, tid)
    return JSONResponse({"ok": True, "action": action, "id": tid})
