import React, { useState, useRef, useEffect } from 'react';
import { useMicVAD, utils } from '@ricky0123/vad-react';
import { Mic, MicOff, Volume2, Globe, ArrowRight, Languages, Zap, Hand, Radio, Users, Settings } from 'lucide-react';
import './App.css';

// ─── Supported target languages ───────────────────────────────────────────────
const TARGET_LANGS = [
  { code: 'hi-IN', name: 'Hindi', native: 'हिन्दी' },
  { code: 'mr-IN', name: 'Marathi', native: 'मराठी' },
  { code: 'bn-IN', name: 'Bengali', native: 'বাংলা' },
  { code: 'ta-IN', name: 'Tamil', native: 'தமிழ்' },
  { code: 'te-IN', name: 'Telugu', native: 'తెలుగు' },
  { code: 'kn-IN', name: 'Kannada', native: 'ಕನ್ನಡ' },
  { code: 'ml-IN', name: 'Malayalam', native: 'മലയാളം' },
  { code: 'gu-IN', name: 'Gujarati', native: 'ગુજરાતી' },
  { code: 'pa-IN', name: 'Punjabi', native: 'ਪੰਜਾਬੀ' },
  { code: 'en-IN', name: 'English', native: 'English' },
];

const SPEAKER_LANGS = [
  { code: 'hi-IN', name: 'Hindi' },
  { code: 'gu-IN', name: 'Gujarati' },
  { code: 'en-IN', name: 'English' },
  { code: 'mr-IN', name: 'Marathi' },
];

// ─── Audio Helpers ────────────────────────────────────────────────────────────
const floatTo16BitPCM = (input: Float32Array): Int16Array => {
  const pcm16 = new Int16Array(input.length);
  for (let i = 0; i < input.length; i++) {
    const s = Math.max(-1, Math.min(1, input[i]));
    pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
  }
  return pcm16;
};

const WS_HOST = window.location.hostname === 'localhost' ? 'localhost:8000' : `${window.location.hostname}:8000`;

function App() {
  const [role, setRole] = useState<'selection' | 'speaker' | 'listener'>('selection');
  const [mode, setMode] = useState<'manual' | 'auto'>('manual');
  const modeRef = useRef(mode);
  useEffect(() => { modeRef.current = mode; }, [mode]);

  const [targetLang, setTargetLang] = useState('mr-IN');
  const [speakerLang, setSpeakerLang] = useState('gu-IN');
  const [voice, setVoice] = useState<'aditya' | 'anushka'>('aditya');
  const [latency, setLatency] = useState<number | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [originalText, setOriginalText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<'connecting' | 'connected' | 'reconnecting' | 'error'>('connecting');

  const socketRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<number | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const isRecordingRef = useRef(false);

  // ── Audio Queue Logic ──────────────────────────────────────────────────────
  const audioQueueRef = useRef<{audioBase64: string, text: string}[]>([]);
  const isPlayingRef = useRef(false);

  const playNextAudio = () => {
    if (audioQueueRef.current.length === 0) {
      isPlayingRef.current = false;
      return;
    }
    isPlayingRef.current = true;
    const nextItem = audioQueueRef.current.shift();
    if (!nextItem) return;

    setTranslatedText(nextItem.text);
    const audio = new Audio(`data:audio/wav;base64,${nextItem.audioBase64}`);
    
    audio.onended = () => playNextAudio();
    audio.play().catch(e => {
      console.error('Audio play error:', e);
      playNextAudio();
    });
  };

  // ── WebSocket setup with Reconnect ─────────────────────────────────────────
  useEffect(() => {
    if (role === 'selection') return;

    let retryCount = 0;
    let isComponentMounted = true;

    const connectWS = () => {
      if (!isComponentMounted) return;
      setWsStatus(retryCount === 0 ? 'connecting' : 'reconnecting');

      const wsUrl = role === 'speaker'
        ? `ws://${WS_HOST}/ws/speaker?lang=${speakerLang}`
        : `ws://${WS_HOST}/ws/listener?lang=${targetLang}&voice=${voice}`;

      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onopen = () => {
        console.log('🔌 Connected to', wsUrl);
        setWsStatus('connected');
        retryCount = 0;
      };

      socket.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === 'transcript' && role === 'speaker') {
          setOriginalText(data.text);
          if (data.flush_timestamp) {
             const now = Date.now();
             setLatency((now - data.flush_timestamp) / 1000);
          }
        } else if (data.type === 'audio' && role === 'listener') {
          audioQueueRef.current.push({ audioBase64: data.audio, text: data.text });
          if (data.latency_s) setLatency(data.latency_s);
          if (!isPlayingRef.current) {
            playNextAudio();
          }
        }
      };

      socket.onclose = () => {
        console.log('🔌 WebSocket closed');
        if (isComponentMounted) {
          const timeout = Math.min(1000 * Math.pow(2, retryCount), 10000);
          retryCount++;
          console.log(`⏳ Reconnecting in ${timeout}ms (Attempt ${retryCount})...`);
          reconnectTimeoutRef.current = window.setTimeout(connectWS, timeout);
        }
      };
    };

    connectWS();

    return () => {
      isComponentMounted = false;
      if (reconnectTimeoutRef.current) window.clearTimeout(reconnectTimeoutRef.current);
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.onclose = null;
        socketRef.current.close();
      }
    };
  }, [role, targetLang, speakerLang, voice]);

  // ── HANDS-FREE VAD LOGIC ────────────────────────────────────────────────
  const vadOptions = React.useMemo(() => ({
    startOnLoad: false,
    baseAssetPath: window.location.origin + "/",
    onnxWASMBasePath: window.location.origin + "/",
    model: "v5" as const,
    ortConfig(ort: any) {
      ort.env.wasm.wasmPaths = window.location.origin + "/";
    },
    onSpeechStart: () => {
      if (modeRef.current === 'auto') {
        setIsRecording(true);
        setError(null);
      }
    },
    onSpeechEnd: (audio: Float32Array) => {
      if (modeRef.current !== 'auto') return;
      setIsRecording(false);
      setIsProcessing(true);
      const pcm16 = floatTo16BitPCM(audio);
      if (socketRef.current?.readyState === WebSocket.OPEN) {
        socketRef.current.send(pcm16.buffer);
        socketRef.current.send(JSON.stringify({ type: 'flush', timestamp: Date.now() }));
      }
      setTimeout(() => setIsProcessing(false), 5000);
    },
    onVADMisfire: () => {
      if (modeRef.current === 'auto') setIsRecording(false);
    }
  }), []);

  const vad = useMicVAD(vadOptions);

  useEffect(() => {
    if (role === 'speaker' && mode === 'auto' && !vad.loading && !vad.errored) {
      vad.start();
    } else {
      vad.pause();
    }
  }, [role, mode, vad.loading, vad.errored]);

  // ── Audio recording (Manual) ────────────────────────────────────────────────
  const startRecording = async () => {
    setError(null);
    try {
      if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        throw new Error("Microphone access is not supported in this browser or requires HTTPS.");
      }
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

      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current) return;
        const inputData = e.inputBuffer.getChannelData(0);
        const pcm16 = floatTo16BitPCM(inputData);
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(pcm16.buffer);
        }
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
    } catch (err: any) {
      console.error('Microphone error:', err);
      setError(err.message || "Could not access microphone.");
      setIsRecording(false);
    }
  };

  const stopRecording = () => {
    isRecordingRef.current = false;
    setIsRecording(false);
    setIsProcessing(true);

    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'flush', timestamp: Date.now() }));
    }

    if (processorRef.current) {
      processorRef.current.disconnect();
      processorRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
      audioContextRef.current = null;
    }
    setTimeout(() => setIsProcessing(false), 5000);
  };

  return (
    <div className="app-container">
      <header>
        <h1>BhashaCast <span className="badge">Beta</span></h1>
        {role !== 'selection' && (
          <button className="mode-btn" onClick={() => setRole('selection')}>
            Change Role
          </button>
        )}
      </header>

      {role === 'selection' ? (
        <main className="selection-screen">
          <div className="intro-text">
            <h2>Break Language Barriers.</h2>
            <p>A real-time, multi-lingual broadcast platform for the modern world.</p>
          </div>

          <div className="role-grid">
            <div className="role-card" onClick={() => setRole('speaker')}>
              <div className="icon-box"><Radio size={32} /></div>
              <div>
                <h3>Broadcast Studio</h3>
                <p>Start a session. Your voice will be translated and broadcasted live to everyone.</p>
              </div>
              <ArrowRight className="arrow" />
            </div>

            <div className="role-card" onClick={() => setRole('listener')}>
              <div className="icon-box"><Users size={32} /></div>
              <div>
                <h3>Join as Listener</h3>
                <p>Tune into a live broadcast and hear it in your preferred native language.</p>
              </div>
              <ArrowRight className="arrow" />
            </div>
          </div>
        </main>
      ) : (
        <main className="studio-layout">
          <section className="main-card">
            <div className="card-header">
              <div className="status">
                <span className={`dot ${isRecording ? 'pulse' : ''} ${wsStatus === 'reconnecting' ? 'reconnecting' : ''} ${wsStatus === 'error' ? 'error' : ''}`}></span>
                {wsStatus === 'reconnecting' ? 'RECONNECTING...' : 
                 wsStatus === 'error' ? 'OFFLINE' : 
                 isProcessing ? 'PROCESSING...' : 
                 isRecording ? 'LIVE' : 'READY'}
              </div>
              
              {role === 'speaker' && (
                <div className="mode-toggle">
                  <button className={`mode-btn ${mode === 'manual' ? 'active' : ''}`} onClick={() => setMode('manual')}>
                    <Hand size={14} /> Manual
                  </button>
                  <button className={`mode-btn ${mode === 'auto' ? 'active' : ''}`} onClick={() => setMode('auto')}>
                    <Zap size={14} /> Hands-Free
                  </button>
                </div>
              )}
              {latency !== null && (
                 <div className="latency-badge" style={{ fontSize: '0.75rem', color: '#4ade80', marginLeft: 'auto', marginRight: '1rem', border: '1px solid #4ade80', padding: '2px 8px', borderRadius: '12px' }}>
                    Latency: ~{latency.toFixed(1)}s
                 </div>
              )}
            </div>

            <div className="controls">
              {role === 'speaker' ? (
                mode === 'manual' ? (
                  <button
                    className={`mic-button ${isRecording ? 'active' : ''} ${isProcessing ? 'loading' : ''}`}
                    onMouseDown={startRecording} onMouseUp={stopRecording} onMouseLeave={isRecording ? stopRecording : undefined}
                    onTouchStart={startRecording} onTouchEnd={stopRecording} disabled={isProcessing}
                  >
                    {isRecording ? <MicOff size={48} /> : <Mic size={48} />}
                    <span className="button-text">{isProcessing ? 'Translating...' : isRecording ? 'Release to Send' : 'Hold to Speak'}</span>
                  </button>
                ) : (
                  <div className="auto-mic-indicator">
                    <div className={`visualizer ${isRecording ? 'active' : ''}`}>
                      <Mic size={48} className={isRecording ? 'pulse-blue' : ''} />
                    </div>
                    <p className="status-text">{isRecording ? "Listening to you..." : "Speak naturally"}</p>
                  </div>
                )
              ) : (
                <div className="listener-view">
                  <Volume2 size={80} className={translatedText ? 'pulse-blue' : ''} />
                  <p className="status-text">{translatedText ? "Receiving Broadcast..." : "Waiting for Speaker..."}</p>
                </div>
              )}
            </div>

            <div className="transcript-area">
              <div className="box">
                <span className="label">{role === 'speaker' ? 'Your Speech' : 'Original Text'}</span>
                <p className="text">{originalText || "..."}</p>
              </div>
              <div className="box">
                <span className="label">Translation ({targetLang})</span>
                <p className="text">{translatedText || "..."}</p>
              </div>
            </div>

            {error && <div className="error-toast">{error}</div>}
          </section>

          <aside className="side-panel">
            <div className="panel-card">
              <h4><Settings size={14} /> Language</h4>
              <div className="lang-list">
                {role === 'speaker' ? (
                  SPEAKER_LANGS.map(l => (
                    <button key={l.code} className={`lang-btn ${speakerLang === l.code ? 'active' : ''}`} onClick={() => setSpeakerLang(l.code)}>
                      {l.name}
                    </button>
                  ))
                ) : (
                  TARGET_LANGS.map(l => (
                    <button key={l.code} className={`lang-btn ${targetLang === l.code ? 'active' : ''}`} onClick={() => setTargetLang(l.code)}>
                      <span>{l.name}</span>
                      <span className="native-label">{l.native}</span>
                    </button>
                  ))
                )}
              </div>
            </div>

            {role === 'listener' && (
              <div className="panel-card">
                <h4><Users size={14} /> Voice Preference</h4>
                <div className="lang-list" style={{ flexDirection: 'row' }}>
                  <button className={`lang-btn ${voice === 'aditya' ? 'active' : ''}`} style={{ flex: 1 }} onClick={() => setVoice('aditya')}>
                    Male
                  </button>
                  <button className={`lang-btn ${voice === 'anushka' ? 'active' : ''}`} style={{ flex: 1 }} onClick={() => setVoice('anushka')}>
                    Female
                  </button>
                </div>
              </div>
            )}
          </aside>
        </main>
      )}
    </div>
  );
}

export default App;
