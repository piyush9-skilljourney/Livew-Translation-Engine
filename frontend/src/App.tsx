import React, { useState, useRef } from 'react';
import { Mic, MicOff, Volume2, Globe, ArrowRight, Languages } from 'lucide-react';
import './App.css';

// ─── Supported target languages ───────────────────────────────────────────────
const LANGUAGES = [
  { code: 'mr-IN', label: 'Marathi', native: 'मराठी' },
  { code: 'hi-IN', label: 'Hindi',   native: 'हिन्दी' },
  { code: 'bn-IN', label: 'Bengali', native: 'বাংলা' },
  { code: 'ta-IN', label: 'Tamil',   native: 'தமிழ்' },
  { code: 'te-IN', label: 'Telugu',  native: 'తెలుగు' },
  { code: 'kn-IN', label: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'ml-IN', label: 'Malayalam', native: 'മലയാളം' },
  { code: 'gu-IN', label: 'Gujarati', native: 'ગુજરાતી' },
  { code: 'pa-IN', label: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
];

function App() {
  const [role, setRole] = useState<'selection' | 'speaker' | 'listener'>('selection');
  const [targetLang, setTargetLang] = useState('mr-IN');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [originalText, setOriginalText] = useState('');
  const [translatedText, setTranslatedText] = useState('');

  const isRecordingRef = useRef(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  // ── WebSocket connection (role + language aware) ──────────────────────────
  React.useEffect(() => {
    if (role === 'selection') return;

    const wsUrl = role === 'speaker'
      ? 'ws://localhost:8000/ws/speaker'
      : `ws://localhost:8000/ws/listener?lang=${targetLang}`;

    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('🔌 Connected to', wsUrl);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'transcript' && role === 'speaker') {
        setOriginalText(data.text);
      } else if (data.type === 'audio' && role === 'listener') {
        setTranslatedText(data.text);
        const audio = new Audio(`data:audio/wav;base64,${data.audio}`);
        audio.play().catch(e => console.error('Audio play error:', e));
      }
    };

    socket.onclose = () => console.log('🔌 WebSocket closed');

    return () => {
      if (socket.readyState === WebSocket.OPEN) socket.close();
    };
  }, [role, targetLang]);

  // ── Audio recording ───────────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;

      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      const source = audioContext.createMediaStreamSource(stream);
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      isRecordingRef.current = true;
      setIsRecording(true);

      let chunkCount = 0;
      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          const s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        chunkCount++;
        if (chunkCount % 8 === 0) console.log(`🎙 Chunk #${chunkCount}`);
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(pcm16.buffer);
        }
      };

      const gainNode = audioContext.createGain();
      gainNode.gain.value = 0;
      source.connect(processor);
      processor.connect(gainNode);
      gainNode.connect(audioContext.destination);

    } catch (err) {
      console.error('Microphone error:', err);
    }
  };

  const stopRecording = () => {
    isRecordingRef.current = false;
    setIsRecording(false);
    setIsProcessing(true);

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'flush' }));
    }
    processorRef.current?.disconnect();
    audioContextRef.current?.close();
    mediaStreamRef.current?.getTracks().forEach(t => t.stop());

    // Reset processing state after a generous timeout
    setTimeout(() => setIsProcessing(false), 8000);
  };

  const selectedLang = LANGUAGES.find(l => l.code === targetLang)!;

  // ── ROLE SELECTION SCREEN ─────────────────────────────────────────────────
  if (role === 'selection') {
    return (
      <div className="container selection-screen">
        <header>
          <div className="logo">
            <Globe className="icon-blue" />
            <h1>Antigravity Live</h1>
          </div>
          <p className="subtitle">Real-Time Indian Language Translation</p>
        </header>

        <div className="role-choices">
          <div className="card choice-card" onClick={() => setRole('speaker')}>
            <Mic size={64} className="icon-blue" />
            <h2>I am a Speaker</h2>
            <p>Broadcast your voice in Hindi and have it translated live.</p>
            <button className="btn-primary">Enter Speaker Studio <ArrowRight size={16} /></button>
          </div>

          <div className="card choice-card listener-choice">
            <Volume2 size={64} className="icon-blue" />
            <h2>I am a Listener</h2>
            <p>Choose the language you want to listen in:</p>

            <div className="lang-grid">
              {LANGUAGES.map(lang => (
                <button
                  key={lang.code}
                  className={`lang-btn ${targetLang === lang.code ? 'selected' : ''}`}
                  onClick={(e) => { e.stopPropagation(); setTargetLang(lang.code); }}
                >
                  <span className="lang-native">{lang.native}</span>
                  <span className="lang-english">{lang.label}</span>
                </button>
              ))}
            </div>

            <button className="btn-primary" onClick={() => setRole('listener')}>
              Join as Listener in {selectedLang.label} <ArrowRight size={16} />
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ── SPEAKER / LISTENER VIEWS ──────────────────────────────────────────────
  return (
    <div className="container">
      <header>
        <div className="logo" onClick={() => { setRole('selection'); setOriginalText(''); setTranslatedText(''); }} style={{ cursor: 'pointer' }}>
          <Globe className="icon-blue" />
          <h1>Antigravity {role === 'speaker' ? 'Studio' : 'Room'}</h1>
        </div>
        <p className="subtitle">
          {role === 'speaker'
            ? 'Hindi Speaker Dashboard'
            : `Listening in ${selectedLang.label} (${selectedLang.native})`}
        </p>
      </header>

      <main>
        {role === 'speaker' ? (
          <div className="card broadcast-card">
            <div className="card-header">
              <div className="status">
                <span className={`dot ${isRecording ? 'pulse' : ''}`}></span>
                {isProcessing ? 'PROCESSING...' : isRecording ? 'LIVE BROADCASTING' : 'READY TO START'}
              </div>
            </div>

            <div className="controls">
              <button
                className={`mic-button ${isRecording ? 'active' : ''} ${isProcessing ? 'loading' : ''}`}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onMouseLeave={isRecording ? stopRecording : undefined}
                onTouchStart={(e) => { e.preventDefault(); startRecording(); }}
                onTouchEnd={(e) => { e.preventDefault(); stopRecording(); }}
                disabled={isProcessing}
              >
                {isRecording ? <MicOff size={48} /> : <Mic size={48} />}
                <span className="button-text">
                  {isProcessing ? 'Translating...' : isRecording ? 'Release to Translate' : 'Hold to Speak'}
                </span>
              </button>
            </div>

            <div className="results-container">
              <div className="result-card full-width">
                <h3>Live Hindi Transcription</h3>
                <p className="transcription-text">{originalText || 'Your transcription will appear here...'}</p>
              </div>
            </div>
          </div>
        ) : (
          <div className="card listener-card">
            <div className="card-header">
              <div className="status">
                <span className="dot pulse"></span>
                LISTENING LIVE
              </div>
              <div className="lang-badge">
                <Languages size={14} />
                {selectedLang.native} · {selectedLang.label}
              </div>
            </div>

            <div className="listener-visualizer">
              <Volume2 size={80} className={translatedText ? 'icon-pulse' : 'icon-dim'} />
              <p>{translatedText ? '🔊 Receiving audio...' : '⌛ Waiting for Speaker...'}</p>
            </div>

            <div className="results-container">
              <div className="result-card highlight full-width">
                <h3>Live {selectedLang.label} Translation</h3>
                <p className="transcription-text">{translatedText || 'Translation will appear here...'}</p>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer>
        <button className="btn-text" onClick={() => { setRole('selection'); setOriginalText(''); setTranslatedText(''); }}>
          ← Change Role
        </button>
        <p>© 2026 Live Translation Engine | Powered by Sarvam AI</p>
      </footer>
    </div>
  );
}

export default App;
