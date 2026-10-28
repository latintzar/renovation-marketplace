"""
Instagram Phone Scraper Route
==============================

Searches Instagram for tradespeople profiles by trade + city.
Extracts phone numbers from bios and linked websites.
Saves results to CSV so the sales tracker can consume them.
"""

import asyncio
import csv
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from fastapi import APIRouter, Query, HTTPException
from scrapers.instagram_scraper import scrape_instagram_profiles

logger = logging.getLogger(__name__)
search_instagram_router = APIRouter()

REPORTS_DIR = Path("/root/leo/internal/scripts/habitissimo-growth-hack/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


def _save_instagram_csv(trade: str, city: str, profiles: list[dict]) -> Path:
    """Save Instagram profiles to CSV in the same reports/ dir the sales tracker reads."""
    slug = city.lower().replace(" ", "_").replace("á", "a").replace("é", "e") \
                       .replace("í", "i").replace("ó", "o").replace("ú", "u")
    ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    fname = f"phones_instagram_{trade}_{slug}_{ts}.csv"
    path = REPORTS_DIR / fname

    fieldnames = ["name", "phone", "phone_type", "profile_url", "bio", "username", "website", "source"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for p in profiles:
            writer.writerow({
                "name": p.get("name", ""),
                "phone": p.get("phone", ""),
                "phone_type": "mobile",
                "profile_url": p.get("url", ""),
                "bio": (p.get("bio") or "")[:200],
                "username": p.get("username", ""),
                "website": p.get("website", ""),
                "source": "instagram",
            })

    logger.info("Instagram CSV saved: %s (%d profiles)", fname, len(profiles))
    return path


@search_instagram_router.get("/api/search/instagram")
async def search_instagram_profiles(
    trade: str = Query(..., description="Trade type (e.g. 'fontanero', 'albanil', 'electricista')"),
    city: str = Query(..., description="City name (e.g. 'Málaga', 'Madrid', 'Barcelona')"),
    save_csv: bool = Query(True, description="Save results to CSV for sales tracker"),
) -> Dict[str, Any]:
    """
    Search Instagram for tradespeople profiles matching trade + city.
    Extract phone numbers from bios and linked websites.

    Results are automatically saved to CSV in the reports/ directory so the
    sales tracker can pick them up on next replenish.
    """
    try:
        logger.info("Instagram search: %s in %s", trade, city)
        results = await scrape_instagram_profiles(trade=trade, city=city, parallelize=True)

        csv_path = None
        if save_csv and results.get("profiles"):
            csv_path = str(_save_instagram_csv(trade, city, results["profiles"]))

        return {
            "trade": trade,
            "city": city,
            "total_profiles": results.get("total_profiles", 0),
            "profiles_with_phone": results.get("profiles_with_phone", 0),
            "results": results.get("profiles", []),
            "deduped": True,
            "proxies_used": results.get("proxies_used", 0),
            "queries_run": results.get("queries_run", 0),
            "csv_saved": csv_path,
            "timestamp": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error("Instagram search failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=f"Instagram search failed: {str(e)}")


@search_instagram_router.get("/api/search/instagram/batch")
async def search_instagram_batch(
    trades: str = Query(..., description="Comma-separated trades"),
    cities: str = Query(..., description="Comma-separated cities"),
) -> List[Dict[str, Any]]:
    """
    Batch search Instagram for multiple trade + city combinations.
    Runs them concurrently (up to 3 in parallel).
    """
    try:
        trade_list = [t.strip() for t in trades.split(",") if t.strip()]
        city_list = [c.strip() for c in cities.split(",") if c.strip()]

        combos = [(t, c) for t in trade_list for c in city_list]
        logger.info("Instagram batch: %d combos", len(combos))

        # Limit concurrency to 3 to avoid hammering Bright Data
        sem = asyncio.Semaphore(3)

        async def _one(trade: str, city: str) -> Dict[str, Any]:
            async with sem:
                return await search_instagram_profiles(trade=trade, city=city, save_csv=True)

        return await asyncio.gather(*[_one(t, c) for t, c in combos])

    except Exception as e:
        logger.error("Batch Instagram search failed: %s", e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
