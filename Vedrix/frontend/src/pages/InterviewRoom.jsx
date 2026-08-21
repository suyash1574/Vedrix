import { useState, useEffect, useRef, useCallback } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic, MicOff, Video, VideoOff, Send, Loader2, Maximize,
  CheckCircle2, Camera, User, PhoneOff, BrainCircuit, SignalHigh,
  Play, Terminal, Save, AudioLines
} from 'lucide-react';
import useAuthStore from '../store/useAuthStore';
import useToastStore from '../store/useToastStore';
import apiClient from '../services/api';
import Editor from '@monaco-editor/react';
import { useIsMobile } from '../hooks/useDeviceDetection';
import DesktopOnlyBanner from '../components/DesktopOnlyBanner';
import InterviewProgressBar from '../components/InterviewProgressBar';
import ConnectionStatus from '../components/ConnectionStatus';
import { enqueueAnswer, syncQueue, getQueueLength, saveDraft } from '../services/offlineQueue';

/* ── WAVEFORM HEIGHTS — pre-generated for stability ────────────────────── */
const waveformHeights = Array.from({ length: 60 }, () => Math.random() * 50 + 10);

/* ── READY CHECK WIZARD ─────────────────────────────────────────────────── */
const ReadyCheckWizard = ({ onReady }) => {
  const [step, setStep] = useState(1);
  const [permissions, setPermissions] = useState({ mic: false, cam: false });
  const [loading, setLoading] = useState(false);

  const checkHardware = async () => {
    setLoading(true);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true, video: true });
      setPermissions({ mic: true, cam: true });
      stream.getTracks().forEach(track => track.stop());
      setStep(2);
    } catch {
      alert('Hardware access (Mic & Camera) is mandatory for this assessment.');
    } finally {
      setLoading(false);
    }
  };

  const handleStart = async () => {
    try {
      if (document.documentElement.requestFullscreen) {
        await document.documentElement.requestFullscreen();
      }
    } finally {
      onReady();
    }
  };

  return (
    <div className="fixed inset-0 bg-[#020617] flex items-center justify-center z-[200] p-6 font-sans">
      <div className="absolute inset-0 overflow-hidden opacity-20 pointer-events-none">
        <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-purple-600 blur-[150px] rounded-full" />
        <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-indigo-600 blur-[150px] rounded-full" />
      </div>

      <motion.div initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
        className="max-w-2xl w-full bg-white/5 backdrop-blur-3xl border border-white/10 rounded-[3rem] p-12 shadow-2xl relative">
        <div className="flex items-center space-x-3 mb-10">
          <div className="w-10 h-10 bg-purple-600 rounded-xl flex items-center justify-center text-white">
            <BrainCircuit size={24} />
          </div>
          <span className="text-xl font-black text-white tracking-tight">Autergo <span className="text-purple-400">Proctor</span></span>
        </div>

        <AnimatePresence mode="wait">
          {step === 1 ? (
            <motion.div key="step1" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h1 className="text-5xl font-black text-white mb-6 leading-tight tracking-tighter">Hardware <br />Validation</h1>
              <p className="text-slate-400 text-lg mb-10 leading-relaxed font-medium">
                We will quickly check your microphone and camera so the interview can run smoothly.
              </p>
              <div className="grid grid-cols-2 gap-4 mb-10">
                <div className={`p-8 rounded-3xl border-2 transition-all ${permissions.mic ? 'bg-purple-600 border-purple-400 text-white' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                  <Mic size={32} className="mb-4" />
                  <span className="font-black text-xs uppercase tracking-widest block">Microphone</span>
                  <span className="text-xs font-bold opacity-60 uppercase">{permissions.mic ? 'READY' : 'CHECK REQUIRED'}</span>
                </div>
                <div className={`p-8 rounded-3xl border-2 transition-all ${permissions.cam ? 'bg-purple-600 border-purple-400 text-white' : 'bg-white/5 border-white/10 text-slate-500'}`}>
                  <Camera size={32} className="mb-4" />
                  <span className="font-black text-xs uppercase tracking-widest block">Camera</span>
                  <span className="text-xs font-bold opacity-60 uppercase">{permissions.cam ? 'READY' : 'CHECK REQUIRED'}</span>
                </div>
              </div>
              <button onClick={checkHardware} disabled={loading}
                className="w-full bg-white text-slate-950 py-5 rounded-2xl font-black uppercase tracking-widest text-sm hover:bg-purple-400 hover:text-white transition-all shadow-xl flex items-center justify-center">
                {loading ? <Loader2 className="animate-spin" size={20} /> : <span>Start Validation</span>}
              </button>
            </motion.div>
          ) : (
            <motion.div key="step2" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }}>
              <h1 className="text-5xl font-black text-white mb-6 leading-tight tracking-tighter">Pre-Interview <br />Checklist</h1>
              <p className="text-slate-400 text-lg mb-10 leading-relaxed font-medium">Before you begin, review the setup and switch to fullscreen for a focused interview experience.</p>
              <ul className="space-y-4 mb-10">
                {['Fullscreen recommended', 'Microphone and camera checked', 'Voice responses supported', 'Typed answers available when needed'].map((rule, i) => (
                  <li key={i} className="flex items-center text-slate-300 font-bold uppercase tracking-widest text-[10px]">
                    <CheckCircle2 size={16} className="mr-3 text-purple-500 shrink-0" />{rule}
                  </li>
                ))}
              </ul>
              <button onClick={handleStart}
                className="w-full bg-purple-600 text-white py-5 rounded-2xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 transition-all shadow-[0_0_50px_rgba(147,51,234,0.4)] flex items-center justify-center space-x-3">
                <span>Begin Interview</span>
                <Maximize size={20} />
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.div>
    </div>
  );
};

/* ── WAVEFORM — stable random heights, no re-render jitter ─────────────── */
const Waveform = ({ isRecording }) => {
  return (
    <div className="h-24 flex items-center justify-center space-x-1 overflow-hidden">
      {waveformHeights.map((h, i) => (
        <motion.div
          key={i}
          animate={{ height: isRecording ? h : 4, opacity: isRecording ? 1 : 0.2 }}
          transition={{ duration: 0.4, delay: i * 0.01 }}
          className="w-1 bg-purple-500 rounded-full"
        />
      ))}
    </div>
  );
};

/* ── MAIN INTERVIEW ROOM ────────────────────────────────────────────────── */
const InterviewRoom = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();
  const addToast = useToastStore((s) => s.addToast);
  const [searchParams] = useSearchParams();

  // Phase 2.1: Mobile detection — block interviews on mobile/tablet
  const isMobile = useIsMobile(1024);

  const [resolvedSessionId] = useState(() =>
    `session_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
  );

  // All state variables
  const [ready, setReady] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [agentStatus, setAgentStatus] = useState('Initializing...');
  const [timeLeft, setTimeLeft] = useState(0); // Overall session timer
  const [voiceAvailable, setVoiceAvailable] = useState(false);
  const [questionTimeLeft, setQuestionTimeLeft] = useState(0); // Per-question countdown
  const [tabSwitches, setTabSwitches] = useState(0);
  const [currentQuestion, setCurrentQuestion] = useState(null);
  const [jobRole, setJobRole] = useState('AI Interview');
  const [completedSessionId, setCompletedSessionId] = useState(null);
  const [showTextInput, setShowTextInput] = useState(false);
  const [manualText, setManualText] = useState('');
  const [codeResult, setCodeResult] = useState(null);
  const [copilotSuggestions, setCopilotSuggestions] = useState([]);
  const [isCopilotLoading, setIsCopilotLoading] = useState(false);
  const [code, setCode] = useState("# Write your solution here...\n");
  const [isCodingMode, setIsCodingMode] = useState(false);
  const [codeLanguage, setCodeLanguage] = useState("python");
  const [skillsCovered, setSkillsCovered] = useState(0);
  const [totalSkills] = useState(8);
  const [advisorReady, setAdvisorReady] = useState(false);
  const [advisorConfidence, setAdvisorConfidence] = useState(0);
  const [connectionStatus, setConnectionStatus] = useState('connected');
  const [queuedCount, setQueuedCount] = useState(0);
  const [syncProgress, setSyncProgress] = useState(null);
  const [displayReconnectAttempts, setDisplayReconnectAttempts] = useState(0);
  const [isVideoOn, setIsVideoOn] = useState(true);
  const [videoStream, setVideoStream] = useState(null);
  const [remoteStream, setRemoteStream] = useState(null);
  const [supervisorMode, setSupervisorMode] = useState('ai_only');
  const [showTimeoutConfirm, setShowTimeoutConfirm] = useState(false);
  const [silenceDuration, setSilenceDuration] = useState(0); // ms of current silence
  const [isSilent, setIsSilent] = useState(false); // whether silence is being detected

  // All refs
  const audioContextRef = useRef(null);
  const silenceIntervalRef = useRef(null);
  const submitCodeRef = useRef(null);
  const submitTextAnswerRef = useRef(null);
  const isCodingModeRef = useRef(false);
  const showTextInputRef = useRef(false);
  const manualTextRef = useRef('');
  const isRecordingRef = useRef(false);
  const toggleRecordingRef = useRef(null);
  const lastUserActivityRef = useRef(0);
  const noResponseTimerRef = useRef(null);
  const disconnectStartTime = useRef(null);
  const offlineThresholdMs = 30000;
  const ws = useRef(null);
  const mediaRecorder = useRef(null);
  const audioChunks = useRef([]);
  const reconnectAttempts = useRef(0);
  const reconnectTimer = useRef(null);
  const socketUrlRef = useRef('');
  const isIntentionalClose = useRef(false);
  const pcRef = useRef(null);
  const videoWsRef = useRef(null);
  const videoRef = useRef(null);
  const supervisorVideoRef = useRef(null);

  // Function declarations needed before useEffects
  const cleanupCandidateWebRTC = () => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (videoWsRef.current) {
      videoWsRef.current.close();
      videoWsRef.current = null;
    }
    setRemoteStream(null);
  };

  const updateActivity = useCallback(() => {
    lastUserActivityRef.current = Date.now();
    if (showTimeoutConfirm) {
      setShowTimeoutConfirm(false);
      clearTimeout(noResponseTimerRef.current);
      setAgentStatus('Welcome back! Continuing interview...');
    }
  }, [showTimeoutConfirm]);

  const submitCode = () => {
    updateActivity();
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'code', data: code }));
      setAgentStatus('AI Evaluator: Analyzing logic...');
    } else {
      enqueueAnswer('code', code);
      setQueuedCount(getQueueLength());
      setAgentStatus('Code saved locally. Will sync when reconnected.');
    }
  };

  const submitTextAnswer = () => {
    updateActivity();
    if (manualText.trim() && ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({ type: 'answer', data: manualText }));
      setAgentStatus('Text answer submitted. Reviewing your response.');
      setManualText('');
      setShowTextInput(false);
    } else if (manualText.trim()) {
      enqueueAnswer('answer', manualText);
      setQueuedCount(getQueueLength());
      setAgentStatus('Answer saved locally. Will sync when reconnected.');
      setManualText('');
      setShowTextInput(false);
    }
  };

  // Now, the useEffect hooks can run safely, knowing everything is defined!
  useEffect(() => {
    lastUserActivityRef.current = Date.now();
  }, []);

  useEffect(() => {
    isRecordingRef.current = isRecording;
  }, [isRecording]);

  useEffect(() => {
    isCodingModeRef.current = isCodingMode;
  }, [isCodingMode]);

  useEffect(() => {
    showTextInputRef.current = showTextInput;
  }, [showTextInput]);

  useEffect(() => {
    manualTextRef.current = manualText;
  }, [manualText]);

  useEffect(() => {
    let qTimer;
    if (currentQuestion?.time_limit) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setQuestionTimeLeft(currentQuestion.time_limit);
      qTimer = setInterval(() => {
        setQuestionTimeLeft(prev => {
          if (prev <= 1) {
            clearInterval(qTimer);
            if (isCodingModeRef.current) {
              submitCodeRef.current?.();
              setAgentStatus('Time up! Auto-submitting code solution...');
            } else if (isRecordingRef.current) {
              toggleRecordingRef.current?.();
              setAgentStatus('Time up! Auto-submitting response...');
            } else if (showTextInputRef.current) {
              submitTextAnswerRef.current?.();
              setAgentStatus('Time up! Auto-submitting text response...');
            } else {
              if (manualTextRef.current.trim()) {
                submitTextAnswerRef.current?.();
                setAgentStatus('Time up! Auto-submitting text response...');
              } else {
                setAgentStatus('Time up!');
              }
            }
            return 0;
          }
          return prev - 1;
        });
      }, 1000);
    }
    return () => clearInterval(qTimer);
  }, [currentQuestion]);

  // Attach video stream to video element
  useEffect(() => {
    if (videoRef.current && videoStream) {
      videoRef.current.srcObject = videoStream;
    }
  }, [videoStream]);

  // Attach remote stream to supervisor video element
  useEffect(() => {
    if (supervisorVideoRef.current && remoteStream) {
      supervisorVideoRef.current.srcObject = remoteStream;
    }
  }, [remoteStream]);

  // Initialize video on mount
  useEffect(() => {
    let localStream = null;
    const initVideo = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localStream = stream;
        setVideoStream(stream);
      } catch {
        console.log('Camera not available, continuing without video');
        setIsVideoOn(false);
      }
    };
    if (ready) initVideo();
    return () => {
      // Clean up the stream captured in this effect's closure, not from state
      if (localStream) {
        localStream.getTracks().forEach(track => track.stop());
      }
    };
  }, [ready]); // removed videoStream from deps — it caused an infinite re-render loop

  // Toggle video function
  const toggleVideo = async () => {
    if (isVideoOn) {
      // Turn off video
      if (videoStream) {
        videoStream.getTracks().forEach(track => track.stop());
      }
      setVideoStream(null);
      setIsVideoOn(false);
    } else {
      // Turn on video
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
        setVideoStream(stream);
        setIsVideoOn(true);
      } catch (err) {
        console.error('Camera access failed:', err);
      }
    }
  };

  // WebRTC Candidate Calling Effect
  useEffect(() => {
    if (supervisorMode !== 'hr_takeover') {
      Promise.resolve().then(() => {
        cleanupCandidateWebRTC();
      });
      return;
    }

    let wsInstance = null;

    async function initCandidateWebRTC() {
      try {
        const pc = new RTCPeerConnection({
          iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });
        pcRef.current = pc;

        // Add local tracks if available
        if (videoStream) {
          videoStream.getTracks().forEach(track => {
            pc.addTrack(track, videoStream);
          });
        } else {
          try {
            const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
            setVideoStream(stream);
            stream.getTracks().forEach(track => {
              pc.addTrack(track, stream);
            });
          } catch (e) {
            console.error("Could not obtain webcam for WebRTC takeover call:", e);
          }
        }

        pc.onicecandidate = (event) => {
          if (event.candidate && wsInstance && wsInstance.readyState === WebSocket.OPEN) {
            wsInstance.send(JSON.stringify({
              type: 'ice_candidate',
              candidate: event.candidate
            }));
          }
        };

        pc.ontrack = (event) => {
          if (event.streams && event.streams[0]) {
            setRemoteStream(event.streams[0]);
          }
        };

        const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
        let wsBase = apiBase;
        if (apiBase.startsWith('https://')) {
          wsBase = 'wss://' + apiBase.substring(8);
        } else if (apiBase.startsWith('http://')) {
          wsBase = 'ws://' + apiBase.substring(7);
        }
        
        let videoUrl = `${wsBase}/interview/video/${resolvedSessionId}?role=candidate`;
        const token = localStorage.getItem('token');
        if (token) {
          videoUrl += `&token=${encodeURIComponent(token)}`;
        }

        wsInstance = new WebSocket(videoUrl);
        videoWsRef.current = wsInstance;

        wsInstance.onmessage = async (e) => {
          try {
            const payload = JSON.parse(e.data);
            if (payload.type === 'offer') {
              await pc.setRemoteDescription(new RTCSessionDescription({
                type: 'offer',
                sdp: payload.sdp
              }));
              const answer = await pc.createAnswer();
              await pc.setLocalDescription(answer);
              wsInstance.send(JSON.stringify({
                type: 'answer',
                sdp: answer.sdp
              }));
            } else if (payload.type === 'ice_candidate') {
              if (payload.candidate) {
                await pc.addIceCandidate(new RTCIceCandidate(payload.candidate));
              }
            } else if (payload.type === 'peer_left') {
              setRemoteStream(null);
            }
          } catch (err) {
            console.error("Signaling error:", err);
          }
        };

        wsInstance.onclose = () => {
          console.log("Candidate video signaling closed");
        };

      } catch (err) {
        console.error("Failed to start candidate WebRTC:", err);
      }
    }

    initCandidateWebRTC();

    return () => {
      cleanupCandidateWebRTC();
    };
  }, [supervisorMode, videoStream, resolvedSessionId]);



  // ── FREE TTS via Browser Web Speech API ────────────────────────────────
  const speakWithBrowserTTS = (text) => {
    if (!('speechSynthesis' in window)) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.95;
    utterance.pitch = 1.0;
    // Pick a good English voice if available
    const voices = window.speechSynthesis.getVoices();
    const preferred = voices.find(v =>
      (v.name.includes('Google') && v.lang.startsWith('en')) ||
      (v.name.includes('Samantha') && v.lang.startsWith('en')) ||
      (v.name.includes('Karen') && v.lang.startsWith('en'))
    );
    if (preferred) utterance.voice = preferred;
    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);
    window.speechSynthesis.speak(utterance);
  };

  // Pre-load voices (Chrome needs this async load)
  useEffect(() => {
    const load = () => window.speechSynthesis?.getVoices();
    load();
    window.speechSynthesis?.addEventListener('voiceschanged', load);
    return () => window.speechSynthesis?.removeEventListener('voiceschanged', load);
  }, []);

  const playAudio = (base64) => {
    // If no base64 audio from backend, use free browser TTS
    if (!base64) return;
    try {
      setIsSpeaking(true);
      let mime = 'audio/opus';
      try {
        const binary = atob(base64.slice(0, 12));
        const isWav = binary.charCodeAt(0) === 0x52;
        mime = isWav ? 'audio/wav' : 'audio/opus';
      } catch { mime = 'audio/opus'; }
      const audio = new Audio(`data:${mime};base64,${base64}`);
      audio.onended = () => setIsSpeaking(false);
      audio.onerror = () => {
        console.warn('Backend audio decode failed — falling back to browser TTS');
        setIsSpeaking(false);
      };
      audio.play().catch(e => {
        console.error('Audio play() failed:', e);
        setIsSpeaking(false);
      });
    } catch (e) {
      console.error('playAudio error:', e);
      setIsSpeaking(false);
    }
  };

  const connectWebSocket = (url) => {
    if (ws.current) ws.current.close();
    ws.current = new WebSocket(url);

    ws.current.onopen = () => {
      setIsConnected(true);
      reconnectAttempts.current = 0;
      setDisplayReconnectAttempts(0);
      setAgentStatus('Connected. Your interviewer is ready.');

      // Phase 2.3: Handle reconnection — sync queued answers if any
      if (disconnectStartTime.current) {
        const offlineDuration = Date.now() - disconnectStartTime.current;
        disconnectStartTime.current = null;

        if (offlineDuration > offlineThresholdMs || getQueueLength() > 0) {
          // Was offline long enough or has queued answers — sync them
          setConnectionStatus('syncing');
          setAgentStatus('Reconnected! Syncing queued answers...');
          syncQueue(ws.current).then(({ synced, failed }) => {
            setSyncProgress({ synced, total: synced + failed });
            setQueuedCount(getQueueLength());
            setTimeout(() => {
              setConnectionStatus('connected');
              setSyncProgress(null);
              setAgentStatus(`Synced ${synced} answer(s). Interview resumed.`);
            }, 2000);
          });
        } else {
          // Brief disconnect — seamless resume
          setConnectionStatus('connected');
          setAgentStatus('Connection restored. Continuing interview...');
        }
      } else {
        setConnectionStatus('connected');
      }
    };

    ws.current.onclose = () => {
      setIsConnected(false);
      if (isIntentionalClose.current) return;

      // Phase 2.3: Track disconnect start time
      disconnectStartTime.current = Date.now();

      // Exponential back-off: 1s, 2s, 4s, 8s, 16s, max 30s
      const delay = Math.min(1000 * 2 ** reconnectAttempts.current, 30000);
      reconnectAttempts.current += 1;
      setDisplayReconnectAttempts(reconnectAttempts.current);

      // Phase 2.3: Update connection status based on duration
      if (delay > offlineThresholdMs || reconnectAttempts.current > 4) {
        setConnectionStatus('offline');
        setQueuedCount(getQueueLength());
        setAgentStatus(`Connection lost. Answers will be saved locally.`);
      } else {
        setConnectionStatus('reconnecting');
        setAgentStatus(`Connection lost. Reconnecting in ${delay / 1000}s...`);
      }

      reconnectTimer.current = setTimeout(() => connectWebSocket(url), delay);
    };

    ws.current.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === 'question') {
        setCurrentQuestion(payload.data);
        if (payload.job_role) setJobRole(payload.job_role);
        setIsCodingMode(payload.is_coding || false);
        if (payload.language) setCodeLanguage(payload.language);
        setAgentStatus('Question ready. We are waiting for your response.');
        // Phase 2.2: Update skills covered from question data
        if (payload.data?.skill_tested) {
          setSkillsCovered(prev => {
            // Increment if this is a new skill (simplified tracking)
            return Math.min(prev + 1, totalSkills);
          });
        }
        if (payload.audio) {
          playAudio(payload.audio);
        } else {
          // Free browser TTS fallback — works on every device, zero cost
          const q = payload.data?.question;
          if (q) speakWithBrowserTTS(q);
        }
      } else if (payload.type === 'supervisor_mode') {
        setSupervisorMode(payload.mode);
      } else if (payload.type === 'status') {
        setAgentStatus(payload.data);
      } else if (payload.type === 'execution_result') {
        setCodeResult(payload.data);
        setAgentStatus('Code submitted. Reviewing your solution now.');
      } else if (payload.type === 'complete') {
        setAgentStatus('Interview complete. Preparing your report.');
        const sid = payload.session_id ?? null;
        setCompletedSessionId(sid);
        isIntentionalClose.current = true;
        // Exit fullscreen on interview complete
        if (document.fullscreenElement) {
          document.exitFullscreen();
        }
        // Navigate to report for all session types — practice sessions have reports too
        setTimeout(() => {
          if (document.fullscreenElement) {
            document.exitFullscreen();
          }
          if (sid) {
            navigate(`/report/${sid}`);
          } else {
            navigate('/dashboard');
          }
        }, 2000);
      } else if (payload.type === 'error') {
        setAgentStatus(`⚠ ${payload.data}`);
      } else if (payload.type === 'metrics_update') {
        // Real-time metrics update during interview
        setAgentStatus('Metrics updated based on your response.');
        // Could display live metrics in a dedicated UI element
        console.log('Metrics update:', payload.data);
      } else if (payload.type === 'copilot_update') {
        setIsCopilotLoading(false);
        if (payload.data) {
          setCopilotSuggestions(prev => [...prev, payload.data]);
        }
        setAgentStatus('Co-Pilot: Suggestion generated.');
      } else if (payload.type === 'advisor_suggestion') {
        // Phase 1A: Advisor suggestion received (primarily for HR, but candidate sees status)
        // Candidate continues normally — HR decides when to close
        console.log('Advisor suggestion:', payload.data);
        // Phase 2.2: Update progress bar advisor state
        if (payload.data?.ready_to_close) {
          setAdvisorReady(true);
          setAdvisorConfidence(payload.data.confidence || 0);
        }
      }
    };
  };

  useEffect(() => {
    if (!ready) return;

    const driveId = searchParams.get('drive_id');
    const token = searchParams.get('token');
    const scheduledSessionId = searchParams.get('scheduled_session_id');

    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    let wsBase = apiBase;
    if (apiBase.startsWith('https://')) {
      wsBase = 'wss://' + apiBase.substring(8);
    } else if (apiBase.startsWith('http://')) {
      wsBase = 'ws://' + apiBase.substring(7);
    }
    let socketUrl = `${wsBase}/interview/ws/${resolvedSessionId}`;
    const queryParams = [];
    if (driveId && token) {
      queryParams.push(`drive_id=${driveId}`);
      queryParams.push(`token=${token}`);
    } else if (scheduledSessionId) {
      queryParams.push(`scheduled_session_id=${scheduledSessionId}`);
      const jwt = localStorage.getItem('token');
      if (jwt) queryParams.push(`auth_token=${encodeURIComponent(jwt)}`);
    } else {
      const jwt = localStorage.getItem('token');
      if (jwt) queryParams.push(`auth_token=${encodeURIComponent(jwt)}`);
    }
    if (queryParams.length > 0) socketUrl += `?${queryParams.join('&')}`;
    socketUrlRef.current = socketUrl;
    isIntentionalClose.current = false;
    connectWebSocket(socketUrl);

    const timer = setInterval(() => setTimeLeft(p => p + 1), 1000);
    return () => {
      isIntentionalClose.current = true;
      clearTimeout(reconnectTimer.current);
      ws.current?.close();
      clearInterval(timer);
      if (silenceIntervalRef.current) {
        clearInterval(silenceIntervalRef.current);
        silenceIntervalRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
        audioContextRef.current = null;
      }
      // Phase 2.3: Reset connection state on cleanup
      setConnectionStatus('connected');
      disconnectStartTime.current = null;
    };
  }, [ready, resolvedSessionId]); // eslint-disable-line react-hooks/exhaustive-deps

  // Check voice capability once ready
  useEffect(() => {
    if (!ready) return;
    (async () => {
      try {
        const resp = await apiClient.get('/voice/capabilities');
        setVoiceAvailable(!!resp.data?.voice_available);
      } catch {
        setVoiceAvailable(false);
      }
    })();
  }, [ready]);

  const toggleRecording = async () => {
    // Track user activity for timeout
    lastUserActivityRef.current = Date.now();
    setShowTimeoutConfirm(false);
    clearTimeout(noResponseTimerRef.current);

    if (isRecording) {
      // Stop recording - this will trigger the onstop event handler defined below
      mediaRecorder.current?.stop();
      setIsRecording(false);
      mediaRecorder.current?.stream.getTracks().forEach(t => t.stop());

      if (silenceIntervalRef.current) {
        clearInterval(silenceIntervalRef.current);
        silenceIntervalRef.current = null;
      }
      if (audioContextRef.current) {
        audioContextRef.current.close().catch(() => {});
        audioContextRef.current = null;
      }
    } else {
      audioChunks.current = [];
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorder.current = new MediaRecorder(stream);
        mediaRecorder.current.ondataavailable = (e) => {
          if (e.data.size > 0) audioChunks.current.push(e.data);
        };
        mediaRecorder.current.onstop = () => {
          setAgentStatus('Processing and submitting your answer...');
          if (audioChunks.current.length > 0) {
            const blob = new Blob(audioChunks.current, { type: 'audio/webm' });
            if (ws.current?.readyState === WebSocket.OPEN) {
              ws.current.send(blob);
              audioChunks.current = [];
              setAgentStatus('Answer submitted. Reviewing your response...');
            } else {
              // Offline — queue the audio answer as text placeholder
              enqueueAnswer('audio_pending', { size: blob.size, type: blob.type });
              audioChunks.current = [];
              setQueuedCount(getQueueLength());
              setAgentStatus('Answer saved locally. Will sync when reconnected.');
            }
          } else {
            setAgentStatus('No audio recorded.');
          }
        };
        mediaRecorder.current.start();
        setIsRecording(true);
        setAgentStatus('Listening... Speak your answer.');

        // Initialize silence detection
        try {
          const AudioContextClass = window.AudioContext || window.webkitAudioContext;
          if (AudioContextClass) {
            const audioContext = new AudioContextClass();
            audioContextRef.current = audioContext;
            const source = audioContext.createMediaStreamSource(stream);
            const analyser = audioContext.createAnalyser();
            analyser.fftSize = 256;
            source.connect(analyser);

            const bufferLength = analyser.frequencyBinCount;
            const dataArray = new Uint8Array(bufferLength);
            let silenceStart = Date.now();

            const checkSilence = () => {
              if (!isRecordingRef.current) {
                if (silenceIntervalRef.current) {
                  clearInterval(silenceIntervalRef.current);
                  silenceIntervalRef.current = null;
                }
                setSilenceDuration(0);
                setIsSilent(false);
                return;
              }
              analyser.getByteFrequencyData(dataArray);
              let sum = 0;
              for (let i = 0; i < bufferLength; i++) {
                sum += dataArray[i];
              }
              const average = sum / bufferLength;

              // If voice level falls below noise floor, count as silence.
              if (average < 5) {
                const elapsed = Date.now() - silenceStart;
                setSilenceDuration(elapsed);
                setIsSilent(true);
                if (elapsed > 4000) { // 4 seconds of silence
                  if (silenceIntervalRef.current) {
                    clearInterval(silenceIntervalRef.current);
                    silenceIntervalRef.current = null;
                  }
                  setSilenceDuration(0);
                  setIsSilent(false);
                  if (isRecordingRef.current) {
                    toggleRecordingRef.current?.();
                    setAgentStatus('Silence detected. Auto-submitting response...');
                  }
                }
              } else {
                silenceStart = Date.now();
                setSilenceDuration(0);
                setIsSilent(false);
              }
            };
            silenceIntervalRef.current = setInterval(checkSilence, 200);
          }
        } catch (err) {
          console.warn("Silence detection context failed to start:", err);
        }

      } catch {
        alert("Microphone access failed.");
      }
    }
  };

  // Sync toggleRecording into ref after it is defined
  useEffect(() => {
    toggleRecordingRef.current = toggleRecording;
  });

  useEffect(() => {
    submitCodeRef.current = submitCode;
  });

  useEffect(() => {
    submitTextAnswerRef.current = submitTextAnswer;
  });

  // Proctor tab switch detection
  useEffect(() => {
    if (!ready || !isConnected) return;

    const handleVisibilityChange = () => {
      if (document.hidden) {
        setTabSwitches(prev => {
          const nextCount = prev + 1;
          
          // Send to backend via websocket
          if (ws.current?.readyState === WebSocket.OPEN) {
            ws.current.send(JSON.stringify({
              type: 'proctor_event',
              event: 'tab_switch',
              timestamp: Date.now()
            }));
          }
          
          return nextCount;
        });
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [ready, isConnected]);

  // Proctor dev simulation keyboard shortcut: Ctrl+Shift+1/2/3 for simulated video proctoring events
  useEffect(() => {
    if (!ready || !isConnected) return;

    const handleKeyDown = (e) => {
      if (e.ctrlKey && e.shiftKey) {
        let eventType = null;
        if (e.key === '1') {
          eventType = 'multiple_faces';
        } else if (e.key === '2') {
          eventType = 'no_face';
        } else if (e.key === '3') {
          eventType = 'gaze_deviation';
        }

        if (eventType && ws.current?.readyState === WebSocket.OPEN) {
          ws.current.send(JSON.stringify({
            type: 'proctor_event',
            event: eventType,
            timestamp: Date.now(),
            confidence: 0.95,
            duration_seconds: 2.5
          }));
          addToast({
            type: 'warning',
            title: 'Proctor Event Simulated',
            message: `Sent simulated "${eventType}" event to proctor server.`,
          });
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => {
      window.removeEventListener('keydown', handleKeyDown);
    };
  }, [ready, isConnected, addToast]);

  const handleEndInterview = useCallback(() => {
    isIntentionalClose.current = true;
    clearTimeout(reconnectTimer.current);
    ws.current?.close();
    // Exit fullscreen on interview end
    if (document.fullscreenElement) {
      document.exitFullscreen();
    }
    if (completedSessionId) {
      navigate(`/report/${completedSessionId}`);
    } else {
      navigate('/');
    }
  }, [completedSessionId, navigate]);

  // Auto-submit on text change and timeout detection
  useEffect(() => {
    const checkActivity = setInterval(() => {
      if (!isConnected || !currentQuestion) return;

      const timeSinceActivity = Date.now() - lastUserActivityRef.current;

      // After 60 seconds of no activity, show a gentle nudge
      if (timeSinceActivity > 60000 && !showTimeoutConfirm) {
        setShowTimeoutConfirm(true);
        setAgentStatus("Take your time, I'm here when you're ready. No pressure.");
        noResponseTimerRef.current = setTimeout(() => {
          // If still no response after another 2 minutes, end interview
          setAgentStatus("It looks like you've been away for a while. I'll wrap up the interview now — feel free to start a new one anytime.");
          setTimeout(() => {
            handleEndInterview();
          }, 3000);
        }, 120000);
      }
    }, 1000);

    return () => clearInterval(checkActivity);
  }, [isConnected, currentQuestion, showTimeoutConfirm, handleEndInterview]);

  // Add activity listeners
  useEffect(() => {
    const handleActivity = () => updateActivity();
    window.addEventListener('click', handleActivity);
    window.addEventListener('keypress', handleActivity);
    return () => {
      window.removeEventListener('click', handleActivity);
      window.removeEventListener('keypress', handleActivity);
    };
  }, [updateActivity]);

  const requestCopilotHint = () => {
    updateActivity();
    if (ws.current?.readyState === WebSocket.OPEN) {
      setIsCopilotLoading(true);
      setAgentStatus('AI Co-Pilot: Formulating hint...');
      ws.current.send(JSON.stringify({ type: 'copilot_request', data: code }));
    } else {
      alert("Co-Pilot unavailable: WebSocket is disconnected.");
    }
  };

  // Phase 2.3: Save Draft handler
  const handleSaveDraft = useCallback(() => {
    const draft = {
      sessionId: resolvedSessionId,
      currentQuestion: currentQuestion,
      code,
      manualText,
      timeLeft,
      isCodingMode,
      savedAt: Date.now(),
    };
    const success = saveDraft(draft);
    if (success) {
      setAgentStatus('Draft saved locally.');
    } else {
      setAgentStatus('Failed to save draft.');
    }
  }, [resolvedSessionId, currentQuestion, code, manualText, timeLeft, isCodingMode]);

  const formatTimer = (s) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;

  // Phase 2.1: Show desktop banner on mobile (after all hooks are called)
  if (isMobile) {
    return <DesktopOnlyBanner />;
  }

  if (!ready) return <ReadyCheckWizard onReady={() => setReady(true)} />;

  return (
    <div className="fixed inset-0 bg-[#020617] text-white flex flex-col font-sans overflow-hidden">

      {/* WARNING BANNER FOR TAB SWITCH */}
      {tabSwitches > 3 && (
        <div className="bg-red-500/10 border-b border-red-500/20 px-12 py-3 flex items-center justify-between z-40 shrink-0 backdrop-blur-md">
          <span className="text-xs font-black uppercase tracking-widest text-red-400 flex items-center">
            <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse mr-2" />
            Critical Proctor Warning: Excessive tab switching detected ({tabSwitches} switches). Your actions are being recorded and flagged for review.
          </span>
        </div>
      )}

      {/* TOP NAV */}
      <div className="h-20 border-b border-white/5 bg-[#020617]/50 backdrop-blur-xl px-12 flex items-center justify-between z-50 shrink-0">
        <div className="flex items-center space-x-12">
          <div className="text-3xl font-black tracking-tighter flex items-center">
            <div className="w-8 h-8 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-lg mr-2" />
            Autergo
          </div>
          <div className="h-8 w-px bg-white/10" />
          <div className="space-y-0.5">
            <h2 className="text-sm font-black uppercase tracking-widest text-white">{jobRole}</h2>
            <ConnectionStatus
              status={connectionStatus}
              reconnectAttempts={displayReconnectAttempts}
              queuedCount={queuedCount}
              syncProgress={syncProgress}
              onSaveDraft={handleSaveDraft}
            />
          </div>
        </div>

        <div className="flex items-center space-x-8">
          {/* Phase 2.2: Progress bar in top nav */}
          <div className="w-80">
            <InterviewProgressBar
              currentQuestion={currentQuestion?.id || 1}
              skillsCovered={skillsCovered}
              totalSkills={totalSkills}
              timeElapsed={timeLeft}
              advisorReady={advisorReady}
              advisorConfidence={advisorConfidence}
            />
          </div>

          <button onClick={handleEndInterview}
            className="bg-red-500/10 border border-red-500/20 text-red-500 px-6 py-3 rounded-2xl text-xs font-black uppercase tracking-widest hover:bg-red-500 hover:text-white transition-all flex items-center space-x-2">
            <PhoneOff size={16} />
            <span>End Interview</span>
          </button>

          <div className="flex items-center space-x-3 pl-6 border-l border-white/10">
            <div className="text-right">
              <p className="text-xs font-black text-white uppercase tracking-tight">{user?.first_name || 'Candidate'}</p>
              <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">Candidate</p>
            </div>
            <div className="w-10 h-10 bg-slate-800 rounded-xl flex items-center justify-center border border-white/10">
              <User size={20} className="text-slate-500" />
            </div>
          </div>
        </div>
      </div>

      {/* MAIN STAGE */}
      <div className="flex-1 relative flex flex-col items-center justify-center p-12 overflow-hidden">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

        <div className="absolute top-6 right-6 flex items-center space-x-2 bg-white/5 border border-white/10 px-3 py-1.5 rounded-xl">
          <SignalHigh size={14} className={
            connectionStatus === 'connected' ? 'text-emerald-500' :
            connectionStatus === 'reconnecting' ? 'text-amber-500 animate-pulse' :
            connectionStatus === 'offline' ? 'text-red-500' :
            connectionStatus === 'syncing' ? 'text-blue-500 animate-pulse' :
            'text-slate-500'
          } />
        </div>

        {/* Video Preview */}
        {isVideoOn && videoStream && supervisorMode !== 'hr_takeover' && (
          <div className="absolute top-16 right-6 w-40 h-28 rounded-2xl overflow-hidden border border-white/10 shadow-[0_4px_30px_rgba(0,0,0,0.5)] backdrop-blur-md z-20">
            <video
              ref={videoRef}
              autoPlay
              muted
              playsInline
              className="w-full h-full object-cover"
            />
            <div className="absolute bottom-2 left-2 bg-black/60 backdrop-blur px-2 py-0.5 rounded-md text-[8px] font-black uppercase tracking-wider text-white">
              You
            </div>
          </div>
        )}

        <div className="relative z-10 w-full max-w-5xl flex flex-col items-center">
          
          {/* Toggle between AI Avatar and Coding Sandbox */}
          {!isCodingMode ? (
            <div className="flex flex-col items-center space-y-12">
              <div className="relative">
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[140%] h-[140%] border border-white/5 rounded-full" />
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[160%] h-[160%] border border-white/5 rounded-full opacity-50" />

                <div className="w-72 h-72 rounded-[3rem] bg-slate-900 border border-white/10 overflow-hidden relative shadow-[0_0_100px_rgba(147,51,234,0.1)]">
                  <img
                    src="https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&q=80&w=1000"
                    alt="Interviewer"
                    className={`w-full h-full object-cover grayscale transition-all duration-500 ${isSpeaking ? 'scale-110 opacity-100' : 'opacity-80'}`}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-[#020617] via-transparent to-transparent" />
                  {isSpeaking && (
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="flex space-x-1">
                        {[1, 2, 3, 4, 5].map(i => (
                          <motion.div key={i} animate={{ height: [8, 28, 8] }}
                            transition={{ duration: 0.6, repeat: Infinity, delay: i * 0.1 }}
                            className="w-1.5 bg-purple-500 rounded-full" />
                        ))}
                      </div>
                    </div>
                  )}
                  <div className="absolute top-4 left-4 bg-slate-900/60 backdrop-blur border border-white/10 px-3 py-1.5 rounded-xl flex items-center space-x-2">
                    <div className="w-1.5 h-1.5 bg-purple-500 rounded-full animate-pulse" />
                    <span className="text-[8px] font-black text-white uppercase tracking-[0.2em]">Interviewer</span>
                  </div>
                </div>

                <motion.div
                  key={currentQuestion?.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute top-1/2 left-1/2 -translate-x-1/2 translate-y-[160px] w-[560px] bg-[#020617]/60 backdrop-blur-3xl border border-purple-500/20 px-10 py-8 rounded-3xl shadow-2xl z-20 text-center"
                >
                  <p className="text-xl font-bold text-white leading-snug italic">
                    "{currentQuestion?.question || 'Initializing your assessment...'}"
                  </p>
                </motion.div>
              </div>
            </div>
          ) : (
            <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} 
              className="w-full h-[60vh] min-h-[450px] grid grid-cols-10 gap-6">
              
              {/* Left Sandbox (7 cols) */}
              <div className="col-span-7 bg-[#0a0f1e] border border-white/10 rounded-[2.5rem] overflow-hidden shadow-2xl relative flex flex-col">
                 <div className="h-12 bg-white/5 border-b border-white/5 px-6 flex items-center justify-between">
                   <div className="flex items-center space-x-2">
                     <Terminal size={16} className="text-purple-400" />
                     <span className="text-[10px] font-black uppercase tracking-widest text-slate-400">Technical Sandbox / {codeLanguage}</span>
                   </div>
                   <div className="flex items-center space-x-4">
                     <p className="text-xs font-bold text-slate-500 italic">Phase: {currentQuestion?.category}</p>
                   </div>
                 </div>
                 <div className="flex-1 min-h-0 relative">
                   <Editor
                     height="100%"
                     theme="vs-dark"
                     language={codeLanguage}
                     value={code}
                     onChange={(val) => setCode(val)}
                     options={{
                       fontSize: 14,
                       minimap: { enabled: false },
                       padding: { top: 20 },
                       scrollBeyondLastLine: false,
                       backgroundColor: 'transparent'
                     }}
                   />
                 </div>
                 <div className="h-20 border-t border-white/5 px-6 flex items-center justify-between bg-[#0a0f1e]/80">
                   <div>
                     {codeResult && (
                       <div className={`px-4 py-2 rounded-xl text-[10px] font-black uppercase tracking-widest border ${
                         codeResult.status === 'Accepted' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'
                       }`}>
                         {codeResult.status} {codeResult.time ? `· ${codeResult.time}ms` : ''}
                       </div>
                     )}
                   </div>
                   <motion.button 
                     onClick={submitCode}
                     whileHover={{ scale: 1.04, boxShadow: '0 0 40px rgba(124,58,237,0.35)' }}
                     whileTap={{ scale: 0.96 }}
                     className="group relative bg-gradient-to-r from-purple-600/20 to-indigo-600/20 border border-purple-500/30 text-purple-200 hover:from-purple-600 hover:to-indigo-600 hover:text-white px-7 py-3.5 rounded-2xl text-xs font-black uppercase tracking-widest shadow-[0_0_30px_rgba(124,58,237,0.15)] flex items-center space-x-2.5 transition-all backdrop-blur-xl overflow-hidden"
                   >
                     <div className="absolute inset-0 bg-gradient-to-r from-purple-500/0 via-white/5 to-purple-500/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                     <Play size={15} fill="currentColor" className="relative z-10" />
                     <span className="relative z-10">Execute & Submit</span>
                     <Send size={13} className="relative z-10 opacity-60 group-hover:opacity-100 transition-opacity" />
                   </motion.button>
                 </div>
              </div>

              {/* Right Co-Pilot Panel (3 cols) */}
              <div className="col-span-3 bg-white/5 border border-white/10 rounded-[2.5rem] backdrop-blur-xl p-6 flex flex-col justify-between shadow-2xl relative overflow-hidden">
                <div className="absolute top-[-50px] right-[-50px] w-[150px] h-[150px] bg-purple-600/10 blur-[50px] rounded-full pointer-events-none" />
                
                <div className="flex-1 flex flex-col min-h-0">
                  <div className="flex items-center space-x-3 mb-4 pb-4 border-b border-white/5">
                    <div className="w-8 h-8 bg-purple-600/20 text-purple-400 border border-purple-500/30 rounded-xl flex items-center justify-center">
                      <BrainCircuit size={18} />
                    </div>
                    <div>
                      <h3 className="text-xs font-black uppercase tracking-widest text-white">AI Co-Pilot Partner</h3>
                      <p className="text-[9px] font-bold text-slate-500 uppercase tracking-tight">Active Assistant</p>
                    </div>
                  </div>

                  <div className="flex-1 overflow-y-auto space-y-4 pr-1 min-h-0 scrollbar-thin">
                    {copilotSuggestions.length === 0 ? (
                      <div className="h-full flex flex-col items-center justify-center text-center p-4">
                        <Terminal className="text-slate-600 mb-3" size={28} />
                        <p className="text-slate-400 text-xs font-bold leading-relaxed">Co-Pilot is listening. Stuck? Press summon below for a conceptual hint.</p>
                      </div>
                    ) : (
                      copilotSuggestions.map((suggestion, idx) => (
                        <div key={idx} className="bg-slate-950/40 border border-purple-500/10 rounded-2xl p-4 text-[11px] leading-relaxed relative">
                          <p className="text-purple-400 font-black uppercase text-[8px] tracking-widest mb-1.5 flex items-center">
                            <span>Suggestion {idx + 1}</span>
                            <span className="mx-2 opacity-30">·</span>
                            <span className="opacity-60">{suggestion.trigger === 'manual_request' ? 'Requested' : 'Auto-Assist'}</span>
                          </p>
                          <p className="text-slate-300 font-medium italic">"{suggestion.hint}"</p>
                        </div>
                      ))
                    )}
                    {isCopilotLoading && (
                      <div className="bg-purple-600/5 border border-purple-500/10 rounded-2xl p-4 flex items-center space-x-3">
                        <Loader2 className="animate-spin text-purple-400" size={16} />
                        <span className="text-[10px] font-black uppercase tracking-widest text-purple-400">Co-Pilot is thinking...</span>
                      </div>
                    )}
                  </div>
                </div>

                <button 
                  disabled={isCopilotLoading}
                  onClick={requestCopilotHint}
                  className={`w-full mt-4 py-3.5 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${
                    isCopilotLoading ? 'bg-purple-500/20 text-purple-300 border border-purple-500/20 cursor-not-allowed' : 'bg-white text-slate-950 hover:bg-purple-400 hover:text-white shadow-lg active:scale-95'
                  }`}
                >
                  Summon Co-Pilot
                </button>
              </div>

            </motion.div>
          )}

          {/* Control bar */}
          <div className={`flex items-center space-x-6 z-30 ${isCodingMode ? 'pt-8' : 'pt-20'}`}>
            <button onClick={toggleVideo}
              className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${isVideoOn ? 'bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10' : 'bg-red-500 text-white'}`}>
              {isVideoOn ? <Video size={20} /> : <VideoOff size={20} />}
            </button>
            <button onClick={toggleRecording}
              className={`w-14 h-14 rounded-full flex items-center justify-center transition-all ${isRecording ? 'bg-red-500 text-white shadow-xl shadow-red-500/30' : 'bg-white/5 border border-white/10 text-slate-400 hover:bg-white/10'}`}>
              {isRecording ? <MicOff size={20} /> : <Mic size={20} />}
            </button>
            <button onClick={handleEndInterview}
              className="w-14 h-14 bg-red-500 rounded-full flex items-center justify-center text-white shadow-xl shadow-red-500/20 hover:bg-red-600 transition-all">
              <PhoneOff size={20} />
            </button>
          </div>
        </div>
      </div>

      {/* BOTTOM RECORDING PANEL */}
      <div className="px-12 pb-10 shrink-0">
        <div className="max-w-5xl mx-auto bg-white/2 border border-white/5 rounded-[2.5rem] p-8 backdrop-blur-xl">

          {/* ── COUNTDOWN PROGRESS BAR ─────────────────────────────────────── */}
          {currentQuestion?.time_limit > 0 && (
            <div className="mb-6">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center space-x-3">
                  <span className={`text-[10px] font-black uppercase tracking-widest ${
                    questionTimeLeft === 0 ? 'text-red-400' :
                    questionTimeLeft < (currentQuestion.time_limit * 0.25) ? 'text-red-400' :
                    questionTimeLeft < (currentQuestion.time_limit * 0.5) ? 'text-amber-400' :
                    'text-emerald-400'
                  }`}>
                    {questionTimeLeft === 0 ? 'Auto-submitting...' : `${questionTimeLeft}s remaining`}
                  </span>
                  {questionTimeLeft > 0 && questionTimeLeft < 10 && (
                    <motion.span
                      animate={{ opacity: [1, 0.3, 1] }}
                      transition={{ duration: 0.6, repeat: Infinity }}
                      className="text-[9px] font-black uppercase tracking-widest text-red-500"
                    >
                      ⚡ Hurry up!
                    </motion.span>
                  )}
                </div>
                <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {Math.round((questionTimeLeft / currentQuestion.time_limit) * 100)}%
                </span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full rounded-full transition-colors duration-500 ${
                    questionTimeLeft === 0 ? 'bg-red-500' :
                    questionTimeLeft < (currentQuestion.time_limit * 0.25) ? 'bg-gradient-to-r from-red-500 to-red-400' :
                    questionTimeLeft < (currentQuestion.time_limit * 0.5) ? 'bg-gradient-to-r from-amber-500 to-yellow-400' :
                    'bg-gradient-to-r from-emerald-500 to-emerald-400'
                  }`}
                  initial={false}
                  animate={{
                    width: `${(questionTimeLeft / currentQuestion.time_limit) * 100}%`,
                    ...(questionTimeLeft < 10 && questionTimeLeft > 0 ? { opacity: [1, 0.5, 1] } : {})
                  }}
                  transition={{
                    width: { duration: 0.8, ease: 'easeOut' },
                    ...(questionTimeLeft < 10 && questionTimeLeft > 0 ? { opacity: { duration: 0.5, repeat: Infinity } } : {})
                  }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-between items-center mb-6">
            <div className="flex items-center space-x-4">
              <span className="text-sm font-black uppercase tracking-widest text-white">Your Answer</span>
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${voiceAvailable ? (isRecording ? 'bg-red-500/10 text-red-400 border-red-500/20' : 'bg-emerald-500/10 text-emerald-500 border-emerald-500/20') : 'bg-gray-500/40 text-slate-300 border-gray-500/40'}`}>
                <div className={`w-1.5 h-1.5 rounded-full animate-pulse ${isRecording ? 'bg-red-400' : voiceAvailable ? 'bg-emerald-500' : 'bg-slate-300'}`} />
                <span>{voiceAvailable ? (isRecording ? 'Recording...' : 'Voice Ready') : 'Voice Unavailable'}</span>
              </div>
              <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${isVideoOn ? 'bg-purple-500/10 text-purple-400 border-purple-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'}`}>
                <div className={`w-1.5 h-1.5 rounded-full ${isVideoOn ? 'bg-purple-400 animate-pulse' : 'bg-red-500'}`} />
                <span>{isVideoOn ? 'Camera Active' : 'Camera Off'}</span>
              </div>
              {currentQuestion?.time_limit && (
                <div className={`flex items-center space-x-2 px-3 py-1 rounded-full text-[10px] font-black uppercase tracking-widest border ${
                  questionTimeLeft === 0 ? 'bg-red-500/20 text-red-300 border-red-500/30' :
                  questionTimeLeft < 10 ? 'bg-red-500/10 text-red-400 border-red-500/20 animate-pulse' :
                  'bg-white/5 text-slate-400 border-white/10'
                }`}>
                   <span>{questionTimeLeft === 0 ? 'Auto-submitting...' : `Time: ${questionTimeLeft}s`}</span>
                </div>
              )}
              <span className="text-xs text-slate-500 font-bold uppercase tracking-widest">{agentStatus}</span>
            </div>
            <div className="text-xl font-mono font-bold tracking-tight text-white opacity-60">
              {formatTimer(timeLeft)}
            </div>
          </div>

          <Waveform isRecording={isRecording} />

          {/* ── SILENCE DETECTION VISUAL INDICATOR ─────────────────────────── */}
          <AnimatePresence>
            {isRecording && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                className="mt-4 overflow-hidden"
              >
                <div className="flex items-center justify-center space-x-4 py-3 px-6 bg-white/[0.02] border border-white/5 rounded-2xl">
                  {/* Pulsing microphone indicator */}
                  <motion.div
                    animate={{ scale: [1, 1.2, 1], opacity: [0.7, 1, 0.7] }}
                    transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
                    className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      isSilent ? 'bg-amber-500/15 border border-amber-500/30' : 'bg-purple-500/15 border border-purple-500/30'
                    }`}
                  >
                    <AudioLines size={16} className={isSilent ? 'text-amber-400' : 'text-purple-400'} />
                  </motion.div>

                  {/* Silence status text */}
                  <div className="flex flex-col">
                    {isSilent && silenceDuration > 500 ? (
                      <>
                        <span className="text-[10px] font-black uppercase tracking-widest text-amber-400">
                          {silenceDuration > 3000
                            ? `Auto-submitting in ${Math.max(0, Math.ceil((4000 - silenceDuration) / 1000))}s...`
                            : 'Detecting silence...'
                          }
                        </span>
                        {/* Silence threshold progress */}
                        <div className="w-40 h-1 bg-white/5 rounded-full mt-1.5 overflow-hidden">
                          <motion.div
                            className="h-full rounded-full bg-gradient-to-r from-amber-500 to-red-500"
                            animate={{ width: `${Math.min((silenceDuration / 4000) * 100, 100)}%` }}
                            transition={{ duration: 0.2 }}
                          />
                        </div>
                      </>
                    ) : (
                      <span className="text-[10px] font-black uppercase tracking-widest text-purple-400/70">
                        Listening actively...
                      </span>
                    )}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <div className="flex justify-between items-center mt-6">
            <motion.button
              onClick={toggleRecording}
              whileHover={{ scale: 1.05, boxShadow: isRecording ? '0 0 40px rgba(239,68,68,0.35)' : '0 0 40px rgba(124,58,237,0.35)' }}
              whileTap={{ scale: 0.95 }}
              className={`group relative flex items-center space-x-2.5 px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-xs transition-all backdrop-blur-md overflow-hidden ${
                isRecording 
                  ? 'bg-gradient-to-r from-red-600/20 via-rose-600/25 to-red-600/20 border border-red-500/30 text-red-400 hover:from-red-600 hover:to-rose-600 hover:text-white shadow-[0_0_30px_rgba(239,68,68,0.15)]' 
                  : 'bg-gradient-to-r from-purple-600/20 via-indigo-600/25 to-purple-600/20 border border-purple-500/30 text-purple-300 hover:from-purple-600 hover:to-indigo-600 hover:text-white shadow-[0_0_30px_rgba(124,58,237,0.15)]'
              }`}
            >
              {/* Shimmer effect */}
              <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/5 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
              
              {isRecording ? (
                <>
                  <Send size={14} className="relative z-10 animate-pulse text-red-400 group-hover:text-white" />
                  <span className="relative z-10">Stop & Send</span>
                </>
              ) : (
                <>
                  <Mic size={14} className="relative z-10 text-purple-400 group-hover:text-white" />
                  <span className="relative z-10">Start Responding</span>
                </>
              )}
            </motion.button>

            <div className="relative flex flex-col items-end space-y-2">
              <AnimatePresence>
                {showTextInput && (
                  <motion.div initial={{ opacity: 0, y: 10, scale: 0.95 }} animate={{ opacity: 1, y: 0, scale: 1 }} exit={{ opacity: 0, y: 10, scale: 0.95 }}
                    className="absolute top-[-220px] right-0 w-96 bg-[#0a0f1e] border border-white/10 p-6 rounded-3xl shadow-2xl z-[60]">
                    <p className="text-xs font-black text-slate-400 uppercase tracking-widest mb-3">Type Your Answer</p>
                    <textarea
                      autoFocus
                      className="w-full h-32 bg-white/5 border border-white/10 rounded-2xl p-4 text-sm text-white focus:ring-2 focus:ring-purple-500 outline-none resize-none mb-4"
                      placeholder="Type your answer here..."
                      value={manualText}
                      onChange={(e) => setManualText(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter' && !e.shiftKey) {
                          e.preventDefault();
                          submitTextAnswer();
                        }
                      }}
                    />
                    <div className="flex justify-end space-x-3">
                      <button onClick={() => setShowTextInput(false)} className="px-4 py-2 text-[10px] font-black uppercase text-slate-500 hover:text-white transition-colors">Cancel</button>

                      {/* ── PREMIUM SUBMIT BUTTON ──────────────────────────────── */}
                      <motion.button
                        onClick={submitTextAnswer}
                        disabled={!manualText.trim()}
                        whileHover={manualText.trim() ? { scale: 1.05, boxShadow: '0 0 50px rgba(124,58,237,0.4)' } : {}}
                        whileTap={manualText.trim() ? { scale: 0.95 } : {}}
                        className={`group relative flex items-center space-x-2.5 px-7 py-3 rounded-2xl text-[10px] font-black uppercase tracking-widest transition-all overflow-hidden ${
                          manualText.trim()
                            ? 'bg-gradient-to-r from-purple-600 to-indigo-600 text-white shadow-[0_0_35px_rgba(124,58,237,0.3)] border border-purple-400/30 backdrop-blur-xl cursor-pointer'
                            : 'bg-white/5 text-slate-600 border border-white/5 cursor-not-allowed'
                        }`}
                      >
                        {/* Animated shimmer on hover */}
                        {manualText.trim() && (
                          <div className="absolute inset-0 bg-gradient-to-r from-white/0 via-white/10 to-white/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                        )}

                        {/* Countdown ring SVG when timer is low */}
                        {currentQuestion?.time_limit > 0 && questionTimeLeft > 0 && questionTimeLeft < 10 && manualText.trim() && (
                          <div className="absolute -inset-[2px] rounded-2xl overflow-hidden pointer-events-none">
                            <svg className="w-full h-full" viewBox="0 0 100 40" preserveAspectRatio="none">
                              <motion.rect
                                x="1" y="1" width="98" height="38" rx="14"
                                fill="none"
                                stroke="url(#submitGlow)"
                                strokeWidth="2"
                                strokeDasharray="280"
                                animate={{ strokeDashoffset: [280, 0] }}
                                transition={{ duration: questionTimeLeft, ease: 'linear' }}
                              />
                              <defs>
                                <linearGradient id="submitGlow" x1="0%" y1="0%" x2="100%" y2="0%">
                                  <stop offset="0%" stopColor="#7C3AED" />
                                  <stop offset="50%" stopColor="#818CF8" />
                                  <stop offset="100%" stopColor="#7C3AED" />
                                </linearGradient>
                              </defs>
                            </svg>
                          </div>
                        )}

                        {/* Pulse animation when timer < 10s */}
                        {currentQuestion?.time_limit > 0 && questionTimeLeft > 0 && questionTimeLeft < 10 && manualText.trim() && (
                          <motion.div
                            className="absolute inset-0 rounded-2xl bg-purple-500/20"
                            animate={{ opacity: [0, 0.4, 0] }}
                            transition={{ duration: 0.8, repeat: Infinity }}
                          />
                        )}

                        <Send size={14} className={`relative z-10 ${manualText.trim() ? 'text-white' : 'text-slate-600'}`} />
                        <span className="relative z-10">Submit</span>
                      </motion.button>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              <div className="flex items-center space-x-4">
                {/* Phase 2.3: Save Draft button */}
                <button
                  onClick={handleSaveDraft}
                  className="flex items-center space-x-2 text-slate-500 font-black uppercase tracking-widest text-[10px] hover:text-white transition-colors"
                >
                  <Save size={16} className="text-amber-500" />
                  <span>Save Draft</span>
                </button>

                <button
                  onClick={() => setShowTextInput(!showTextInput)}
                  className="flex items-center space-x-2 text-slate-500 font-black uppercase tracking-widest text-[10px] hover:text-white transition-colors"
                >
                   <Send size={16} className="text-purple-500" />
                   <span>{showTextInput ? 'Close Text Entry' : 'Manual Text Answer'}</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Live Recruiter Takeover Call Panel */}
      {supervisorMode === 'hr_takeover' && (
        <div className="fixed bottom-6 right-6 w-80 bg-slate-950/80 backdrop-blur-md border border-red-500/20 rounded-[2rem] p-4 shadow-2xl z-[150] flex flex-col space-y-4">
          <div className="flex justify-between items-center px-1">
            <span className="text-[10px] font-black uppercase tracking-widest text-red-400 flex items-center space-x-1.5">
              <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
              <span>Recruiter Takeover</span>
            </span>
            <span className="text-[9px] text-slate-500 font-bold uppercase">Live Call</span>
          </div>

          <div className="relative aspect-video rounded-2xl overflow-hidden bg-black/40 border border-white/5">
            {/* Remote Recruiter Stream */}
            {remoteStream ? (
              <video
                ref={supervisorVideoRef}
                autoPlay
                playsInline
                className="w-full h-full object-cover"
              />
            ) : (
              <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 text-xs">
                <Loader2 className="animate-spin text-red-500 mb-2" size={16} />
                <span>Connecting to Recruiter...</span>
              </div>
            )}

            {/* Candidate Local Preview Thumbnail (PiP) */}
            {isVideoOn && videoStream && (
              <div className="absolute bottom-2 right-2 w-24 h-16 rounded-lg overflow-hidden border border-white/10 shadow-lg bg-black z-20">
                <video
                  ref={videoRef}
                  autoPlay
                  muted
                  playsInline
                  className="w-full h-full object-cover"
                />
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default InterviewRoom;
