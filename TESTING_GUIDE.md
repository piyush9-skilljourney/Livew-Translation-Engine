# Testing Guide: Live Translation Engine

## ✅ Current Working Mode: Push-to-Talk Broadcast

### Prerequisites
1. Backend running: `python -m uvicorn app.main:app --reload` (in `backend/`)
2. Frontend running: `npm run dev` (in `frontend/`)
3. Open two browser tabs to `http://localhost:5173/`

---

### Test: Basic Push-to-Talk Broadcast

**Setup:**
- Tab 1 → Click **"I am a Speaker"**
- Tab 2 → Click **"I am a Listener"**

**Backend terminal should show:**
```
🎤 Speaker Connected
👥 Listener Joined. Total: 1
```

**Speaking:**
1. In Tab 1, **hold the microphone button**
2. Speak clearly in Hindi for **at least 3 seconds**, e.g.:  
   *"मेरा नाम आदित्य है और मैं एक सॉफ्टवेयर इंजीनियर हूँ"*
3. **Release the button**

**Backend terminal should show:**
```
🎤 Speaker pressed button. Collecting audio...
📡 Buffered 4 chunks (250ms)
🌊 Button released. 20 chunks, 5.1s of audio.
🧠 Transcribing with Sarvam batch STT...
📥 Transcript: मेरा नाम आदित्य है...
✅ Translated: माझे नाव आदित्य आहे...
🔊 Broadcasting to 1 listener(s).
```

**Expected result:**
- Tab 2 (Listener) plays the Marathi audio automatically
- Tab 2 shows the Marathi text subtitle
- Tab 1 (Speaker) shows the Hindi transcription feedback

---

### Test: Multiple Listeners

1. Open 3+ tabs of `http://localhost:5173/`
2. Tab 1 = Speaker, Tabs 2/3/4 = Listeners
3. Backend will show `👥 Listener Joined. Total: 3`
4. All Listener tabs should receive the broadcast simultaneously

---

### Troubleshooting

| Issue | Cause | Fix |
|---|---|---|
| No audio in Listener tab | Browser autoplay policy | Click anywhere in the Listener tab first to unlock autoplay |
| `⚠️ No transcript from STT` | Audio too short or mic too quiet | Hold button for 3+ seconds, speak close to mic |
| `❌ Broadcast Error` | Listener disconnected | Refresh both tabs |
| Latency is 5+ seconds | Normal for batch pipeline | Expected — see Phase 3 for live streaming |

---

### Known Limitations (Push-to-Talk Mode)
- Speaker must hold a button — not hands-free
- 3–5 second latency per utterance
- `ScriptProcessorNode` deprecation warning in Chrome (non-breaking)
- Browser must have microphone permission granted

---

## 🔄 Phase 3 (Coming): True Live Streaming
- No button required — VAD auto-detects speech
- Target latency: 1–2 seconds
- See `implementation_plan.md` for roadmap
