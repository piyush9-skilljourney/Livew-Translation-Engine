"""
cache.py — Two-Level Translation & TTS Cache
============================================
Level 1: In-memory LRU cache (cachetools) — microsecond access
Level 2: MongoDB (motor async driver)     — persistent, survives restarts

Cache Keys (SHA-256):
  Translation: normalize(text) + src_lang + target_lang
  TTS:         translated_text + target_lang + voice

Policies:
  - Only cache if len(text) <= CACHE_MAX_TEXT_LENGTH
  - Only cache TTS audio if base64 size <= CACHE_TTS_MAX_B64_BYTES
  - MongoDB TTL index auto-expires documents
"""

import hashlib
import logging
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from cachetools import LRUCache
from motor.motor_asyncio import AsyncIOMotorClient

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Normalization ──────────────────────────────────────────────────────────────

def normalize_text(text: str) -> str:
    """
    Full normalization pipeline for stable cache keys.
    'Hello!!  How are you?' → 'hello how are you'
    """
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)   # strip punctuation
    text = re.sub(r"\s+", " ", text)       # collapse spaces
    return text.strip()


def make_key(*parts: str) -> str:
    """Build a deterministic SHA-256 cache key from string parts."""
    raw = "|".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ── Metrics Counters ───────────────────────────────────────────────────────────

class CacheMetrics:
    def __init__(self):
        self.translation_hits   = 0
        self.translation_misses = 0
        self.tts_hits           = 0
        self.tts_misses         = 0

    # Approximate cost rates (₹ per unit) derived from your analytics:
    # Cost estimation based on FREE PLAN
    # Translate: ₹2.0 / 1k chars | TTS: ₹3.0 / 1k chars
    _TRANSLATE_RATE = 0.002   
    _TTS_RATE       = 0.003   
    _PLAN_NAME      = "Sarvam AI Free"



    def record_translation_hit(self, text_len: int):
        self.translation_hits += 1
        logger.debug(f"[CACHE] Translation HIT (saved ~₹{text_len * self._TRANSLATE_RATE:.4f})")

    def record_translation_miss(self):
        self.translation_misses += 1

    def record_tts_hit(self, text_len: int):
        self.tts_hits += 1
        logger.debug(f"[CACHE] TTS HIT (saved ~₹{text_len * self._TTS_RATE:.4f})")

    def record_tts_miss(self):
        self.tts_misses += 1

    def to_dict(self) -> dict:
        total_translation_chars_saved = 0  # We don't track per-hit char counts in-memory for simplicity
        return {
            "translation": {
                "hits":   self.translation_hits,
                "misses": self.translation_misses,
                "hit_rate": round(
                    self.translation_hits / max(1, self.translation_hits + self.translation_misses), 3
                ),
            },
            "tts": {
                "hits":   self.tts_hits,
                "misses": self.tts_misses,
                "hit_rate": round(
                    self.tts_hits / max(1, self.tts_hits + self.tts_misses), 3
                ),
            },
            "total_api_calls_saved": self.translation_hits + self.tts_hits,
            "estimated_inr_saved": round(
                self.translation_hits * 50 * self._TRANSLATE_RATE
                + self.tts_hits * 50 * self._TTS_RATE,
                4,
            ),
            "plan_metadata": {
                "name": self._PLAN_NAME,
                "credits_total": 0,
                "rate_limit": "60 req/min"
            }

        }


# ── Cache Service ──────────────────────────────────────────────────────────────

class CacheService:
    # Collection names in MongoDB
    _TRANSLATION_COL = "translation_cache"
    _TTS_COL         = "tts_cache"

    def __init__(self):
        # Level 1: RAM LRU caches
        self._translation_lru: LRUCache = LRUCache(maxsize=512)
        self._tts_lru:         LRUCache = LRUCache(maxsize=128)

        # Level 2: MongoDB (initialized lazily via startup event)
        self._mongo_client: Optional[AsyncIOMotorClient] = None
        self._db = None

        self.metrics = CacheMetrics()
        logger.info("[CACHE] CacheService initialized (MongoDB connection deferred to startup).")

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    async def startup(self):
        """Connect to MongoDB and ensure TTL indexes exist. Call from app lifespan."""
        try:
            self._mongo_client = AsyncIOMotorClient(settings.MONGODB_URL)
            self._db = self._mongo_client[settings.DATABASE_NAME]

            # Ensure TTL indexes (idempotent — safe to call on every startup)
            await self._db[self._TRANSLATION_COL].create_index(
                "expires_at", expireAfterSeconds=0
            )
            await self._db[self._TTS_COL].create_index(
                "expires_at", expireAfterSeconds=0
            )
            logger.info("[CACHE] MongoDB connected and TTL indexes ensured.")
        except Exception as e:
            logger.error(f"[CACHE] MongoDB connection failed: {e}. Will run on RAM-only mode.")
            self._db = None

    async def shutdown(self):
        """Gracefully close the MongoDB connection."""
        if self._mongo_client:
            self._mongo_client.close()
            logger.info("[CACHE] MongoDB connection closed.")

    def _is_cacheable_text(self, text: str) -> bool:
        """Guard: only cache short, non-empty text."""
        return bool(text) and len(text) <= settings.CACHE_MAX_TEXT_LENGTH

    def _is_cacheable_audio(self, audio_b64: str) -> bool:
        """Guard: only cache audio that is within our size budget."""
        return bool(audio_b64) and len(audio_b64.encode("utf-8")) <= settings.CACHE_TTS_MAX_B64_BYTES

    # ── Translation Cache ──────────────────────────────────────────────────────

    async def get_translation(
        self, text: str, src_lang: str, target_lang: str
    ) -> Optional[str]:
        if not self._is_cacheable_text(text):
            return None

        key = make_key(normalize_text(text), src_lang, target_lang)

        # L1: RAM
        if key in self._translation_lru:
            self.metrics.record_translation_hit(len(text))
            return self._translation_lru[key]

        # L2: MongoDB
        if self._db is not None:
            try:
                doc = await self._db[self._TRANSLATION_COL].find_one({"_id": key})
                if doc:
                    self._translation_lru[key] = doc["translated_text"]  # warm L1
                    self.metrics.record_translation_hit(len(text))
                    return doc["translated_text"]
            except Exception as e:
                logger.warning(f"[CACHE] MongoDB read error (translation): {e}")

        self.metrics.record_translation_miss()
        return None

    async def set_translation(
        self, text: str, src_lang: str, target_lang: str, translated_text: str
    ):
        if not self._is_cacheable_text(text) or not translated_text:
            return

        key = make_key(normalize_text(text), src_lang, target_lang)

        # L1: RAM
        self._translation_lru[key] = translated_text

        # L2: MongoDB
        if self._db is not None:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(days=settings.CACHE_TRANSLATION_TTL_DAYS)
                await self._db[self._TRANSLATION_COL].update_one(
                    {"_id": key},
                    {"$set": {
                        "_id": key,
                        "translated_text": translated_text,
                        "src_lang": src_lang,
                        "target_lang": target_lang,
                        "original_text": text[:50],  # store snippet for debugging
                        "expires_at": expires_at,
                        "updated_at": datetime.now(timezone.utc),
                    }},
                    upsert=True,
                )
            except Exception as e:
                logger.warning(f"[CACHE] MongoDB write error (translation): {e}")

    # ── TTS Cache ──────────────────────────────────────────────────────────────

    async def get_tts(
        self, translated_text: str, target_lang: str, voice: str
    ) -> Optional[str]:
        if not self._is_cacheable_text(translated_text):
            return None

        key = make_key(translated_text, target_lang, voice)

        # L1: RAM
        if key in self._tts_lru:
            self.metrics.record_tts_hit(len(translated_text))
            return self._tts_lru[key]

        # L2: MongoDB
        if self._db is not None:
            try:
                doc = await self._db[self._TTS_COL].find_one({"_id": key})
                if doc:
                    self._tts_lru[key] = doc["audio_b64"]  # warm L1
                    self.metrics.record_tts_hit(len(translated_text))
                    return doc["audio_b64"]
            except Exception as e:
                logger.warning(f"[CACHE] MongoDB read error (tts): {e}")

        self.metrics.record_tts_miss()
        return None

    async def set_tts(
        self, translated_text: str, target_lang: str, voice: str, audio_b64: str
    ):
        if not self._is_cacheable_text(translated_text) or not self._is_cacheable_audio(audio_b64):
            return

        key = make_key(translated_text, target_lang, voice)

        # L1: RAM
        self._tts_lru[key] = audio_b64

        # L2: MongoDB
        if self._db is not None:
            try:
                expires_at = datetime.now(timezone.utc) + timedelta(days=settings.CACHE_TTS_TTL_DAYS)
                await self._db[self._TTS_COL].update_one(
                    {"_id": key},
                    {"$set": {
                        "_id": key,
                        "audio_b64": audio_b64,
                        "target_lang": target_lang,
                        "voice": voice,
                        "text_snippet": translated_text[:50],  # for debugging
                        "expires_at": expires_at,
                        "updated_at": datetime.now(timezone.utc),
                    }},
                    upsert=True,
                )
            except Exception as e:
                logger.warning(f"[CACHE] MongoDB write error (tts): {e}")

    # ── Purge ──────────────────────────────────────────────────────────────────

    async def purge(self, lang: Optional[str] = None) -> dict:
        """
        Manual cache invalidation.
        - lang=None  → purge everything
        - lang='mr-IN' → purge only that language's TTS and translation entries
        """
        result = {"translation_deleted": 0, "tts_deleted": 0, "ram_cleared": False}

        # Always clear RAM LRU — it's cheap and guarantees consistency
        if lang is None:
            self._translation_lru.clear()
            self._tts_lru.clear()
            result["ram_cleared"] = True

        if self._db is not None:
            try:
                query = {"target_lang": lang} if lang else {}
                t_del = await self._db[self._TRANSLATION_COL].delete_many(query)
                tts_del = await self._db[self._TTS_COL].delete_many(query)
                result["translation_deleted"] = t_del.deleted_count
                result["tts_deleted"] = tts_del.deleted_count
                logger.info(f"[CACHE] Purge complete: {result}")
            except Exception as e:
                logger.error(f"[CACHE] Purge failed: {e}")

        return result


# ── Singleton ──────────────────────────────────────────────────────────────────
cache_service = CacheService()
