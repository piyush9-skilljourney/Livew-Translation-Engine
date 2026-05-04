from sarvamai import SarvamAI, AsyncSarvamAI
from app.core.config import settings
from contextlib import asynccontextmanager
import typing
import base64

class SarvamService:
    def __init__(self):
        api_key = settings.SARVAM_API_KEY
        if not api_key or api_key == "your_key_here":
            print("⚠️ WARNING: SARVAM_API_KEY is not set in .env file.")
            self.client = None
            self.async_client = None
        else:
            try:
                self.client = SarvamAI(api_subscription_key=api_key)
                self.async_client = AsyncSarvamAI(api_subscription_key=api_key)
            except Exception as e:
                print(f"❌ ERROR: Failed to initialize SarvamAI client: {e}")
                self.client = None
                self.async_client = None

    @asynccontextmanager
    async def get_streaming_client(self, language_code: str = "hi-IN"):
        """Get a streaming connection to Sarvam AI."""
        if not self.async_client:
            raise Exception("AsyncSarvamAI client not initialized.")
        
        try:
            async with self.async_client.speech_to_text_streaming.connect(
                language_code=language_code,
                model="saaras:v3",
            ) as socket:
                yield socket
        except Exception as e:
            print(f"❌ Sarvam SDK Connection Error: {e}", flush=True)
            raise e

    def transcribe(self, audio_file_path: str, language_code: str = "hi-IN"):
        """Convert speech to text using Saaras v3."""
        if not self.client:
            print("❌ ERROR: SarvamAI client not initialized.")
            return None
        
        try:
            print(f"🎙 Calling Saaras v3 for {audio_file_path}...")
            with open(audio_file_path, "rb") as audio_file:
                response = self.client.speech_to_text.transcribe(
                    file=audio_file,
                    model="saaras:v3",
                    language_code=language_code
                )
            
            if hasattr(response, 'transcript'):
                return response.transcript
            if hasattr(response, 'model_dump'):
                return response.model_dump().get("transcript", "")
            return str(response)
        except Exception as e:
            print(f"❌ STT Error: {str(e)}")
            return None

    def translate(self, text: str, target_language: str = "mr-IN"):
        """Translate text using Sarvam Translate."""
        if not self.client:
            return None
        
        try:
            print(f"🌐 Calling translation for text: {text[:20]}...")
            response = self.client.text.translate(
                input=text,
                source_language_code="hi-IN",
                target_language_code=target_language,
                model="sarvam-translate:v1"
            )
            
            if hasattr(response, 'translated_text'):
                return response.translated_text
            if hasattr(response, 'model_dump'):
                return response.model_dump().get("translated_text", "")
            return str(response)
        except Exception as e:
            print(f"❌ Translation Error: {str(e)}")
            return None

    def text_to_speech(self, text: str, target_language: str = "mr-IN", speaker: str = "aditya"):
        """Convert text to speech using Bulbul v3."""
        if not self.client:
            return None
        
        try:
            print(f"🔊 Calling Bulbul v3 for {target_language} ({speaker})...")
            response = self.client.text_to_speech.convert(
                text=text,
                target_language_code=target_language,
                model="bulbul:v3",
                speaker=speaker
            )
            if hasattr(response, "audios") and response.audios:
                return response.audios[0]
            return None
        except Exception as e:
            print(f"❌ TTS Error: {str(e)}")
            return None

sarvam_service = SarvamService()
