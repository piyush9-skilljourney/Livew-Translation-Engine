from sarvamai import SarvamAI
from app.core.config import settings

class SarvamService:
    def __init__(self):
        api_key = settings.SARVAM_API_KEY
        # Check if key is empty or still the default placeholder
        if not api_key or api_key == "your_key_here":
            print("⚠️ WARNING: SARVAM_API_KEY is not set in .env file.")
            self.client = None
        else:
            try:
                self.client = SarvamAI(api_subscription_key=api_key)
            except Exception as e:
                print(f"❌ ERROR: Failed to initialize SarvamAI client: {e}")
                self.client = None

    def transcribe(self, audio_file_path: str, language_code: str = "hi-IN"):
        """Convert speech to text using Saaras v3."""
        if not self.client:
            print("❌ ERROR: SarvamAI client not initialized.")
            return None
        
        try:
            print(f"🎙 Calling Saaras v3 for {audio_file_path}...")
            with open(audio_file_path, "rb") as audio_file:
                # The correct method is client.speech_to_text.transcribe
                response = self.client.speech_to_text.transcribe(
                    file=audio_file,
                    model="saaras:v3",
                    language_code=language_code
                )
            # Response is usually a Pydantic object, but let's be safe
            return getattr(response, "transcript", str(response))
        except Exception as e:
            print(f"❌ STT Error: {str(e)}")
            return None

    def translate(self, text: str, target_language: str = "mr-IN"):
        """Translate text using Sarvam Translate."""
        if not self.client:
            return None
        
        try:
            print(f"🌐 Calling translation for text: {text[:20]}...")
            # The correct method is client.text.translate
            response = self.client.text.translate(
                input=text,
                source_language_code="hi-IN",
                target_language_code=target_language,
                model="sarvam-translate:v1"
            )
            # Response is a TranslationResponse object
            return getattr(response, "translated_text", str(response))
        except Exception as e:
            print(f"❌ Translation Error: {str(e)}")
            return None

    def text_to_speech(self, text: str, target_language: str = "mr-IN"):
        """Convert text to speech using Bulbul v3."""
        if not self.client:
            return None
        
        try:
            print(f"🔊 Calling Bulbul v3 for {target_language}...")
            # The correct method is client.text_to_speech.convert
            response = self.client.text_to_speech.convert(
                text=text,
                target_language_code=target_language,
                model="bulbul:v3",
                speaker="aditya"
            )
            # The SDK returns a list of audios in the 'audios' field
            if hasattr(response, "audios") and response.audios:
                return response.audios[0]
            return None
        except Exception as e:
            print(f"❌ TTS Error: {str(e)}")
            return None

sarvam_service = SarvamService()
