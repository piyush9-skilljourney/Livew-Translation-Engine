import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

# DIAGNOSTIC PRINTS
env_path = os.path.join(os.getcwd(), ".env")
print(f"🔍 DEBUG: Looking for .env at: {env_path}")
print(f"🔍 DEBUG: File exists? {os.path.exists(env_path)}")

load_dotenv(env_path, override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Live Translation Engine"
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "translation_engine")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")

settings = Settings()
print(f"🔍 DEBUG: Key loaded? {'YES' if settings.SARVAM_API_KEY else 'NO'}")
if settings.SARVAM_API_KEY:
    print(f"🔍 DEBUG: Key starts with: {settings.SARVAM_API_KEY[:5]}...")
