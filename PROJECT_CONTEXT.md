# Project Context: Live Translation Engine

## Overview
A real-time speech-to-speech translation engine for Indian languages.

## Tech Stack
- **Backend:** FastAPI (Python 3.10+) with `asyncio` Task architecture
- **Frontend:** React (TypeScript) + Vite + Glassmorphic CSS
- **AI Models:** Sarvam AI API (Saaras STT, Translate v1, Bulbul TTS)
- **Local AI Edge:** Silero V5 Neural VAD via WebAssembly
- **Real-time Engine:** Custom persistent WebSockets with Exponential Backoff

## Core Architecture
1. **Zero-Touch Capture**: Browser-side neural network automatically detects speech boundaries.
2. **Buffer Guards**: Hard limits on backend PCM chunk buffering to prevent OOM errors.
3. **Tuple Grouping**: Listeners are grouped in O(1) dictionary by `(TargetLanguage, VoicePreference)` to minimize API translations.
4. **Audio Queuing**: Frontend guarantees sequential HTML5 Audio playback via `onended` events to prevent TTS overlaps.
5. **End-to-End Telemetry**: Time profiling injected from backend to frontend to display real-time latency.

## Cache Layer (Phase 5 — added 2026-05-05)
- `app/core/cache.py` — `CacheService` singleton
- **Level 1**: `cachetools.LRUCache` — in-memory, microsecond access (512 slots translation / 128 slots TTS)
- **Level 2**: MongoDB via `motor` async driver — persistent across restarts, auto-expiring TTL indexes
- **Key**: `SHA-256(normalize(text) + src_lang + target_lang)` for translation; `SHA-256(translated_text + target_lang + voice)` for TTS
- **Normalization pipeline**: lowercase → trim → strip punctuation → collapse spaces
- **Guards**: Only cache text ≤ 200 chars; TTS audio only if ≤ 100 KB base64

## Admin Endpoints (new)
- `GET  /api/v1/cache/metrics` — hit/miss rates and estimated ₹ saved
- `DELETE /api/v1/cache?lang=mr-IN` — invalidate cache (per-language or full purge)

## Current Status
- [x] Phase 1: Core AI Pipeline (Walkie-Talkie)
- [x] Phase 2: One-to-Many Broadcasting (WebSockets)
- [x] Phase 3: Hands-Free Auto-Segmentation (Silero VAD)
- [x] Phase 4: Resilience & Production Polish (Queues, Telemetry, Voice Selection)
- [x] Phase 5: Cost Optimization (Two-Level Translation & TTS Cache)
