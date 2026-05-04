from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.sarvam import sarvam_service
import os
import uuid
import base64

router = APIRouter()

@router.post("/translate-audio")
async def translate_audio(file: UploadFile = File(...), target_lang: str = "mr-IN"):
    print(f"📥 Received audio upload: {file.filename}")
    temp_filename = f"temp_{uuid.uuid4()}.wav"
    try:
        with open(temp_filename, "wb") as buffer:
            content = await file.read()
            print(f"💾 Saved {len(content)} bytes to {temp_filename}")
            buffer.write(content)

        # 1. Transcribe
        print("🎙 Transcribing...")
        transcript = sarvam_service.transcribe(temp_filename, language_code="hi-IN")
        print(f"📝 Transcript: {transcript}")
        
        if not transcript:
            print("❌ Transcription returned empty result")
            raise HTTPException(status_code=500, detail="Transcription failed")

        # 2. Translate
        print(f"🌐 Translating to {target_lang}...")
        translated_text = sarvam_service.translate(transcript, target_language=target_lang)
        print(f"✅ Translated: {translated_text}")
        
        if not translated_text:
            print("❌ Translation returned empty result")
            raise HTTPException(status_code=500, detail="Translation failed")

        # 3. TTS
        print("🔊 Generating TTS...")
        audio_content = sarvam_service.text_to_speech(translated_text, target_language=target_lang)
        
        if not audio_content:
            print("❌ TTS returned empty result")
            raise HTTPException(status_code=500, detail="TTS failed")

        print("✨ All steps complete! Sending response.")
        return {
            "original_text": transcript,
            "translated_text": translated_text,
            "audio_base64": audio_content
        }

    except Exception as e:
        print(f"💥 GLOBAL CRASH: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
