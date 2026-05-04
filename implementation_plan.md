# Implementation Plan: Live Translation Engine

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

### 🔄 Phase 3: True Live Streaming (PLANNED)
- **Goal:** Zero-button, continuous translation like YouTube Live.
- Replace `ScriptProcessorNode` with `AudioWorkletNode`
- Replace Sarvam Streaming STT with Deepgram Nova-2 (proven streaming STT)
- Implement browser-side VAD (`@ricky0123/vad-web`) to auto-detect speech
- Translate at sentence-boundary level for low latency
- Target latency: **1–2 seconds**

**Architecture:**
```
Mic → AudioWorklet → FastAPI /ws/speaker → Deepgram STT (streaming)
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
