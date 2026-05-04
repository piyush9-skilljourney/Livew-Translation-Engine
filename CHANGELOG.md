# Changelog & Progress Log

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
