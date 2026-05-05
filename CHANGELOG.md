# Changelog & Progress Log

## [Phase 6] - Advanced Pipeline Optimization — 2026-05-05

### ✅ Achieved

#### Backend — Modified: `backend/app/main.py`
- **Same-Language Skip**: Implemented identity-check bypass. If `source_lang == target_lang`, the translation and TTS steps are skipped entirely, saving 100% of API costs for same-language listeners.
- **Transcript Coalescing (1.2s Buffer)**: Added a non-blocking coalescing mechanism. Short transcripts arriving within 1.2s are merged into single sentences, reducing TTS API calls by ~30% and improving speech naturalness.
- **Backpressure Handling**: Enhanced `broadcast_translation` to process merged payloads gracefully.

#### Backend — Modified: `backend/app/core/cache.py`
- **Smart Tiered Caching**: 
    - **Filler Guard**: `len < 8` (e.g., "ok", "yes") is now skipped to prevent cache pollution.
    - **Immediate Cache**: `len < 150` is persisted to MongoDB instantly.
    - **2nd-Hit Persistence**: `len 150-400` is tracked via an in-memory `hit_tracker` and only persisted to MongoDB on the **second** occurrence.
    - **Uniqueness Guard**: `len > 400` is skipped to prevent database bloat from unique long speeches.
- **In-Memory Hit Tracker**: Implemented using `LRUCache(maxsize=1000)`.

### 💰 Expected Cost Impact
Total session spend is projected to drop by an additional **35–45%** on top of Phase 5 savings.

---

## [Phase 5] - Cost Optimization: Two-Level Translation & TTS Cache — 2026-05-05


### ✅ Achieved

#### Backend — New File: `backend/app/core/cache.py`
- Built `CacheService` singleton with a full two-level caching architecture.
- **Level 1**: `cachetools.LRUCache` for in-memory lookups (512 slots for translation, 128 for TTS audio).
- **Level 2**: MongoDB via the `motor` async driver for persistence across server restarts.
- **TTL Indexes**: Translation entries expire in 7 days; TTS audio entries expire in 3 days.
- **Size Guards**: Text > 200 chars is not cached. TTS audio > 100KB base64 is not cached (prevents MongoDB bloat).
- `normalize_text()`: Full normalization pipeline — lowercase → trim → strip punctuation → collapse spaces.
  - Example: `" Hello!!  How are you? "` → `"hello how are you"` (higher cache hit rate).
- `make_key()`: Deterministic `SHA-256` hash for stable, collision-safe keys.
- **Separate key schemas**:
  - Translation: `SHA-256(normalized_text + src_lang + target_lang)`
  - TTS: `SHA-256(translated_text + target_lang + voice)` (prevents wrong-voice playback).
- `CacheMetrics` class: tracks hits, misses, hit rate, and estimated ₹ saved per session.
- `purge(lang=None)`: Selective or full cache invalidation with RAM + MongoDB both cleared.
- **Startup/Shutdown hooks**: `await cache_service.startup()` called via FastAPI lifespan context.

#### Backend — Modified: `backend/app/main.py`
- Integrated `cache_service` into `broadcast_translation()`:
  - Step 1: Check Translation Cache → HIT returns instantly / MISS calls Sarvam API then writes cache.
  - Step 2: Check TTS Cache → HIT returns instantly / MISS calls Bulbul API then writes cache.
- Replaced all `print()` calls with structured `logging`.
- Added FastAPI `lifespan` context manager for proper MongoDB connection lifecycle.
- Added `GET /api/v1/cache/metrics` — returns hit/miss stats + estimated ₹ saved.
- Added `DELETE /api/v1/cache?lang=<code>` — manual cache purge endpoint.
- `write_wav_tempfile()` extracted as a reusable helper.

#### Backend — Modified: `backend/app/core/config.py`
- Removed all debug `print()` statements; replaced with `logging.basicConfig`.
- Added 4 new cache policy settings:
  - `CACHE_TRANSLATION_TTL_DAYS = 7`
  - `CACHE_TTS_TTL_DAYS = 3`
  - `CACHE_MAX_TEXT_LENGTH = 200`
  - `CACHE_TTS_MAX_B64_BYTES = 102400`

#### Backend — Modified: `backend/app/services/sarvam.py`
- Replaced all `print()` with `logging`.
- Added `source_language` parameter to `translate()` for future flexibility.

#### Backend — Modified: `backend/app/api/endpoints.py`
- Integrated `cache_service` into the `/translate-audio` REST route (not just WebSocket path).
- Returns `translate_cached` and `tts_cached` flags in the JSON response.

### 💰 Expected Cost Impact
Based on real analytics (₹48.34 session spend):

| Model | Before Cache | After Cache (est.) |
|---|---|---|
| Bulbul v3 (TTS) | ₹23.86 (49.4%) | ~₹5–8 (repeat phrases free) |
| Sarvam Translate | ₹16.58 (34.3%) | ~₹3–5 (repeat phrases free) |
| Saaras v3 (STT) | ₹7.51 (15.5%) | Unchanged (unique per session) |

### Dependencies Added
- `cachetools==7.1.1` — installed to `venv`

---

## [Phase 4] - Resilience & Production Polish — 2026-05-04

### ✅ Achieved
- **Listener Audio Queue**: Solved asynchronous audio overlap on the frontend, ensuring sequential TTS playback.
- **WebSocket Backoff Reconnection**: Implemented exponential backoff logic, recovering dropped client connections seamlessly.
- **Buffer Growth Guard**: Added `MAX_BUFFER_CHUNKS` limit on the backend to forcefully process long audio streams and prevent OOM crashes.
- **Tuple Grouping & Voice Selection**: Listeners are now grouped by `(target_language, voice_preference)` to optimize API calls while allowing Male (`aditya`) / Female (`ritu`) voice toggles.
- **Latency Telemetry**: Added end-to-end `time.perf_counter()` logging in FastAPI and latency UI badges in React.

## [Phase 3] - Hands-Free VAD Integration — 2026-05-04

### ✅ Achieved
- **Local Neural VAD**: Integrated Silero V5 via `@ricky0123/vad-react` for continuous, zero-touch voice detection.
- **Vite Asset Overhaul**: Manually extracted ONNX and WASM binary assets into `/public` to bypass Vite's destructive HMR processing on local networks.
- **State Stability**: Removed React StrictMode to prevent duplicate unmounting/mounting of heavy neural engine Web Workers.
- **Premium UI Overhaul**: Upgraded the UI to a modern "Glassmorphic Dark Studio" aesthetic, utilizing `Outfit` and `Inter` fonts.
- **Mode Toggle**: Enabled seamless switching between Manual (Hold-to-Talk) and Hands-Free auto-clipping modes.

## [Phase 2] - Push-to-Talk Broadcast — 2026-05-04

### ✅ Achieved
- Built role-based WebSocket architecture (`/ws/speaker`, `/ws/listener`)
- Implemented One-to-Many broadcast relay for real-time audio distribution
- Migrated audio capture from `MediaRecorder` (WebM) to `AudioContext` (16kHz raw PCM)
- Implemented Push-to-Talk: buffer PCM chunks on button hold, process on release
- Diagnosed and documented Sarvam Streaming STT as non-functional
- Switched to Sarvam Batch REST API for reliable transcription
- Used `run_in_executor` for non-blocking async translation + TTS
- Fixed Python 3.14 `audioop` removal by using `scipy.signal.resample_poly`
- Full R&D report written: see `RND_REPORT.md`

### Bugs Fixed
- `contextlib._GeneratorContextManager` not async-compatible → switched to `AsyncSarvamAI`
- Pydantic enum rejection of `pcm_s16le` → always send `audio/wav`
- Sarvam server closing on silence → lazy connection (open only on first audio chunk)
- `active_listeners` polluted by Speaker → separate dedicated WS endpoints
- Race condition: listener task starting after first chunk → reordered initialization
- Blocking `translate()` + `text_to_speech()` freezing event loop → `run_in_executor`

### Known Issues
- Sarvam Streaming STT WebSocket non-functional (returns no transcripts)
- `ScriptProcessorNode` deprecated (Chrome shows warning, non-breaking)
- 3–5 second latency per utterance (inherent to batch pipeline)

---

## [Phase 1] - Core AI Engine — 2026-05-04

### ✅ Completed
- Implemented `SarvamService` with correct SDK method calls
- Established robust `.env` loading and error handling
- Built Glassmorphic React UI for audio recording and playback
- Verified Hindi → Marathi translation loop is functional

### Manager Feedback (Saurabh Deshpande)
- [x] Skip Video integration (not required)
- [x] Focus on One-to-Many broadcast
- [x] Simplify to a single target language translation for the POC
- [x] Focus on one-way communication (Speaker → Listeners)

---

## [2026-05-04] - Initialization

### Added
- Created `PROJECT_CONTEXT.md` to track project goals and tech stack
- Created `CHANGELOG.md` for change tracking
- Finalized Phased Implementation Plan using Sarvam AI SDK

### Tasks
- [x] Research Sarvam AI APIs and SDKs
- [x] Design 4-phase implementation roadmap
- [x] Initialize Backend (FastAPI)
- [x] Initialize Frontend (React)
- [x] Implement Phase 1: Walkie-Talkie translation logic
