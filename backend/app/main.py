"""
main.py — BhashaCast FastAPI Server
=====================================
WebSocket endpoints for Speaker (/ws/speaker) and Listener (/ws/listener).
Two-level cache (LRU + MongoDB) sits between STT and the broadcast pipeline
to eliminate repeat Translate + TTS API costs (83.7% of total spend).

Data Flow:
  Speaker → PCM chunks → WAV → Saaras STT
  → normalize → Translation Cache (L1/L2) → Sarvam Translate (on miss)
  → TTS Cache (L1/L2) → Bulbul TTS (on miss)
  → Broadcast JSON to all Listeners
"""

import asyncio
import base64
import io
import json
import logging
import os
import tempfile
import time
import wave
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.cache import cache_service
from app.core.config import settings
from app.services.sarvam import sarvam_service

logger = logging.getLogger(__name__)

# ── App Lifespan (startup / shutdown) ─────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 BhashaCast starting up...")
    await cache_service.startup()
    yield
    logger.info("🛑 BhashaCast shutting down...")
    await cache_service.shutdown()

app = FastAPI(title=settings.PROJECT_NAME, lifespan=lifespan)

# ── CORS ───────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to specific origins in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.endpoints import router as translation_router
app.include_router(translation_router, prefix="/api/v1")

# ── State ──────────────────────────────────────────────────────────────────────

# Maps websocket → (target_language_code, voice)
active_listeners: dict[WebSocket, tuple[str, str]] = {}

MAX_BUFFER_CHUNKS = 300   # ~15 seconds at 16kHz/16-bit to prevent OOM

# ── Audio Utilities ────────────────────────────────────────────────────────────

def pcm_chunks_to_wav_b64(chunks: list[bytes], sample_rate: int = 16000) -> str:
    """Combine raw PCM chunks into a base64-encoded WAV string."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)       # 16-bit PCM
        wf.setframerate(sample_rate)
        for chunk in chunks:
            wf.writeframes(chunk)
    return base64.b64encode(wav_io.getvalue()).decode("utf-8")


def write_wav_tempfile(chunks: list[bytes], sample_rate: int = 16000) -> str:
    """Write PCM chunks to a temp WAV file. Caller is responsible for unlinking."""
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = tmp.name
        wav_io = io.BytesIO()
        with wave.open(wav_io, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            for chunk in chunks:
                wf.writeframes(chunk)
        tmp.write(wav_io.getvalue())
    return tmp_path


# ── Listener WebSocket ─────────────────────────────────────────────────────────

@app.websocket("/ws/listener")
async def websocket_listener(
    websocket: WebSocket,
    lang: str  = Query(default="mr-IN"),
    voice: str = Query(default="aditya"),
):
    await websocket.accept()
    active_listeners[websocket] = (lang, voice)
    logger.info(f"👥 Listener joined | lang={lang} voice={voice} | total={len(active_listeners)}")

    try:
        while True:
            # Keep the connection alive; listeners only receive, never send
            await websocket.receive()
    except WebSocketDisconnect:
        active_listeners.pop(websocket, None)
        logger.info(f"🔌 Listener disconnected | remaining={len(active_listeners)}")
    except Exception as e:
        active_listeners.pop(websocket, None)
        logger.error(f"❌ Listener error: {e}")


# ── Broadcast Pipeline (with Cache) ───────────────────────────────────────────

async def broadcast_translation(text: str, src_lang: str, loop: asyncio.AbstractEventLoop, original_audio_b64: Optional[str] = None):
    """
    Translate text into each listener's language and broadcast the TTS audio.
    If original_audio_b64 is provided and target_lang == src_lang, use that for zero-cost pass-through.
    """
    if not text.strip() or not active_listeners:
        return

    # Group listeners by (target_language, voice) to minimize API calls
    lang_groups: dict[tuple[str, str], list[WebSocket]] = {}
    for ws, prefs in list(active_listeners.items()):
        lang_groups.setdefault(prefs, []).append(ws)

    for (target_lang, voice), listeners in lang_groups.items():
        try:
            t_start = time.perf_counter()

            # ── Optimization: Same-Language Skip (Original Audio Pass-through) ────────
            if target_lang.strip().lower() == src_lang.strip().lower():
                logger.info(f"[Pipeline] PASS-THROUGH for {target_lang} (Source == Target)")
                broadcast_msg = {
                    "type":              "audio",
                    "audio":             original_audio_b64, # Use real speaker voice!
                    "text":              text,
                    "latency_s":         0,
                    "translate_cached":  True,
                    "tts_cached":        True,
                }
                dead: list[WebSocket] = []
                for listener in listeners:
                    try:
                        await listener.send_json(broadcast_msg)
                    except:
                        dead.append(listener)
                for d in dead:
                    active_listeners.pop(d, None)
                continue # Skip to next language group

            # ── Step 1: Translation (cache-first) ─────────────────────────────

            translated: Optional[str] = await cache_service.get_translation(text, src_lang, target_lang)
            translate_cached = translated is not None

            if not translate_cached:
                t0 = time.perf_counter()
                translated = await loop.run_in_executor(
                    None,
                    lambda l=target_lang: sarvam_service.translate(text, target_language=l, source_language=src_lang),
                )
                t1 = time.perf_counter()
                if not translated:
                    logger.warning(f"[Translate] Empty result for {target_lang}")
                    continue
                await cache_service.set_translation(text, src_lang, target_lang, translated)
                logger.info(f"[Translate] MISS → API call ({t1-t0:.2f}s) | {target_lang}: {translated[:60]}")
            else:
                logger.info(f"[Translate] HIT  → cache | {target_lang}: {translated[:60]}")

            # ── Step 2: TTS (cache-first) ──────────────────────────────────────
            audio_b64: Optional[str] = await cache_service.get_tts(translated, target_lang, voice)
            tts_cached = audio_b64 is not None

            if not tts_cached:
                t2 = time.perf_counter()
                audio_b64 = await loop.run_in_executor(
                    None,
                    lambda l=target_lang, t=translated, v=voice: sarvam_service.text_to_speech(t, target_language=l, speaker=v),
                )
                t3 = time.perf_counter()
                if not audio_b64:
                    logger.warning(f"[TTS] Empty result for {target_lang}-{voice}")
                    continue
                await cache_service.set_tts(translated, target_lang, voice, audio_b64)
                logger.info(f"[TTS] MISS → API call ({t3-t2:.2f}s) | {target_lang}-{voice}")
            else:
                logger.info(f"[TTS] HIT  → cache | {target_lang}-{voice}")

            t_end = time.perf_counter()
            total_latency = round(t_end - t_start, 3)

            # ── Step 3: Broadcast ──────────────────────────────────────────────
            broadcast_msg = {
                "type":              "audio",
                "audio":             audio_b64,
                "text":              translated,
                "latency_s":         total_latency,
                "translate_cached":  translate_cached,
                "tts_cached":        tts_cached,
            }

            logger.info(
                f"🚀 Broadcasting to {len(listeners)} listener(s) | {target_lang}-{voice} "
                f"| latency={total_latency}s "
                f"| translate={'HIT' if translate_cached else 'MISS'} "
                f"| tts={'HIT' if tts_cached else 'MISS'}"
            )

            dead: list[WebSocket] = []
            for listener in listeners:
                try:
                    await listener.send_json(broadcast_msg)
                except Exception:
                    dead.append(listener)
            for d in dead:
                active_listeners.pop(d, None)

        except Exception as e:
            logger.error(f"❌ Broadcast error [{target_lang}]: {e}", exc_info=True)


# ── Speaker WebSocket ──────────────────────────────────────────────────────────

@app.websocket("/ws/speaker")
async def websocket_speaker(
    websocket: WebSocket,
    lang: str = Query(default="hi-IN"),
):
    await websocket.accept()
    logger.info(f"🎤 Speaker connected | src_lang={lang}")
    loop = asyncio.get_event_loop()

    try:
        while True:
            # ── Wait for first PCM chunk ───────────────────────────────────────
            message = await websocket.receive()
            if message.get("bytes") is None:
                continue

            logger.info("🎤 Speaker started speaking — collecting audio chunks...")
            pcm_chunks: list[bytes] = [message["bytes"]]
            flush_timestamp: Optional[float] = None

            # ── Inner loop: collect chunks until flush signal ──────────────────
            while True:
                inner_msg = await websocket.receive()

                if inner_msg.get("bytes") is not None:
                    pcm_chunks.append(inner_msg["bytes"])
                    total_bytes = sum(len(c) for c in pcm_chunks)

                    if len(pcm_chunks) % 8 == 0:
                        duration_ms = (total_bytes // 2) / 16000 * 1000
                        logger.debug(f"📡 Buffered {len(pcm_chunks)} chunks ({duration_ms:.0f}ms)")

                    # Buffer guard: prevent OOM on very long speeches
                    if len(pcm_chunks) >= MAX_BUFFER_CHUNKS:
                        logger.warning(f"⚠️ Buffer guard triggered at {MAX_BUFFER_CHUNKS} chunks — forcing flush")
                        break


                elif inner_msg.get("text") is not None:
                    try:
                        text_data = json.loads(inner_msg["text"])
                        if text_data.get("type") == "flush":
                            flush_timestamp = text_data.get("timestamp")
                            total_bytes = sum(len(c) for c in pcm_chunks)
                            duration_s = (total_bytes // 2) / 16000
                            logger.info(f"🌊 Flush received | {len(pcm_chunks)} chunks | {duration_s:.1f}s of audio")
                            break
                    except json.JSONDecodeError:
                        logger.warning("Received malformed text frame — ignoring")

            if not pcm_chunks:
                logger.warning("No audio chunks collected — skipping transcription")
                continue

            # ── Transcribe ─────────────────────────────────────────────────────
            t_stt_start = time.perf_counter()
            tmp_path = write_wav_tempfile(pcm_chunks)
            try:
                transcript = await loop.run_in_executor(
                    None,
                    lambda: sarvam_service.transcribe(tmp_path, language_code=lang),
                )
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

            if not transcript or not transcript.strip():
                logger.warning("⚠️ Empty transcript from STT — skipping")
                continue

            t_stt_end = time.perf_counter()
            logger.info(f"📥 Transcript: '{transcript}' | STT took {t_stt_end - t_stt_start:.2f}s")

            # ── Echo transcript back to speaker UI ─────────────────────────────
            try:
                await websocket.send_json({
                    "type":            "transcript",
                    "text":            transcript,
                    "flush_timestamp": flush_timestamp,
                })
            except Exception as e:
                logger.warning(f"Failed to echo transcript to speaker: {e}")

            # ── Transcript & Audio Coalescing Logic ───────────────────────────
            if not hasattr(websocket, "coalesce_buffer"):
                websocket.coalesce_buffer = [] # List of (transcript, pcm_bytes)
                websocket.coalesce_lock = asyncio.Lock()

            async def delayed_broadcast():
                start_time = time.time()
                while time.time() - start_time < 2.0:
                    await asyncio.sleep(0.1)
                    async with websocket.coalesce_lock:
                        if not websocket.coalesce_buffer:
                            return
                        last_text = websocket.coalesce_buffer[-1][0].strip()
                        if last_text and last_text[-1] in ".?!":
                            break
                
                async with websocket.coalesce_lock:
                    if websocket.coalesce_buffer:
                        # Merge text and audio
                        merged_text = " ".join([item[0] for item in websocket.coalesce_buffer])
                        all_pcm = b"".join([item[1] for item in websocket.coalesce_buffer])
                        websocket.coalesce_buffer.clear()

                        # Convert merged PCM to base64 WAV for pass-through
                        import io, wave, base64
                        with io.BytesIO() as wav_io:
                            with wave.open(wav_io, 'wb') as wav_file:
                                wav_file.setnchannels(1)
                                wav_file.setsampwidth(2) # 16-bit
                                wav_file.setframerate(16000)
                                wav_file.writeframes(all_pcm)
                            original_audio_b64 = base64.b64encode(wav_io.getvalue()).decode('utf-8')

                        asyncio.create_task(broadcast_translation(merged_text, lang, loop, original_audio_b64))
                        logger.info(f"🌊 Coalesced PASS-THROUGH broadcast: '{merged_text[:50]}...'")

            async with websocket.coalesce_lock:
                # Store both the transcript and the raw pcm data we just processed
                raw_pcm = b"".join(pcm_chunks)
                websocket.coalesce_buffer.append((transcript, raw_pcm))
                if len(websocket.coalesce_buffer) == 1:
                    asyncio.create_task(delayed_broadcast())


    except WebSocketDisconnect:
        logger.info("🔌 Speaker disconnected")
    except Exception as e:
        logger.error(f"❌ Speaker global error: {e}", exc_info=True)


# ── Health & Cache API Endpoints ──────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "running",
        "service": settings.PROJECT_NAME,
        "active_listeners": len(active_listeners),
    }


@app.get("/api/v1/cache/metrics", tags=["Cache"])
async def get_cache_metrics():
    """Returns cache hit/miss stats and estimated API cost saved."""
    return JSONResponse(content=cache_service.metrics.to_dict())


@app.delete("/api/v1/cache", tags=["Cache"])
async def purge_cache(lang: Optional[str] = Query(default=None, description="Language code e.g. 'mr-IN'. Omit to purge all.")):
    """
    Manually invalidate the translation and TTS caches.
    Use after a Sarvam model upgrade or when stale audio is detected.
    """
    result = await cache_service.purge(lang=lang)
    return JSONResponse(content={"purged": result})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
