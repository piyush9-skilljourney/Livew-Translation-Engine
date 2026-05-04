import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Mic, MicOff, Volume2, Globe, ArrowRight } from 'lucide-react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api/v1';

function App() {
  const [role, setRole] = useState<'selection' | 'speaker' | 'listener'>('selection');
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [originalText, setOriginalText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  
  const isRecordingRef = useRef(false);
  const audioContextRef = useRef<AudioContext | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const socketRef = useRef<WebSocket | null>(null);

  // Handle WebSocket connection based on role
  React.useEffect(() => {
    if (role === 'selection') return;

    const wsUrl = role === 'speaker' ? 'ws://localhost:8000/ws/speaker' : 'ws://localhost:8000/ws/listener';
    const socket = new WebSocket(wsUrl);
    socketRef.current = socket;

    socket.onopen = () => {
      console.log('🔌 WebSocket Connected to', wsUrl);
    };

    socket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === 'transcript' && role === 'speaker') {
        setOriginalText(data.text);
      } else if (data.type === 'audio' && role === 'listener') {
        setTranslatedText(data.text);
        const audio = new Audio(`data:audio/wav;base64,${data.audio}`);
        audio.play().catch(e => console.error("Audio play error:", e));
      }
    };

    return () => {
      if (socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [role]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      
      // Use 16000Hz as required by Sarvam AI
      const AudioContextClass = window.AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      
      const source = audioContext.createMediaStreamSource(stream);
      // Process audio in tiny blocks (4096 frames = ~250ms)
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;
      
      isRecordingRef.current = true;
      setIsRecording(true);

      // Diagnostic counter
      let chunkCount = 0;

      processor.onaudioprocess = (e) => {
        if (!isRecordingRef.current) return;
        
        // Extract raw audio data (Float32)
        const inputData = e.inputBuffer.getChannelData(0);
        // Convert to PCM Int16
        const pcm16 = new Int16Array(inputData.length);
        for (let i = 0; i < inputData.length; i++) {
          let s = Math.max(-1, Math.min(1, inputData[i]));
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF;
        }
        
        chunkCount++;
        if (chunkCount % 4 === 0) {
           console.log(`🎙 Captured and sending audio chunk #${chunkCount} (${pcm16.length} samples)`);
        }

        // Send raw bytes directly through WebSocket
        if (socketRef.current?.readyState === WebSocket.OPEN) {
          socketRef.current.send(pcm16.buffer);
        }
      };
      
      // Silent node to prevent nasty feedback loops
      const gainNode = audioContext.createGain();

      gainNode.gain.value = 0;
      
      source.connect(processor);
      processor.connect(gainNode);
      gainNode.connect(audioContext.destination);

    } catch (err) {
      console.error('Error accessing microphone:', err);
    }
  };

  const stopRecording = () => {
    isRecordingRef.current = false;
    setIsRecording(false);
    
    if (socketRef.current?.readyState === WebSocket.OPEN) {
      socketRef.current.send(JSON.stringify({ type: 'flush' }));
    }
    
    if (processorRef.current) {
      processorRef.current.disconnect();
    }
    if (audioContextRef.current) {
      audioContextRef.current.close();
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach(track => track.stop());
    }
  };


  const sendAudioToBackend = async (audioBlob: Blob) => {
    setIsProcessing(true);
    const formData = new FormData();
    formData.append('file', audioBlob, 'recording.wav');
    formData.append('target_lang', 'mr-IN'); // Default to Marathi for POC

    try {
      const response = await axios.post(`${API_BASE_URL}/translate-audio`, formData);
      const { original_text, translated_text, audio_base64 } = response.data;
      
      setOriginalText(original_text);
      setTranslatedText(translated_text);
      
      // 📡 BROADCAST TO ALL LISTENERS 📡
      if (role === 'speaker' && socketRef.current?.readyState === WebSocket.OPEN && audio_base64) {
        socketRef.current.send(JSON.stringify({
          type: 'broadcast',
          text: translated_text,
          audio: audio_base64
        }));
      }

      // Play the translated audio locally so the speaker knows it worked
      if (audio_base64) {
        const audio = new Audio(`data:audio/wav;base64,${audio_base64}`);
        audio.play().catch(e => console.error("Audio playback failed:", e));
      }
    } catch (err) {
      console.error('Translation error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

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
            <p>Broadcast your voice in Hindi and get it translated live.</p>
            <button className="btn-primary">Enter Speaker Studio</button>
          </div>
          
          <div className="card choice-card" onClick={() => setRole('listener')}>
            <Volume2 size={64} className="icon-blue" />
            <h2>I am a Listener</h2>
            <p>Listen to the live Marathi translation of the speaker.</p>
            <button className="btn-primary">Join Listening Room</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="container">
      <header>
        <div className="logo" onClick={() => setRole('selection')} style={{ cursor: 'pointer' }}>
          <Globe className="icon-blue" />
          <h1>Antigravity {role === 'speaker' ? 'Studio' : 'Room'}</h1>
        </div>
        <p className="subtitle">{role === 'speaker' ? 'Hindi Speaker Dashboard' : 'Marathi Listener Dashboard'}</p>
      </header>

      <main>
        {role === 'speaker' ? (
          <div className="card broadcast-card">
            <div className="card-header">
              <div className="status">
                <span className={`dot ${isRecording ? 'pulse' : ''}`}></span>
                {isRecording ? 'LIVE BROADCASTING' : 'READY TO START'}
              </div>
            </div>

            <div className="controls">
              <button 
                className={`mic-button ${isRecording ? 'active' : ''} ${isProcessing ? 'loading' : ''}`}
                onMouseDown={startRecording}
                onMouseUp={stopRecording}
                onMouseLeave={isRecording ? stopRecording : undefined}
                disabled={isProcessing}
              >
                {isRecording ? <MicOff size={48} /> : <Mic size={48} />}
                <span className="button-text">
                  {isProcessing ? 'Processing...' : isRecording ? 'Speaking Live...' : 'Hold to Broadcast'}
                </span>
              </button>
            </div>
            
            <div className="results-container">
              <div className="result-card full-width">
                <h3>Live Hindi Transcription</h3>
                <p className="transcription-text">{originalText || 'Transcription will appear here...'}</p>
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
            </div>

            <div className="listener-visualizer">
              <Volume2 size={80} className={translatedText ? 'icon-pulse' : 'icon-dim'} />
              <p>{translatedText ? '🔊 Receiving Marathi Audio...' : '⌛ Waiting for Speaker...'}</p>
            </div>

            <div className="results-container">
              <div className="result-card highlight full-width">
                <h3>Live Marathi Translation</h3>
                <p className="transcription-text">{translatedText || 'Translation will appear here...'}</p>
              </div>
            </div>
          </div>
        )}
      </main>

      <footer>
        <button className="btn-text" onClick={() => setRole('selection')}>Change Role</button>
        <p>&copy; 2026 Live Translation Engine | Powered by Sarvam AI</p>
      </footer>
    </div>
  );
}

export default App;
