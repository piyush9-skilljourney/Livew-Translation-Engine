# 🏗️ BhashaCast: System Architecture Report

This report provides a detailed map of how, what, and where each component is implemented in the Live Translation Engine.

---

## 🎨 Frontend (React + Vite)

### 1. `frontend/src/main.tsx` (The Entry Point)
- **Role**: Initializes the React application.
- **Key Implementation**: We explicitly removed `StrictMode` here to prevent double-initialization of the heavy AI/WASM engines in development.

### 2. `frontend/src/App.tsx` (The Core Engine)
This is the "Brain" of the frontend. It manages three major systems:
- **VAD Logic**: Uses `@ricky0123/vad-react` to run the Silero V5 neural network. It's memoized via `useMemo` to prevent memory leaks and "destroy" loops.
- **WebSocket System**: Manages persistent connections to `/ws/speaker` or `/ws/listener`. It implements **Exponential Backoff Reconnection** to recover from network drops.
- **Audio Capture & Queue**: Implements a `floatTo16BitPCM` utility and a **Listener Audio Queue**. The queue ensures that rapid incoming translations play sequentially using `onended` events, preventing audio overlap.
- **Telemetry Display**: Calculates and displays real-time end-to-end latency using timestamps passed through the WebSocket.

### 3. `frontend/src/App.css` (The Design System)
- **Role**: Implements the "Premium Studio" aesthetic.
- **Key Features**: 
  - **Glassmorphism**: Uses `backdrop-filter: blur()` and semi-transparent surfaces.
  - **Branding**: Uses CSS gradients to solve visibility issues for the "BhashaCast" title.
  - **Animations**: CSS keyframes for the "Live" pulse and the blue voice visualizer.

### 4. `frontend/public/` (The AI Asset Store)
- **Role**: Serves static binaries that cannot be processed by Vite.
- **Contents**:
  - `*.onnx`: The neural network models for voice detection.
  - `*.wasm`: The WebAssembly binaries that allow ONNX to run at near-native speed in the browser.
  - `*.mjs`: The Javascript glue code for the ONNX runtime.

---

## ⚙️ Backend (FastAPI)

### 1. `backend/app/main.py` (The Server Host)
- **Role**: Configures the FastAPI app, CORS settings, and includes the WebSocket routers.
- **State Management**: Maintains the `active_listeners` global set to track who is currently tuned in.

- **`/ws/speaker`**: Receives raw PCM chunks. Includes a **Buffer Growth Guard** (`MAX_BUFFER_CHUNKS`) to prevent memory leaks by forcing transcription if the speaker exceeds 15 seconds without a pause.
- **`/ws/listener`**: Subscribes a user to the broadcast stream. It uses **(Language + Voice) Grouping** to ensure efficient API utilization while respecting individual voice preferences (e.g., Male `aditya` vs Female `ritu`).

### 3. `backend/app/services/sarvam.py` (The AI Orchestrator)
- **STT (Speech-to-Text)**: Sends PCM data to Sarvam's REST API.
- **Translation**: Converts the transcription into the target language.
- **TTS (Text-to-Speech)**: Generates the audio response.
- **Optimization**: All these calls are wrapped in `run_in_executor` to prevent blocking the async event loop.

### 4. `backend/app/services/audio.py` (The Audio Lab)
- **Resampling**: Uses `scipy.signal.resample_poly` to convert audio between 22050Hz (Sarvam TTS) and 16000Hz (Sarvam STT).
- **WAV Handling**: Adds the required 44-byte headers to raw PCM data so it can be played by the browser's `<audio>` tag.

---

## 📚 Libraries & Frameworks

### Frontend Libraries:
- **`@ricky0123/vad-react`**: Provides the hook-based interface for voice activity detection.
- **`onnxruntime-web`**: The engine that executes machine learning models in the browser.
- **`lucide-react`**: Used for the professional iconography (Mic, Zap, Radio, etc.).

### Backend Libraries:
- **`fastapi[all]`**: The high-performance web framework.
- **`websockets`**: Handles the low-level full-duplex communication.
- **`scipy`**: Handles complex audio resampling without the deprecated `audioop` module.
- **`python-dotenv`**: Manages the Sarvam API keys and environment variables.

---

## 🗺️ Execution Flow (Data Journey)
1. **Frontend**: Mic → VAD (Neural Check) → PCM 16-bit Conversion → WebSocket [with Timestamp].
2. **Backend**: WebSocket → Buffer → [Guard Check / Flush Signal] → Sarvam STT.
3. **Coalescing (Optimization)**: 1.2s delay buffer merges short transcripts into single sentences to reduce TTS frequency.
4. **Skip Logic (Optimization)**: If `source_lang == target_lang`, skip translation/TTS entirely.
5. **Cache Check 1**: Normalize transcript → check Translation Cache (RAM → MongoDB).

   - **HIT**: Skip Sarvam Translate entirely. Latency: ~1ms. Cost: ₹0.
   - **MISS**: Call Sarvam Translate API → write result to cache.
4. **Cache Check 2**: Check TTS Cache (RAM → MongoDB) using `(translated_text, lang, voice)`.
   - **HIT**: Skip Bulbul TTS entirely. Latency: ~1ms. Cost: ₹0.
   - **MISS**: Call Bulbul TTS API → write result to cache (if audio ≤ 100KB).
5. **Broadcast**: Backend → Group by (Language, Voice) → Profile Latency → Send to all Listeners in group.
6. **Listener**: WebSocket → Queue Received Audio → Sequential Playback → Display Latency Badge.

---

## 🗄️ Cache Layer (Phase 5 Addition)

### `backend/app/core/cache.py`
- **`normalize_text(text)`**: Produces canonical form for cache key stability.
- **`make_key(*parts)`**: SHA-256 hash of `|`-joined parts for compact, deterministic keys.
- **`CacheMetrics`**: In-memory counters for hits, misses, and estimated ₹ saved (session-scoped).
- **`CacheService`**:
  - `startup()` / `shutdown()` — lifecycle managed by FastAPI `lifespan` context.
  - `get_translation()` / `set_translation()` — L1 (LRU 512) → L2 (MongoDB, TTL 7d).
  - `get_tts()` / `set_tts()` — L1 (LRU 128) → L2 (MongoDB, TTL 3d, size-guarded).
  - `purge(lang=None)` — clears RAM cache and MongoDB entries (per-language or all).

### MongoDB Collections
| Collection | Key Schema | TTL |
|---|---|---|
| `translation_cache` | `SHA-256(normalized_text\|src_lang\|target_lang)` | 7 days |
| `tts_cache` | `SHA-256(translated_text\|target_lang\|voice)` | 3 days |

### New Admin REST Endpoints
| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/v1/cache/metrics` | Hit/miss rates and ₹ saved |
| `DELETE` | `/api/v1/cache?lang=mr-IN` | Manual cache invalidation |

---

## 📚 Libraries & Frameworks

### Frontend Libraries:
- **`@ricky0123/vad-react`**: Provides the hook-based interface for voice activity detection.
- **`onnxruntime-web`**: The engine that executes machine learning models in the browser.
- **`lucide-react`**: Used for the professional iconography (Mic, Zap, Radio, etc.).

### Backend Libraries:
- **`fastapi[all]`**: The high-performance web framework.
- **`websockets`**: Handles the low-level full-duplex communication.
- **`motor`**: Async MongoDB driver — used for the persistent cache layer.
- **`cachetools`**: Provides the `LRUCache` implementation for the in-memory cache layer.
- **`scipy`**: Handles complex audio resampling without the deprecated `audioop` module.
- **`python-dotenv`**: Manages the Sarvam API keys and environment variables.

