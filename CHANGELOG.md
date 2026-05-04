# Changelog & Progress Log

## [Phase 4] - Resilience & Production Polish — 2026-05-04

### ✅ Achieved
- **Listener Audio Queue**: Implemented sequential audio playback queue to prevent simultaneous overlapping translations.
- **WebSocket Reconnection**: Added exponential backoff reconnect logic for dropped network connections.
- **Buffer Growth Guard**: Hard-capped backend PCM buffer to 300 chunks (~15s) to prevent OOM memory leaks.
- **Voice Selection**: Implemented dual-voice grouping (Language + Voice). Used 'aditya' (Male) and 'anushka' (Female) Sarvam v3 voices.
- **Latency Telemetry**: Added `time.perf_counter()` to backend for precise STT/Translate/TTS logs, and E2E latency UI indicator.
- Updated project architecture documentation.

---

## [Phase 3] - Hands-Free Broadcast (VAD) — 2026-05-04

### ✅ Achieved
- Integrated local Voice Activity Detection (`@ricky0123/vad-react`) via Silero V5 neural network.
- Automated speech boundary detection (auto-clipping) for hands-free broadcasting.
- Created robust "Public Asset Store" to bypass Vite's HMR corrupting WASM/ONNX model loading.
- Fixed React 18 `StrictMode` double-mount issue destroying the VAD lifecycle.
- Overhauled UI to "Premium Studio" aesthetic (Dark mode, glassmorphism, Google Fonts).

---

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
