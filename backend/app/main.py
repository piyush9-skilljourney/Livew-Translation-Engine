from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.services.sarvam import sarvam_service
import asyncio
import base64
import json
import io
import wave
import struct

app = FastAPI(title=settings.PROJECT_NAME)

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://10.179.32.64:5173", # Your network IP
    "*", # Allow all for easier local network testing
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.endpoints import router as translation_router
app.include_router(translation_router, prefix="/api/v1")

import time

# Store listeners as a dict: websocket → (target_language_code, voice)
active_listeners: dict[WebSocket, tuple[str, str]] = {}

MAX_BUFFER_CHUNKS = 300  # Approx 15 seconds of audio to prevent OOM

def pcm_chunks_to_wav_b64(chunks: list[bytes], sample_rate: int = 16000) -> str:
    """Combine all raw PCM chunks into one complete WAV file and return as base64."""
    wav_io = io.BytesIO()
    with wave.open(wav_io, 'wb') as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)     # 16-bit PCM
        wf.setframerate(sample_rate)
        for chunk in chunks:
            wf.writeframes(chunk)
    return base64.b64encode(wav_io.getvalue()).decode('utf-8')


# ──────────────────────────────────────────────
# LISTENER ENDPOINT
# ──────────────────────────────────────────────
@app.websocket("/ws/listener")
async def websocket_listener(
    websocket: WebSocket,
    lang: str = Query(default="mr-IN"),
    voice: str = Query(default="aditya")
):
    await websocket.accept()
    active_listeners[websocket] = (lang, voice)
    print(f"👥 Listener Joined ({lang}, {voice}). Total: {len(active_listeners)}", flush=True)
    try:
        while True:
            await websocket.receive()
    except WebSocketDisconnect:
        active_listeners.pop(websocket, None)
        print("🔌 Listener Disconnected", flush=True)
    except Exception as e:
        active_listeners.pop(websocket, None)
        print(f"❌ Listener Error: {e}", flush=True)


# ──────────────────────────────────────────────
# HELPER: translate + TTS + broadcast
# ──────────────────────────────────────────────
async def broadcast_translation(text: str, loop: asyncio.AbstractEventLoop):
    """For each listener, translate+TTS into their chosen language and send."""
    if not text.strip() or not active_listeners:
        return

    # Group listeners by (language, voice)
    lang_groups: dict[tuple[str, str], list[WebSocket]] = {}
    for ws, prefs in list(active_listeners.items()):
        lang_groups.setdefault(prefs, []).append(ws)

    for (lang, voice), listeners in lang_groups.items():
        try:
            t0 = time.perf_counter()
            translated = await loop.run_in_executor(
                None, lambda l=lang: sarvam_service.translate(text, target_language=l)
            )
            t1 = time.perf_counter()
            if not translated:
                print(f"⚠️ Translation to {lang} returned empty.", flush=True)
                continue
            print(f"✅ [{lang}] Translated: {translated} (Took {t1-t0:.2f}s)", flush=True)

            t2 = time.perf_counter()
            audio_b64 = await loop.run_in_executor(
                None, lambda l=lang, t=translated, v=voice: sarvam_service.text_to_speech(t, target_language=l, speaker=v)
            )
            t3 = time.perf_counter()
            if not audio_b64:
                print(f"⚠️ TTS for {lang} returned empty.", flush=True)
                continue
            print(f"🔊 [{lang}-{voice}] TTS generated (Took {t3-t2:.2f}s)", flush=True)

            broadcast_msg = {
                "type": "audio", 
                "audio": audio_b64, 
                "text": translated,
                "latency_s": round((t1-t0) + (t3-t2), 2)
            }
            print(f"🚀 Broadcasting [{lang}-{voice}] to {len(listeners)} listener(s). Total API Latency: {broadcast_msg['latency_s']}s", flush=True)

            dead = []
            for listener in listeners:
                try:
                    await listener.send_json(broadcast_msg)
                except Exception:
                    dead.append(listener)
            for d in dead:
                active_listeners.pop(d, None)

        except Exception as e:
            print(f"❌ Broadcast Error [{lang}]: {e}", flush=True)


# ──────────────────────────────────────────────
# SPEAKER ENDPOINT
# ──────────────────────────────────────────────
@app.websocket("/ws/speaker")
async def websocket_speaker(
    websocket: WebSocket,
    lang: str = Query(default="hi-IN")
):
    await websocket.accept()
    print(f"🎤 Speaker Connected ({lang})", flush=True)
    loop = asyncio.get_event_loop()

    try:
        while True:
            # ── Wait for first PCM chunk (microphone button pressed) ──
            message = await websocket.receive()
            if message.get("bytes") is None:
                continue

            print("🎤 Speaker pressed button. Collecting audio...", flush=True)
            pcm_chunks: list[bytes] = []
            pcm_chunks.append(message["bytes"])

            # ── Inner loop: collect chunks until button released ──
            while True:
                inner_msg = await websocket.receive()

                if inner_msg.get("bytes") is not None:
                    pcm_chunks.append(inner_msg["bytes"])
                    total = sum(len(c) for c in pcm_chunks)
                    if len(pcm_chunks) % 4 == 0:
                        duration_ms = (total // 2) / 16000 * 1000
                        print(f"📡 Buffered {len(pcm_chunks)} chunks ({duration_ms:.0f}ms)", flush=True)

                    # 🚨 Buffer Guard: Force flush if buffer grows too large
                    if len(pcm_chunks) >= MAX_BUFFER_CHUNKS:
                        print(f"⚠️ Buffer Guard triggered! {MAX_BUFFER_CHUNKS} chunks reached. Forcing processing...", flush=True)
                        break

                elif inner_msg.get("text") is not None:
                    text_data = json.loads(inner_msg["text"])
                    if text_data.get("type") == "flush":
                        # Record flush start time
                        flush_timestamp = time.time()
                        total_bytes = sum(len(c) for c in pcm_chunks)
                        duration_s = (total_bytes // 2) / 16000
                        print(f"🌊 Flush received. {len(pcm_chunks)} chunks, {duration_s:.1f}s of audio.", flush=True)
                        break

            # ── Transcribe using BATCH STT (streaming API is unreliable) ──
            t_stt_start = time.perf_counter()
            print("🧠 Transcribing with Sarvam batch STT...", flush=True)
            import tempfile, os
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp_path = tmp.name
                wav_io = io.BytesIO()
                with wave.open(wav_io, 'wb') as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(16000)
                    for chunk in pcm_chunks:
                        wf.writeframes(chunk)
                tmp.write(wav_io.getvalue())

            try:
                transcript = await loop.run_in_executor(
                    None, lambda l=lang: sarvam_service.transcribe(tmp_path, language_code=l)
                )
            finally:
                os.unlink(tmp_path)

            if not transcript:
                print("⚠️ No transcript from STT. Skipping.", flush=True)
                continue

            t_stt_end = time.perf_counter()
            print(f"📥 Transcript: {transcript} (STT Took {t_stt_end-t_stt_start:.2f}s)", flush=True)

            # Echo transcript to speaker UI
            try:
                # Include a processing timestamp so the frontend can calculate total latency
                await websocket.send_json({
                    "type": "transcript", 
                    "text": transcript,
                    "flush_timestamp": inner_msg.get("timestamp", time.time() * 1000) if 'inner_msg' in locals() and inner_msg.get("text") else None
                })
            except Exception:
                pass

            # Broadcast translation to all listeners
            asyncio.create_task(broadcast_translation(transcript, loop))

    except WebSocketDisconnect:
        print("🔌 Speaker Disconnected", flush=True)
    except Exception as e:
        print(f"❌ Speaker Global Error: {e}", flush=True)


@app.get("/")
async def root():
    return {"message": "Live Translation Engine API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)
