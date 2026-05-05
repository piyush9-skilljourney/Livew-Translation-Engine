"""
endpoints.py — REST API Endpoints
===================================
The /translate-audio endpoint is the HTTP-based alternative to the WebSocket flow.
Cache is integrated here too, so the REST and WebSocket paths share the same savings.
"""

import logging
import os
import uuid

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from app.core.cache import cache_service
from app.services.sarvam import sarvam_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/translate-audio", tags=["Translation"])
async def translate_audio(
    file: UploadFile = File(...),
    target_lang: str = "mr-IN",
    src_lang: str = "hi-IN",
    voice: str = "aditya",
):
    """
    Upload a WAV file → receive translated text + TTS audio base64.
    Both translation and TTS results are cached for reuse.
    """
    temp_filename = f"temp_{uuid.uuid4()}.wav"
    try:
        content = await file.read()
        with open(temp_filename, "wb") as buffer:
            buffer.write(content)
        logger.info(f"[REST] Received audio upload: {file.filename} ({len(content)} bytes)")

        # ── Step 1: Transcribe ─────────────────────────────────────────────────
        transcript = sarvam_service.transcribe(temp_filename, language_code=src_lang)
        transcript = str(transcript).strip() if transcript else ""
        if not transcript:
            logger.warning("[REST] Transcription returned empty result")
            return JSONResponse(content={"original_text": "", "translated_text": "", "audio_base64": ""})

        # ── Step 2: Translation (cache-first) ──────────────────────────────────
        translated = await cache_service.get_translation(transcript, src_lang, target_lang)
        translate_cached = translated is not None

        if not translate_cached:
            translated = sarvam_service.translate(transcript, target_language=target_lang, source_language=src_lang)
            if not translated:
                raise HTTPException(status_code=500, detail="Translation failed")
            await cache_service.set_translation(transcript, src_lang, target_lang, translated)

        logger.info(f"[REST] Translation {'HIT' if translate_cached else 'MISS'}: {translated[:60]}")

        # ── Step 3: TTS (cache-first) ──────────────────────────────────────────
        audio_b64 = await cache_service.get_tts(translated, target_lang, voice)
        tts_cached = audio_b64 is not None

        if not tts_cached:
            audio_b64 = sarvam_service.text_to_speech(translated, target_language=target_lang, speaker=voice)
            if not audio_b64:
                raise HTTPException(status_code=500, detail="TTS generation failed")
            await cache_service.set_tts(translated, target_lang, voice, audio_b64)

        logger.info(f"[REST] TTS {'HIT' if tts_cached else 'MISS'}: {target_lang}-{voice}")

        return {
            "original_text":      transcript,
            "translated_text":    translated,
            "audio_base64":       audio_b64,
            "translate_cached":   translate_cached,
            "tts_cached":         tts_cached,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[REST] translate-audio crashed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
