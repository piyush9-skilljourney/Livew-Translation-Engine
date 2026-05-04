# Testing Guide: Live Translation Engine

This document provides step-by-step instructions to verify the functionality of each phase of the project.

---

## 🧪 Phase 1: Core AI Engine (Walkie-Talkie)
**Goal:** Verify the base Speech-to-Text -> Translation -> Text-to-Speech pipeline.

### 1. Prerequisites
- [ ] Valid `SARVAM_API_KEY` in `backend/.env`.
- [ ] Backend running on `http://localhost:8000`.
- [ ] Frontend running on `http://localhost:5173`.

### 2. Test Execution
1.  **Permissions:** Ensure the browser has microphone access.
2.  **Capture:** Click and **hold** the "Hold to Speak" button.
3.  **Input:** Speak a simple Hindi phrase (e.g., *"Aaj ka mausam kaisa hai?"*).
4.  **Process:** Release the button and wait for the "Processing" state to finish.

### 3. Verification Checklist
- [ ] **STT:** Does the "Original (Hindi)" text accurately reflect what you said?
- [ ] **NMT:** Is the "Translated (Marathi)" text a correct translation?
- [ ] **TTS:** Does the audio play automatically?
- [ ] **Voice Quality:** Is the Marathi voice clear and natural sounding?

---

## 🧪 Phase 2: Real-time Streaming (Coming Soon)
*Steps will be added upon implementation.*
