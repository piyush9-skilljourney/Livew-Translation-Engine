import React, { useState, useRef } from 'react';
import axios from 'axios';
import { Mic, MicOff, Volume2, Globe, ArrowRight } from 'lucide-react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api/v1';

function App() {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [originalText, setOriginalText] = useState('');
  const [translatedText, setTranslatedText] = useState('');
  
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/wav' });
        await sendAudioToBackend(audioBlob);
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (err) {
      console.error('Error accessing microphone:', err);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
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
      
      // Play the translated audio
      const audio = new Audio(`data:audio/wav;base64,${audio_base64}`);
      audio.play();
    } catch (err) {
      console.error('Translation error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="container">
      <header>
        <div className="logo">
          <Globe className="icon-blue" />
          <h1>Antigravity Translation</h1>
        </div>
        <p className="subtitle">Live One-Way Audio Broadcast POC</p>
      </header>

      <main>
        <div className="card broadcast-card">
          <div className="card-header">
            <div className="status">
              <span className={`dot ${isRecording ? 'pulse' : ''}`}></span>
              {isRecording ? 'LIVE RECORDING' : 'READY TO BROADCAST'}
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
                {isProcessing ? 'Processing...' : isRecording ? 'Release to Send' : 'Hold to Speak'}
              </span>
            </button>
          </div>

          <div className="languages">
            <div className="lang-tag">Hindi (Speaker)</div>
            <ArrowRight size={16} />
            <div className="lang-tag highlight">Marathi (Listeners)</div>
          </div>
        </div>

        {(originalText || translatedText) && (
          <div className="results-container">
            <div className="result-card">
              <h3>Original (Hindi)</h3>
              <p>{originalText || '...'}</p>
            </div>
            <div className="result-card highlight">
              <h3>Translated (Marathi) <Volume2 size={16} /></h3>
              <p>{translatedText || '...'}</p>
            </div>
          </div>
        )}
      </main>

      <footer>
        <p>&copy; 2026 Live Translation Engine POC | Powered by Sarvam AI</p>
      </footer>
    </div>
  );
}

export default App;
