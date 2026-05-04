# Project Context: Live Translation Engine

## Overview
A real-time speech-to-speech translation engine for Indian languages.

## Tech Stack
- **Backend:** FastAPI (Python 3.10+)
- **Frontend:** React (TypeScript) + Vite
- **Database:** MongoDB
- **AI Models:** Sarvam AI (Saaras, Bulbul, Mayura)
- **Real-time Media:** LiveKit

## Core Goals
1. Low-latency one-way audio translation (Speaker -> Multiple Listeners).
2. Skip video (as per manager feedback).
3. One-to-many listener support for a single target language.
4. Live subtitles for translated audio.

## Current Status
- [x] Phase 1: Core AI Pipeline (REST/Batch)
- [x] Phase 2: Push-to-Talk Broadcast (WebSockets)
- [x] Phase 3: Hands-Free Auto-Segment (Silero VAD)
- [x] Phase 4: Production Resilience & Polish (Queues, Latency, Voices)
- [ ] Phase 5: Distribution & Scale (LiveKit / Multi-room) - *Future*
