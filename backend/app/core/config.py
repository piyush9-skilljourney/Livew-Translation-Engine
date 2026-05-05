import os
import logging
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"), override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Live Translation Engine"
    MONGODB_URL: str = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
    DATABASE_NAME: str = os.getenv("DATABASE_NAME", "translation_engine")
    SARVAM_API_KEY: str = os.getenv("SARVAM_API_KEY", "")

    # ── Cache Policies ─────────────────────────────────────────────────────────
    CACHE_TRANSLATION_TTL_DAYS: int = 7      # How long to keep translations in MongoDB
    CACHE_TTS_TTL_DAYS: int = 3              # How long to keep TTS audio in MongoDB
    CACHE_MAX_TEXT_LENGTH: int = 200         # Skip caching if text > 200 chars
    CACHE_TTS_MAX_B64_BYTES: int = 204800    # Skip caching TTS audio > 200KB (base64)


settings = Settings()

# ── Startup Validation ─────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

if not settings.SARVAM_API_KEY:
    logger.warning("SARVAM_API_KEY is not set in .env — AI features will be disabled.")
else:
    logger.info(f"SARVAM_API_KEY loaded (starts with: {settings.SARVAM_API_KEY[:5]}...)")
