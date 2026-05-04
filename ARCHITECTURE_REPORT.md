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
- **WebSocket System**: Manages persistent connections to `/ws/speaker` or `/ws/listener`. It handles the binary transmission of PCM audio.
- **Audio Capture**: Implements a `floatTo16BitPCM` utility to convert browser-standard 32-bit audio into the 16-bit PCM required by Sarvam AI.

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

### 2. `backend/app/api/endpoints.py` (The Traffic Controller)
- **`/ws/speaker`**: Receives raw PCM chunks. When a "flush" signal is received, it triggers the Sarvam AI pipeline.
- **`/ws/listener`**: Subscribes a user to the broadcast stream. It uses "Language Grouping" to ensure we only translate once per language, regardless of how many listeners are joined.

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
1. **Frontend**: Mic → VAD (Neural Check) → PCM 16-bit Conversion → WebSocket.
2. **Backend**: WebSocket → Buffer → [Flush Signal] → Sarvam STT.
3. **AI Pipeline**: STT (Hindi) → Translation (Marathi) → TTS (Marathi Audio).
4. **Broadcast**: Backend → Group by Language → Send to all Listeners in group.
5. **Listener**: WebSocket → Received Base64 Audio → Browser `Audio()` Player.
