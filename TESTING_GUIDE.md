# 🧪 Phase 5 Testing Guide — Translation & TTS Cache

This guide walks you through verifying every aspect of the caching system step by step.

---

## Prerequisites

Make sure you have:
- [ ] Backend server running: `uvicorn app.main:app --reload` (from `/backend` folder)
- [ ] MongoDB running locally (`mongodb://localhost:27017`) OR connected to Atlas
- [ ] Sarvam API key set in `backend/.env`
- [ ] A REST client (browser, curl, or Postman)

---

## Step 1 — Verify the Server Starts Cleanly

Run the server and check the logs for these exact lines:

```powershell
cd "D:\Projects\FastAPI\Live Translation Engine\backend"
.\venv\Scripts\uvicorn app.main:app --reload --port 8000
```

**Expected log output (in order):**
```
HH:MM:SS | INFO | app.core.config     | SARVAM_API_KEY loaded (starts with: sk_qt...)
HH:MM:SS | INFO | app.core.cache      | [CACHE] CacheService initialized ...
HH:MM:SS | INFO | app.services.sarvam | SarvamAI client initialized successfully.
HH:MM:SS | INFO | app.main            | 🚀 BhashaCast starting up...
HH:MM:SS | INFO | app.core.cache      | [CACHE] MongoDB connected and TTL indexes ensured.
```

> [!IMPORTANT]
> If you see `MongoDB connection failed`, check that MongoDB is running.
> The server will still work — it just falls back to RAM-only mode (L1 cache only).

---

## Step 2 — Verify Health Endpoint

```
GET http://localhost:8000/
```

**Expected response:**
```json
{
  "status": "running",
  "service": "Live Translation Engine",
  "active_listeners": 0
}
```

---

## Step 3 — Test Normalization (Unit Test)

Run this one-liner to verify the normalization pipeline:

```powershell
cd "D:\Projects\FastAPI\Live Translation Engine\backend"
.\venv\Scripts\python -c "
from app.core.cache import normalize_text, make_key

# Test 1: Normalization
tests = [
    ' Hello!!  How are you? ',
    'hello how are you',
    'HELLO HOW ARE YOU??',
    '  hello   how   are   you  ',
]
results = [normalize_text(t) for t in tests]
assert all(r == 'hello how are you' for r in results), 'FAIL: Normalization mismatch'
print('✅ Test 1 PASSED: All variants normalize to the same key')

# Test 2: Key stability
k1 = make_key('hello how are you', 'hi-IN', 'mr-IN')
k2 = make_key('hello how are you', 'hi-IN', 'mr-IN')
assert k1 == k2, 'FAIL: Key is not deterministic'
print('✅ Test 2 PASSED: SHA-256 key is deterministic')

# Test 3: Key uniqueness (different voice = different key)
k_male   = make_key('hello', 'mr-IN', 'aditya')
k_female = make_key('hello', 'mr-IN', 'ritu')
assert k_male != k_female, 'FAIL: Male and Female keys collided'
print('✅ Test 3 PASSED: Male and Female TTS keys are different')
"
```

**Expected output:**
```
✅ Test 1 PASSED: All variants normalize to the same key
✅ Test 2 PASSED: SHA-256 key is deterministic
✅ Test 3 PASSED: Male and Female TTS keys are different
```

---

## Step 4 — Test Cache Metrics Endpoint (Empty State)

```
GET http://localhost:8000/api/v1/cache/metrics
```

**Expected response (fresh start):**
```json
{
  "translation": { "hits": 0, "misses": 0, "hit_rate": 0.0 },
  "tts":         { "hits": 0, "misses": 0, "hit_rate": 0.0 },
  "total_api_calls_saved": 0,
  "estimated_inr_saved": 0.0
}
```

---

## Step 5 — Test Cache Miss (First Call)

Use the REST endpoint to send an audio file for translation:

```
POST http://localhost:8000/api/v1/translate-audio
Body: form-data
  file: [upload backend/test_speech.wav or backend/test_stt.wav]
  target_lang: mr-IN
  voice: aditya
```

**Expected response:**
```json
{
  "original_text":    "...",
  "translated_text":  "...",
  "audio_base64":     "...",
  "translate_cached": false,
  "tts_cached":       false
}
```

**Expected log lines:**
```
[Translate] MISS → API call (X.XXs) | mr-IN: ...
[TTS] MISS → API call (X.XXs) | mr-IN-aditya
```

---

## Step 6 — Test Cache Hit (Second Call — Same File)

Send the **exact same request again** immediately:

```
POST http://localhost:8000/api/v1/translate-audio
[same file, same params]
```

**Expected response:**
```json
{
  "translate_cached": true,
  "tts_cached":       true
}
```

**Expected log lines:**
```
[Translate] HIT  → cache | mr-IN: ...
[TTS] HIT  → cache | mr-IN-aditya
```

> [!TIP]
> The second response should be noticeably faster — no API round-trip.

---

## Step 7 — Verify Metrics Updated

```
GET http://localhost:8000/api/v1/cache/metrics
```

**Expected response (after Step 5 + 6):**
```json
{
  "translation": { "hits": 1, "misses": 1, "hit_rate": 0.5 },
  "tts":         { "hits": 1, "misses": 1, "hit_rate": 0.5 },
  "total_api_calls_saved": 2,
  "estimated_inr_saved": 0.25
}
```

---

## Step 8 — Test Cache Purge (Per-Language)

```
DELETE http://localhost:8000/api/v1/cache?lang=mr-IN
```

**Expected response:**
```json
{
  "purged": {
    "translation_deleted": 1,
    "tts_deleted": 1,
    "ram_cleared": false
  }
}
```

Now repeat Step 5 — the response should show `translate_cached: false` again (cache was purged).

---

## Step 9 — Test Full Purge

```
DELETE http://localhost:8000/api/v1/cache
```

**Expected response:**
```json
{
  "purged": {
    "translation_deleted": 0,
    "tts_deleted": 0,
    "ram_cleared": true
  }
}
```

---

## Step 10 — End-to-End WebSocket Test (Live Flow)

1. Open the frontend: `http://localhost:5173`
2. Open **two browser tabs**.
3. **Tab 1**: Choose "Broadcast Studio" (Speaker) — language: Hindi.
4. **Tab 2**: Choose "Join as Listener" — language: Marathi, Voice: Male.
5. In Tab 1, speak a short phrase (e.g., "Namaste").
6. Check the backend logs for:
   ```
   [Translate] MISS → API call ...
   [TTS] MISS → API call ...
   🚀 Broadcasting to 1 listener(s) | mr-IN-aditya | translate=MISS | tts=MISS
   ```
7. Say the **same phrase again**.
8. Check the backend logs:
   ```
   [Translate] HIT  → cache | mr-IN: ...
   [TTS] HIT  → cache | mr-IN-aditya
   🚀 Broadcasting to 1 listener(s) | mr-IN-aditya | translate=HIT | tts=HIT
   ```
9. The listener should **hear the same translated audio** — but the second time arrives much faster.

---

## Step 11 — MongoDB Persistence Test

1. Run Steps 5–6 to populate the cache.
2. **Stop the server** (Ctrl+C).
3. **Restart the server**.
4. Send the same file again (Step 5).
5. The response should show `translate_cached: true, tts_cached: true` — loaded from MongoDB.

> [!NOTE]
> If MongoDB is NOT running, the server falls back to RAM-only mode.
> On restart, the RAM cache will be empty and you'll see cache misses again.

---

## Step 12 — Guard Tests

### 12a: Long Text (Should NOT be cached)
Send a WAV file where the speaker says a very long sentence (> 200 characters in transcript).
- The logs should show `[Translate] MISS` twice — the second call is also a MISS because the text was too long to cache.

### 12b: Check Metrics Endpoint via Browser
Navigate to: `http://localhost:8000/api/v1/cache/metrics`
You should see a live JSON response in the browser.

---

## ✅ Test Checklist Summary

| # | Test | Expected Result |
|---|---|---|
| 1 | Server startup logs | MongoDB connected, no errors |
| 2 | `GET /` | `status: running` |
| 3 | Normalization unit test | All 3 assertions pass |
| 4 | Metrics (empty) | All zeros |
| 5 | First `/translate-audio` | `translate_cached: false, tts_cached: false` |
| 6 | Second `/translate-audio` | `translate_cached: true, tts_cached: true` |
| 7 | Metrics (after 5+6) | hits=1, misses=1 each |
| 8 | Purge `?lang=mr-IN` | Deleted count > 0 |
| 9 | Purge all | `ram_cleared: true` |
| 10 | Live WebSocket test | Second phrase logs HIT for both |
| 11 | Persistence test | Cached after restart |
| 12a | Long text guard | Not cached (miss twice) |
| 12b | Metrics in browser | JSON visible |
