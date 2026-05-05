"""
sarvam.py — Sarvam AI Service
===============================
Wraps the three Sarvam API calls (STT, Translate, TTS).
Cache integration happens ABOVE this layer (in main.py / endpoints.py)
so this service stays focused on pure API communication.
"""

import logging
from sarvamai import SarvamAI, AsyncSarvamAI
from app.core.config import settings

logger = logging.getLogger(__name__)


class SarvamService:
    def __init__(self):
        api_key = settings.SARVAM_API_KEY
        if not api_key:
            logger.warning("SarvamAI client NOT initialized — SARVAM_API_KEY is missing.")
            self.client = None
            self.async_client = None
            return

        try:
            self.client = SarvamAI(api_subscription_key=api_key)
            self.async_client = AsyncSarvamAI(api_subscription_key=api_key)
            logger.info("SarvamAI client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize SarvamAI client: {e}")
            self.client = None
            self.async_client = None

    # ── STT ────────────────────────────────────────────────────────────────────

    def transcribe(self, audio_file_path: str, language_code: str = "hi-IN") -> str | None:
        """Convert speech to text using Saaras v3 (synchronous — called via run_in_executor)."""
        if not self.client:
            logger.error("transcribe() called but SarvamAI client is not initialized.")
            return None

        try:
            logger.info(f"[STT] Calling Saaras v3 | lang={language_code} | file={audio_file_path}")
            with open(audio_file_path, "rb") as audio_file:
                response = self.client.speech_to_text.transcribe(
                    file=audio_file,
                    model="saaras:v3",
                    language_code=language_code,
                )
            if hasattr(response, "transcript"):
                return response.transcript
            if hasattr(response, "model_dump"):
                return response.model_dump().get("transcript", "")
            return str(response)
        except Exception as e:
            logger.error(f"[STT] Saaras v3 error: {e}")
            return None

    # ── Translation ────────────────────────────────────────────────────────────

    def translate(self, text: str, target_language: str = "mr-IN", source_language: str = "hi-IN") -> str | None:
        """Translate text using Sarvam Translate v1 (synchronous — called via run_in_executor)."""
        if not self.client:
            logger.error("translate() called but SarvamAI client is not initialized.")
            return None

        try:
            logger.info(f"[Translate] '{text[:40]}...' → {target_language}")
            response = self.client.text.translate(
                input=text,
                source_language_code=source_language,
                target_language_code=target_language,
                model="sarvam-translate:v1",
            )
            if hasattr(response, "translated_text"):
                return response.translated_text
            if hasattr(response, "model_dump"):
                return response.model_dump().get("translated_text", "")
            return str(response)
        except Exception as e:
            logger.error(f"[Translate] Error → {target_language}: {e}")
            return None

    # ── TTS ────────────────────────────────────────────────────────────────────

    def text_to_speech(self, text: str, target_language: str = "mr-IN", speaker: str = "aditya") -> str | None:
        """Convert text to speech using Bulbul v3 (synchronous — called via run_in_executor)."""
        if not self.client:
            logger.error("text_to_speech() called but SarvamAI client is not initialized.")
            return None

        try:
            logger.info(f"[TTS] Bulbul v3 | lang={target_language} | speaker={speaker} | chars={len(text)}")
            response = self.client.text_to_speech.convert(
                text=text,
                target_language_code=target_language,
                model="bulbul:v3",
                speaker=speaker,
            )
            if hasattr(response, "audios") and response.audios:
                return response.audios[0]
            return None
        except Exception as e:
            logger.error(f"[TTS] Bulbul v3 error | lang={target_language}: {e}")
            return None


sarvam_service = SarvamService()
