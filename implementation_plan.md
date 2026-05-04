# Implementation Plan: BhashaCast (Live Translation Engine)

## 🚀 Roadmap Overview

---

### ✅ Phase 1: Core AI Pipeline (COMPLETED — 2026-05-04)
- Functional STT → Translation → TTS loop established via Sarvam AI.
- Single-user Walkie-Talkie style (record → POST → play response).
- Glassmorphic React UI built and verified.

---

### ✅ Phase 2: Push-to-Talk Broadcast (COMPLETED — 2026-05-04)
- **Goal:** Speaker holds a button, Listeners hear the translation live.

**Achieved:**
- [x] Role-selection screen (Speaker / Listener)
- [x] Dedicated WebSocket endpoints: `/ws/speaker` and `/ws/listener`
- [x] One-to-Many broadcast relay via `active_listeners` set
- [x] PCM audio capture at 16kHz via `AudioContext` + `ScriptProcessorNode`
- [x] Push-to-Talk: buffer PCM on button hold, flush on button release
- [x] Batch STT via Sarvam REST API (streaming WebSocket non-functional)
- [x] Async translation + TTS via `run_in_executor` (non-blocking)
- [x] Marathi audio + subtitle broadcast to all Listeners
- [x] Speaker receives live Hindi transcription feedback

**Known Limitations:**
- 3–5 second latency per utterance (batch pipeline)
- Speaker must hold a button (not hands-free)
- `ScriptProcessorNode` is deprecated (Chrome warning)
- Sarvam Streaming STT WebSocket is non-functional (documented in RND_REPORT.md)

---

### 🌟 Phase 2.5: BhashaCast Upgrades (COMPLETED)
- **Goal:** Enhance the user experience with more language control and better naming.
- [x] Renamed app to **BhashaCast**.
- [x] Speaker Language Selection (Gujarati, Hindi, etc.) passed dynamically to STT.
- [x] Addressed "Hinglish/Marathinglish" (Conversational code-mixing requires LLMs; Sarvam standardizes to pure scripts, but Sarvam TTS handles English gracefully).

---

### 🔄 Phase 3: Auto-Segmenting Broadcast (PLANNED)
- **Goal:** Zero-button, continuous translation *without* needing Deepgram.
- Replace manual button with browser-side VAD (`@ricky0123/vad-web`).
- **Auto-Segmentation:** VAD detects speech pause -> sends audio -> triggers STT.
- Replace `ScriptProcessorNode` with `AudioWorkletNode`.
- This provides a "walkie-talkie" feel but completely hands-free.

**Architecture:**
```
Mic → AudioWorklet + VAD → [Speech detected] → Collect PCM
[Pause detected] → Send PCM to FastAPI /ws/speaker
                 → Sarvam Batch STT
                 → Sarvam Translate → Sarvam TTS
                 → Broadcast to /ws/listener × N
```


---

### 📡 Phase 4: Production & Scale (FUTURE)
- Multi-language Listener support (each Listener chooses their language)
- Room-based sessions (Speaker creates a room, Listeners join via code)
- LiveKit integration for scalable WebRTC distribution
- Authentication & Authorization
- Production Deployment (Docker + Cloud Run)
