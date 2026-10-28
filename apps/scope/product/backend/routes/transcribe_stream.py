"""
Deepgram Streaming Transcription Proxy
=======================================

WebSocket endpoint ``/api/transcribe-stream`` — bridges the browser to
Deepgram's real-time streaming API without exposing the API key client-side.

Flow:
  Browser  ---(WebSocket)-->  /api/transcribe-stream  ---(WebSocket)-->  Deepgram
  Browser  <-- JSON events --  backend                <-- JSON events --  Deepgram

Browser sends:
  - Raw audio bytes (any format Deepgram accepts: webm/opus, linear16, etc.)
  - Text JSON message to configure: {"type":"config","language":"es","model":"nova-3"}

Backend sends to browser:
  {"type":"transcript","is_final":true,"text":"Hola, ¿cómo estás?","confidence":0.99}
  {"type":"transcript","is_final":false,"text":"Hola, ¿cómo"}
  {"type":"error","message":"..."}
  {"type":"ready"}   — once Deepgram connection is open

Deepgram model: nova-3  (best multilingual, ~200ms latency)
Docs: https://developers.deepgram.com/reference/speech-to-text/listen-streaming
"""

import asyncio
import json
import logging
import os
import urllib.parse
from typing import Optional

import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

DEEPGRAM_WS_BASE = "wss://api.deepgram.com/v1/listen"

# Default query params — all overridable by client config message
DEEPGRAM_DEFAULTS = {
    "model":               "nova-3",
    "language":            "multi",      # multilingual auto-detect (nova-3 supports this)
    "punctuate":           "true",
    "smart_format":        "true",       # numbers, dates, etc. formatted correctly
    "interim_results":     "true",       # stream partial results as user speaks
    "endpointing":         "700",        # ms of silence before finalising utterance — 300ms was too
                                         # aggressive; caused mid-sentence fragmentation on natural pauses
    "utterance_end_ms":    "1500",       # emit UtteranceEnd event after 1.5s silence so frontend can
                                         # flush and merge any buffered mid-utterance finals cleanly
    "encoding":            "linear16",   # PCM from AudioWorklet / Swift capture_audio
    "sample_rate":         "16000",
    "channels":            "1",
    "filler_words":        "false",
    "diarize":             "false",
}


def _build_deepgram_url(overrides: dict) -> str:
    params = {**DEEPGRAM_DEFAULTS, **overrides}
    return f"{DEEPGRAM_WS_BASE}?{urllib.parse.urlencode(params)}"


@router.websocket("/api/transcribe-stream")
async def transcribe_stream(ws: WebSocket):
    """
    WebSocket proxy: browser audio → Deepgram → transcript events back to browser.

    The client may send an optional JSON config frame first:
        {"type": "config", "language": "es", "model": "nova-3"}
    Then send raw audio bytes for the lifetime of the session.
    """
    await ws.accept()

    dg_key = (settings.DEEPGRAM_API_KEY or "").strip()
    if not dg_key:
        await ws.send_json({"type": "error", "message": "DEEPGRAM_API_KEY not configured on server"})
        await ws.close()
        return

    # --- wait for optional config frame (first message, text only) ---
    overrides: dict = {}
    _buffered: Optional[bytes] = None
    try:
        # Give the client 2s to send a config frame before we open Deepgram
        first = await asyncio.wait_for(ws.receive(), timeout=2.0)
        if first.get("text"):
            try:
                cfg = json.loads(first["text"])
                if cfg.get("type") == "config":
                    if cfg.get("language"):
                        overrides["language"] = cfg["language"]
                    if cfg.get("model"):
                        overrides["model"] = cfg["model"]
                    if cfg.get("encoding"):
                        overrides["encoding"] = cfg["encoding"]
                    if cfg.get("sample_rate"):
                        overrides["sample_rate"] = str(cfg["sample_rate"])
                    if cfg.get("endpointing") is not None:
                        overrides["endpointing"] = str(cfg["endpointing"])
                    if cfg.get("utterance_end_ms") is not None:
                        overrides["utterance_end_ms"] = str(cfg["utterance_end_ms"])
                    logger.info("[DG proxy] config: %s", overrides)
            except Exception:
                pass
        elif first.get("bytes"):
            # Client sent audio immediately — buffer until Deepgram is open
            _buffered = first["bytes"]
    except asyncio.TimeoutError:
        _buffered = None

    dg_url = _build_deepgram_url(overrides)
    logger.info("[DG proxy] connecting to %s", dg_url.split("?")[0])

    try:
        async with websockets.connect(
            dg_url,
            additional_headers={"Authorization": f"Token {dg_key}"},
            max_size=10 * 1024 * 1024,
            ping_interval=10,
            ping_timeout=20,
        ) as dg_ws:
            logger.info("[DG proxy] Deepgram WebSocket open")
            await ws.send_json({"type": "ready"})

            # If we buffered a first audio frame before DG was open, send it now
            if _buffered:
                await dg_ws.send(_buffered)

            async def browser_to_deepgram():
                """Forward raw audio bytes from browser → Deepgram."""
                total_bytes = 0
                try:
                    while True:
                        msg = await ws.receive()
                        if msg.get("bytes"):
                            data = msg["bytes"]
                            total_bytes += len(data)
                            if total_bytes % (16000 * 2 * 2) < len(data):  # log every ~2s
                                logger.info("[DG proxy] audio flowing: %d bytes sent so far", total_bytes)
                            await dg_ws.send(data)
                        elif msg.get("text"):
                            # Allow mid-session control (e.g. flush)
                            try:
                                ctrl = json.loads(msg["text"])
                                if ctrl.get("type") == "finalize":
                                    await dg_ws.send(json.dumps({"type": "Finalize"}))
                            except Exception:
                                pass
                except WebSocketDisconnect:
                    logger.info("[DG proxy] browser disconnected")
                except Exception as e:
                    logger.warning("[DG proxy] browser→DG error: %s", e)
                finally:
                    try:
                        await dg_ws.close()
                    except Exception:
                        pass

            async def deepgram_to_browser():
                """Forward Deepgram transcript events → browser."""
                try:
                    async for raw in dg_ws:
                        if isinstance(raw, bytes):
                            continue  # Deepgram shouldn't send binary, but guard anyway
                        try:
                            evt = json.loads(raw)
                        except Exception:
                            continue

                        msg_type = evt.get("type", "")

                        if msg_type == "Results":
                            channel = evt.get("channel", {})
                            alts    = channel.get("alternatives", [{}])
                            text    = (alts[0].get("transcript") or "").strip()
                            is_final = evt.get("is_final", False)
                            speech_final = evt.get("speech_final", False)
                            confidence = alts[0].get("confidence", 0.0) if alts else 0.0

                            # Log ALL results (even empty) to diagnose audio issues
                            logger.info(
                                "[DG proxy] Results: is_final=%s speech_final=%s text=%r conf=%.2f",
                                is_final, speech_final, text, confidence
                            )

                            if text:
                                await ws.send_json({
                                    "type":         "transcript",
                                    "text":         text,
                                    "is_final":     is_final,
                                    "speech_final": speech_final,
                                    "confidence":   round(confidence, 3),
                                })

                        elif msg_type == "Metadata":
                            logger.info("[DG proxy] metadata: %s", evt)

                        elif msg_type in ("SpeechStarted", "UtteranceEnd"):
                            await ws.send_json({"type": msg_type.lower()})

                        elif msg_type == "error":
                            err = evt.get("description", str(evt))
                            logger.error("[DG proxy] Deepgram error: %s", err)
                            await ws.send_json({"type": "error", "message": err})

                except websockets.exceptions.ConnectionClosed:
                    logger.info("[DG proxy] Deepgram connection closed")
                except Exception as e:
                    logger.warning("[DG proxy] DG→browser error: %s", e)
                finally:
                    try:
                        await ws.close()
                    except Exception:
                        pass

            # Run both directions concurrently
            await asyncio.gather(
                browser_to_deepgram(),
                deepgram_to_browser(),
                return_exceptions=True,
            )

    except Exception as e:
        logger.error("[DG proxy] failed to connect to Deepgram: %s", e)
        try:
            await ws.send_json({"type": "error", "message": f"Deepgram connection failed: {e}"})
            await ws.close()
        except Exception:
            pass
