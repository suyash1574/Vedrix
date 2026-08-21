import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { LineChart, Line, ResponsiveContainer } from 'recharts';
import {
  Briefcase, Plus, Link as LinkIcon, Activity,
  ChevronRight, Copy, CheckCircle2, Clock, LayoutDashboard,
  LogOut, Settings, MoreVertical, X, Loader2, Mail, Send, Menu,
  ChevronDown, Radio, MessageSquareText, Home, Download,
  Play, Target, AlertTriangle, Brain, TrendingUp, Users, Layers
} from 'lucide-react';
import apiClient from '../services/api';
import useAuthStore from '../store/useAuthStore';
import SkillMatrixTab from '../components/SkillMatrixTab';
import AdvisorBadge from '../components/AdvisorBadge';

/* ── MINI SPARKLINE COMPONENT ── */
const MiniSparkline = ({ data, color = '#7c3aed' }) => (
  <ResponsiveContainer width="100%" height={30}>
    <LineChart data={data}>
      <Line type="monotone" dataKey="v" stroke={color} strokeWidth={1.5} dot={false} />
    </LineChart>
  </ResponsiveContainer>
);

/* ── ANIMATED STAT COUNTER ── */
const AnimatedStat = ({ value, suffix = '' }) => {
  const [display, setDisplay] = useState(() => {
    const num = typeof value === 'string' ? parseFloat(value) : value;
    return isNaN(num) ? value : 0;
  });
  const started = useRef(false);
  useEffect(() => {
    if (started.current || value === null || value === undefined) return;
    started.current = true;
    const num = typeof value === 'string' ? parseFloat(value) : value;
    if (isNaN(num)) return;
    const duration = 1200;
    const startTime = performance.now();
    const animate = (now) => {
      const progress = Math.min((now - startTime) / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      setDisplay(Math.round(eased * num * 10) / 10);
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [value]);
  if (value === null || value === undefined) return <>—</>;
  return <>{typeof display === 'number' ? (Number.isInteger(value) ? Math.round(display) : display.toFixed(1)) : value}{suffix}</>;
};

/* ── CREATE/EDIT DRIVE MODAL ── */
const DriveModal = ({ onClose, onSaved, drive = null }) => {
  const [formData, setFormData] = useState({ 
    title: drive?.title || '', 
    job_role: drive?.job_role || '', 
    description: drive?.description || '', 
    skills_required: drive?.skills_required || '' 
  });
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      if (drive) {
        await apiClient.put(`/hr/drives/${drive.id}`, formData);
      } else {
        await apiClient.post('/hr/drives', formData);
      }
      onSaved();
      onClose();
    } catch {
      alert(`Failed to ${drive ? 'update' : 'create'} drive`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-xl overflow-hidden shadow-2xl">
        <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
          <h2 className="text-xl font-bold text-white">{drive ? 'Edit Recruitment Drive' : 'New Recruitment Drive'}</h2>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors"><X size={20} /></button>
        </div>
        <form onSubmit={handleSubmit} className="p-8 space-y-5">
          {[
            { label: 'Drive Title', key: 'title', placeholder: 'e.g. Summer Internship 2026' },
            { label: 'Target Job Role', key: 'job_role', placeholder: 'e.g. Senior Backend Engineer' },
            { label: 'Required Skills (comma separated)', key: 'skills_required', placeholder: 'FastAPI, React, SQLModel' },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">{label}</label>
              <input required={key !== 'skills_required'}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder={placeholder}
                value={formData[key]}
                onChange={(e) => setFormData({ ...formData, [key]: e.target.value })}
              />
            </div>
          ))}
          <button type="submit" disabled={loading}
            className="w-full bg-purple-600 text-white py-4 rounded-2xl font-bold hover:bg-purple-500 shadow-xl shadow-purple-900/30 transition-all flex items-center justify-center">
            {loading ? <Loader2 className="animate-spin" size={20} /> : <span>{drive ? 'Save Changes' : 'Initialize Drive'}</span>}
          </button>
        </form>
      </motion.div>
    </div>
  );
};

/* ── DELETE CONFIRMATION MODAL ── */
const DeleteModal = ({ drive, onClose, onDeleted }) => {
  const [loading, setLoading] = useState(false);

  const handleDelete = async () => {
    setLoading(true);
    try {
      await apiClient.delete(`/hr/drives/${drive.id}`);
      onDeleted();
      onClose();
    } catch {
      alert('Failed to delete drive');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-[#0f172a] border border-red-500/20 rounded-[2rem] w-full max-w-md overflow-hidden shadow-2xl">
        <div className="p-8 text-center space-y-6">
          <div className="w-16 h-16 bg-red-500/10 rounded-full flex items-center justify-center mx-auto text-red-500 mb-2">
            <X size={32} />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white">Delete Drive?</h2>
            <p className="text-sm text-slate-400 mt-2">Are you sure you want to delete <span className="text-white font-bold">{drive.title}</span>? This action cannot be undone and will delete all associated session data.</p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <button onClick={onClose}
              className="bg-white/5 border border-white/10 text-white py-3 rounded-2xl font-bold hover:bg-white/10 transition-all">
              Cancel
            </button>
            <button onClick={handleDelete} disabled={loading}
              className="bg-red-600 text-white py-3 rounded-2xl font-bold hover:bg-red-500 transition-all flex items-center justify-center">
              {loading ? <Loader2 className="animate-spin" size={18} /> : 'Delete Now'}
            </button>
          </div>
        </div>
      </motion.div>
    </div>
  );
};

/* ── BULK INVITE MODAL ── */
const BulkInviteModal = ({ drive, onClose }) => {
  const [emailInput, setEmailInput] = useState('');
  const [expiryHours, setExpiryHours] = useState(72);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const emails = emailInput.split(/[\n,]+/).map(e => e.trim()).filter(Boolean);
    if (!emails.length) return alert('Enter at least one email.');
    setLoading(true);
    try {
      const res = await apiClient.post(`/hr/drives/${drive.id}/bulk-invite`, {
        emails,
        expires_in_hours: expiryHours
      });
      setResult(res.data);
    } catch {
      alert('Failed to send invites');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-xl overflow-hidden shadow-2xl">
        <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold text-white">Bulk Schedule Candidates</h2>
            <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-0.5">{drive.title}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors"><X size={20} /></button>
        </div>

        {result ? (
          <div className="p-8 space-y-6">
            <div className="flex items-center space-x-3 text-emerald-400">
              <CheckCircle2 size={28} />
              <div>
                <p className="font-black text-lg text-white">{result.invited} Invites Generated</p>
                <p className="text-xs text-slate-500 uppercase tracking-widest font-bold">Invitation links are ready to share</p>
              </div>
            </div>
            <div className="space-y-3 max-h-64 overflow-y-auto pr-1">
              {result.links.map((l, i) => (
                <div key={i} className="bg-white/5 border border-white/10 rounded-xl px-4 py-3 flex items-center justify-between gap-3">
                  <p className="text-xs text-slate-400 font-mono truncate flex-1">{l.link}</p>
                  <button onClick={() => navigator.clipboard.writeText(l.link)}
                    className="text-purple-400 hover:text-purple-300 shrink-0"><Copy size={14} /></button>
                </div>
              ))}
            </div>
            <button onClick={onClose}
              className="w-full bg-white/5 border border-white/10 text-white py-3 rounded-2xl font-bold hover:bg-white/10 transition-all">
              Done
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="p-8 space-y-5">
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                Candidate Emails <span className="text-slate-600">(one per line or comma-separated)</span>
              </label>
              <textarea rows={5} value={emailInput} onChange={e => setEmailInput(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all resize-none font-mono text-sm"
                placeholder={"candidate1@company.com\ncandidate2@company.com"} />
            </div>
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                Link Expiry
              </label>
              <div className="relative">
                <select value={expiryHours} onChange={e => setExpiryHours(Number(e.target.value))}
                  className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white focus:ring-2 focus:ring-purple-500 outline-none appearance-none">
                  <option value={24} className="bg-slate-900">24 hours</option>
                  <option value={48} className="bg-slate-900">48 hours</option>
                  <option value={72} className="bg-slate-900">72 hours (default)</option>
                  <option value={168} className="bg-slate-900">7 days</option>
                </select>
                <ChevronDown size={16} className="absolute right-4 top-1/2 -translate-y-1/2 text-slate-500 pointer-events-none" />
              </div>
            </div>
            <button type="submit" disabled={loading}
              className="w-full bg-purple-600 text-white py-4 rounded-2xl font-bold hover:bg-purple-500 shadow-xl shadow-purple-900/30 transition-all flex items-center justify-center space-x-2">
              {loading ? <Loader2 className="animate-spin" size={20} /> : <><Send size={18} /><span>Send Invites</span></>}
            </button>
          </form>
        )}
      </motion.div>
    </div>
  );
};

/* ── TAKEOVER MODAL ── */
const TakeoverModal = ({ session, onClose }) => {
  const [instruction, setInstruction] = useState('');
  const [loading, setLoading] = useState(false);
  const [wsStatus, setWsStatus] = useState('connecting');
  const [chatHistory, setChatHistory] = useState([]);
  const [empathyMetrics, setEmpathyMetrics] = useState({ stress_level: 0, hesitation_rating: 0, pacing: 'normal' });
  const [debateRounds, setDebateRounds] = useState({});
  const [supervisorMode, setSupervisorMode] = useState('ai_only');
  const [wsError, setWsError] = useState('');
  const [activeCritiqueTab, setActiveCritiqueTab] = useState('skeptic'); // 'skeptic' | 'pragmatist' | 'bias'

  const wsRef = useRef(null);
  const chatEndRef = useRef(null);

  // WebRTC States & Refs
  const [localStream, setLocalStream] = useState(null);
  const [remoteStream, setRemoteStream] = useState(null);
  const [isMuted, setIsMuted] = useState(false);
  const [isVideoStopped, setIsVideoStopped] = useState(false);
  const pcRef = useRef(null);
  const videoWsRef = useRef(null);
  const localVideoRef = useRef(null);
  const remoteVideoRef = useRef(null);
  const localStreamRef = useRef(null);

  const cleanupWebRTC = useCallback((streamToStop = null) => {
    if (pcRef.current) {
      pcRef.current.close();
      pcRef.current = null;
    }
    if (videoWsRef.current) {
      videoWsRef.current.close();
      videoWsRef.current = null;
    }
    const stream = streamToStop || localStreamRef.current;
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
    }
    setLocalStream(null);
    localStreamRef.current = null;
    setRemoteStream(null);
  }, []);

  // Auto-scroll chat history
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatHistory]);

  // Attach local video stream
  useEffect(() => {
    if (localVideoRef.current && localStream) {
      localVideoRef.current.srcObject = localStream;
    }
  }, [localStream]);

  // Attach remote video stream
  useEffect(() => {
    if (remoteVideoRef.current && remoteStream) {
      remoteVideoRef.current.srcObject = remoteStream;
    }
  }, [remoteStream]);

  // WebRTC Call Initiation & Management
  useEffect(() => {
    if (supervisorMode !== 'hr_takeover') {
      Promise.resolve().then(() => {
        cleanupWebRTC();
      });
      return;
    }

    let activeStream = null;
    let wsInstance = null;

    async function initWebRTC() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        activeStream = stream;
        setLocalStream(stream);
        localStreamRef.current = stream;

        const pc = new RTCPeerConnection({
          iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
        });
        pcRef.current = pc;

        stream.getTracks().forEach(track => {
          pc.addTrack(track, stream);
        });

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
        
        const token = localStorage.getItem('token');
        let videoUrl = `${wsBase}/interview/video/${session.id}?role=hr`;
        if (token) {
          videoUrl += `&token=${encodeURIComponent(token)}`;
        }

        wsInstance = new WebSocket(videoUrl);
        videoWsRef.current = wsInstance;

        wsInstance.onmessage = async (e) => {
          try {
            const payload = JSON.parse(e.data);
            if (payload.type === 'peer_joined' && payload.role === 'candidate') {
              const offer = await pc.createOffer();
              await pc.setLocalDescription(offer);
              wsInstance.send(JSON.stringify({
                type: 'offer',
                sdp: offer.sdp
              }));
            } else if (payload.type === 'offer') {
              // Fallback: If candidate sent offer first
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
            } else if (payload.type === 'answer') {
              await pc.setRemoteDescription(new RTCSessionDescription({
                type: 'answer',
                sdp: payload.sdp
              }));
            } else if (payload.type === 'ice_candidate') {
              if (payload.candidate) {
                await pc.addIceCandidate(new RTCIceCandidate(payload.candidate));
              }
            } else if (payload.type === 'peer_left') {
              setRemoteStream(null);
            }
          } catch {
            console.error("Signaling error");
          }
        };

        wsInstance.onclose = () => {
          console.log("Video signaling closed");
        };

      } catch {
        console.error("Failed to start WebRTC");
        alert("Could not access camera/microphone or establish connection.");
      }
    }

    initWebRTC();

    return () => {
      cleanupWebRTC(activeStream);
    };
  }, [supervisorMode, session.id, cleanupWebRTC]);

  const toggleMute = () => {
    if (localStream) {
      localStream.getAudioTracks().forEach(track => {
        track.enabled = !track.enabled;
      });
      setIsMuted(prev => !prev);
    }
  };

  const toggleVideoEnabled = () => {
    if (localStream) {
      localStream.getVideoTracks().forEach(track => {
        track.enabled = !track.enabled;
      });
      setIsVideoStopped(prev => !prev);
    }
  };

  useEffect(() => {
    const apiBase = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
    let wsBase = apiBase;
    if (apiBase.startsWith('https://')) {
      wsBase = 'wss://' + apiBase.substring(8);
    } else if (apiBase.startsWith('http://')) {
      wsBase = 'ws://' + apiBase.substring(7);
    }
    
    let socketUrl = `${wsBase}/interview/ws/${session.id}/hr`;
    const token = localStorage.getItem('token');
    if (token) {
      socketUrl += `?token=${encodeURIComponent(token)}`;
    }

    Promise.resolve().then(() => {
      setWsStatus('connecting');
    });
    const ws = new WebSocket(socketUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setWsStatus('connected');
      setWsError('');
    };

    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.type === 'state_sync') {
          const data = payload.data || {};
          if (data.messages) setChatHistory(data.messages);
          if (data.empathy_metrics) setEmpathyMetrics(data.empathy_metrics);
          if (data.debate_rounds) setDebateRounds(data.debate_rounds);
          if (data.supervisor_mode) setSupervisorMode(data.supervisor_mode);
        } else if (payload.type === 'supervisor_mode') {
          setSupervisorMode(payload.mode);
        } else if (payload.type === 'metrics_update') {
          setEmpathyMetrics(prev => ({ ...prev, ...payload.data }));
        } else if (payload.type === 'status') {
          console.log("WS status notification:", payload.data);
        } else if (payload.type === 'advisor_suggestion') {
          console.log("WS Advisor suggestion:", payload.data);
        } else if (payload.type === 'error') {
          setWsError(payload.data);
        }
      } catch {
        console.error("Error parsing WS message");
      }
    };

    ws.onclose = () => {
      setWsStatus('disconnected');
    };

    ws.onerror = () => {
      setWsStatus('error');
      setWsError('WebSocket connection error.');
    };

    return () => {
      ws.close();
      cleanupWebRTC();
    };
  }, [session.id, cleanupWebRTC]);

  const handleSendWhisper = () => {
    if (!instruction.trim() || !wsRef.current) return;
    setLoading(true);
    try {
      wsRef.current.send(JSON.stringify({
        type: 'hr_whisper',
        data: instruction
      }));
      setInstruction('');
      // Optimistic update of chat history
      setChatHistory(prev => [
        ...prev,
        { role: 'hr_whisper', content: instruction, timestamp: new Date().toISOString() }
      ]);
    } catch {
      alert("Failed to send whisper.");
    } finally {
      setLoading(false);
    }
  };

  const handleSetMode = (mode) => {
    if (!wsRef.current) return;
    try {
      wsRef.current.send(JSON.stringify({
        type: 'supervisor_control',
        action: 'set_mode',
        mode: mode
      }));
      setSupervisorMode(mode);
    } catch {
      alert("Failed to update control mode.");
    }
  };

  const handleForceClose = () => {
    if (!window.confirm("Are you sure you want to immediately terminate this candidate session? This will generate a report based on the current answers and end the interview.")) return;
    if (!wsRef.current) return;
    try {
      wsRef.current.send(JSON.stringify({
        type: 'supervisor_control',
        action: 'force_close'
      }));
      alert("Termination signal sent.");
      onClose();
    } catch {
      alert("Failed to send termination signal.");
    }
  };

  // Helper to format stress level colors
  const getStressColor = (level) => {
    if (level >= 7) return 'from-red-500 to-rose-600 text-red-400';
    if (level >= 4) return 'from-amber-400 to-orange-500 text-orange-400';
    return 'from-emerald-400 to-teal-500 text-emerald-400';
  };

  const getStressLabel = (level) => {
    if (level >= 7) return 'CRITICAL / STUCK';
    if (level >= 4) return 'MODERATE STRESS';
    return 'CALM / ENGAGED';
  };

  return (
    <div className="fixed inset-0 bg-black/80 backdrop-blur-md z-[200] flex items-center justify-center p-4">
      <motion.div initial={{ opacity: 0, scale: 0.98 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.98 }}
        className="bg-[#0b0f19] border border-white/10 rounded-[2.5rem] w-full max-w-7xl h-[90vh] overflow-hidden shadow-2xl flex flex-col">
        
        {/* Header */}
        <div className="px-10 py-6 border-b border-white/5 flex justify-between items-center bg-white/2">
          <div className="flex items-center space-x-4">
            <div className="w-10 h-10 rounded-xl bg-purple-600/10 border border-purple-500/20 flex items-center justify-center text-purple-400">
              <Radio size={20} className={wsStatus === 'connected' ? 'animate-pulse' : ''} />
            </div>
            <div>
              <div className="flex items-center space-x-3">
                <h2 className="text-xl font-bold text-white">Live Session Oversight</h2>
                <span className={`w-2.5 h-2.5 rounded-full ${
                  wsStatus === 'connected' ? 'bg-emerald-500 animate-ping' :
                  wsStatus === 'connecting' ? 'bg-amber-500 animate-pulse' : 'bg-red-500'
                }`} />
                <span className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                  {wsStatus}
                </span>
              </div>
              <p className="text-xs text-slate-500 font-bold uppercase tracking-widest mt-0.5">
                Session #{session.id} — Candidate: {session.candidate_name || session.candidate_email}
              </p>
            </div>
          </div>
          <button onClick={onClose} className="bg-white/5 border border-white/10 text-slate-400 p-3 rounded-2xl hover:text-white hover:bg-white/10 transition-all">
            <X size={20} />
          </button>
        </div>

        {wsError && (
          <div className="bg-red-500/10 border-b border-red-500/20 text-red-400 px-10 py-3 text-sm flex items-center space-x-2">
            <AlertTriangle size={16} />
            <span>{wsError}</span>
          </div>
        )}

        {/* Modal Body */}
        <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-6 p-8 overflow-hidden bg-[#070b14]">
          
          {/* LEFT COLUMN: Transcript (Col span 7) */}
          <div className="lg:col-span-7 flex flex-col h-full bg-[#0a0f1e]/60 border border-white/5 rounded-3xl p-6 overflow-hidden">
            <div className="flex justify-between items-center mb-4 pb-3 border-b border-white/5">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest">Live Transcript</span>
              <span className="text-[10px] text-slate-500 font-bold">Auto-updating</span>
            </div>
            
            <div className="flex-1 overflow-y-auto pr-2 space-y-4 min-h-0">
              {chatHistory.length === 0 ? (
                <div className="h-full flex flex-center items-center justify-center text-slate-500">
                  <div className="text-center space-y-3">
                    <Loader2 className="animate-spin text-purple-500 mx-auto" size={24} />
                    <p className="text-sm">Waiting for conversation activity...</p>
                  </div>
                </div>
              ) : (
                chatHistory.map((msg, i) => {
                  if (msg.role === 'system') return null;
                  
                  const isAssistant = msg.role === 'assistant';
                  const isWhisper = msg.role === 'hr_whisper';
                  
                  return (
                    <div key={i} className={`flex flex-col ${isAssistant ? 'items-start' : 'items-end'}`}>
                      <div className={`text-[9px] uppercase tracking-wider font-bold mb-1 ${
                        isAssistant ? 'text-purple-400' : isWhisper ? 'text-red-400' : 'text-blue-400'
                      }`}>
                        {isAssistant ? 'AI Interviewer' : isWhisper ? 'HR Whisper' : 'Candidate'}
                      </div>
                      
                      <div className={`max-w-[85%] rounded-2xl px-5 py-3 text-sm ${
                        isAssistant 
                          ? 'bg-[#151226]/80 border border-purple-500/20 text-purple-200' 
                          : isWhisper
                            ? 'bg-red-500/10 border border-red-500/20 text-red-200 font-medium italic'
                            : 'bg-white/5 border border-white/10 text-white'
                      }`}>
                        {msg.content.includes('[Code Submitted]') ? (
                          <div className="space-y-2">
                            <span className="text-blue-400 font-bold">Submitted Code:</span>
                            <pre className="bg-black/40 border border-white/5 p-3 rounded-lg overflow-x-auto font-mono text-xs text-emerald-400">
                              {msg.content}
                            </pre>
                          </div>
                        ) : (
                          <p className="whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        )}
                      </div>
                    </div>
                  );
                })
              )}
              <div ref={chatEndRef} />
            </div>
          </div>

          {/* RIGHT COLUMN: Analytics & Controls (Col span 5) */}
          <div className="lg:col-span-5 flex flex-col gap-6 h-full overflow-y-auto pr-2">
            
            {/* Stress Index & Empathy Gauge */}
            <div className="bg-[#0a0f1e]/60 border border-white/5 rounded-3xl p-6">
              <div className="flex justify-between items-center mb-4">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-1.5">
                  <span>Candidate Stress Gauge</span>
                </span>
                <span className={`text-[10px] px-2.5 py-0.5 rounded-full font-black tracking-tighter bg-gradient-to-r ${getStressColor(empathyMetrics.stress_level)}`}>
                  {getStressLabel(empathyMetrics.stress_level)}
                </span>
              </div>
              
              <div className="space-y-4">
                <div className="flex justify-between items-end">
                  <div>
                    <p className="text-3xl font-black text-white">{empathyMetrics.stress_level ?? 0}<span className="text-sm font-normal text-slate-500"> / 10</span></p>
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider mt-1">Pacing: {empathyMetrics.pacing ?? 'Normal'}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Hesitations</p>
                    <p className="text-lg font-bold text-slate-300">{empathyMetrics.hesitation_rating ?? 0}</p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="w-full h-3 bg-white/5 rounded-full overflow-hidden border border-white/5 relative">
                  <motion.div 
                    initial={{ width: 0 }} 
                    animate={{ width: `${(empathyMetrics.stress_level ?? 0) * 10}%` }}
                    transition={{ type: 'spring', stiffness: 50 }}
                    className={`h-full bg-gradient-to-r ${
                      empathyMetrics.stress_level >= 7 ? 'from-orange-500 to-red-600' :
                      empathyMetrics.stress_level >= 4 ? 'from-amber-400 to-orange-500' : 'from-emerald-400 to-teal-500'
                    }`} 
                  />
                </div>
              </div>
            </div>

            {/* AI Debate Logs */}
            <div className="bg-[#0a0f1e]/60 border border-white/5 rounded-3xl p-6 flex-1 flex flex-col min-h-[250px]">
              <div className="flex justify-between items-center mb-4">
                <span className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-1.5">
                  <Brain size={14} className="text-purple-400" />
                  <span>Real-Time Debate Arena</span>
                </span>
                <span className="text-[9px] text-purple-400 font-bold uppercase tracking-wider animate-pulse">Parallel Audit</span>
              </div>

              {/* Tabs */}
              <div className="flex space-x-1 bg-white/5 p-1 rounded-xl mb-4 border border-white/5">
                {[
                  { id: 'skeptic', label: 'Skeptic', color: 'text-amber-400 border-amber-500/20' },
                  { id: 'pragmatist', label: 'Pragmatist', color: 'text-blue-400 border-blue-500/20' },
                  { id: 'bias_auditor', label: 'Bias Auditor', color: 'text-emerald-400 border-emerald-500/20' }
                ].map(tab => (
                  <button key={tab.id}
                    onClick={() => setActiveCritiqueTab(tab.id)}
                    className={`flex-1 text-center py-2 text-[10px] font-black uppercase tracking-wider rounded-lg transition-all ${
                      activeCritiqueTab === tab.id 
                        ? 'bg-purple-600 text-white shadow-md shadow-purple-900/30' 
                        : 'text-slate-500 hover:text-white'
                    }`}>
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Critique Content */}
              <div className="flex-1 overflow-y-auto pr-1 text-xs text-slate-300 leading-relaxed bg-black/20 border border-white/5 rounded-2xl p-4 font-mono max-h-[160px]">
                {debateRounds[activeCritiqueTab] ? (
                  <p className="whitespace-pre-wrap">{debateRounds[activeCritiqueTab]}</p>
                ) : (
                  <p className="text-slate-600 italic text-center py-10">No critiques recorded for this round yet.</p>
                )}
              </div>
            </div>

            {/* Live Video Call Panel (if takeover mode is active) */}
            {supervisorMode === 'hr_takeover' && (
              <div className="bg-[#0a0f1e]/60 border border-red-500/20 rounded-3xl p-6 space-y-4">
                <div className="flex justify-between items-center mb-1">
                  <span className="text-xs font-bold text-red-400 uppercase tracking-widest flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    <span>Live Takeover Video Call</span>
                  </span>
                  <span className="text-[10px] text-slate-500 font-bold">Active P2P Feed</span>
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  {/* Candidate Feed */}
                  <div className="relative bg-black/40 border border-white/5 rounded-2xl overflow-hidden aspect-video">
                    {remoteStream ? (
                      <video ref={remoteVideoRef} autoPlay playsInline className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center text-slate-600 text-xs">
                        <Loader2 className="animate-spin text-red-500 mb-2" size={16} />
                        <span>Connecting to Candidate...</span>
                      </div>
                    )}
                    <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/60 text-[9px] font-bold text-white uppercase">Candidate</span>
                  </div>

                  {/* Recruiter Local Feed */}
                  <div className="relative bg-[#000]/40 border border-white/5 rounded-2xl overflow-hidden aspect-video">
                    {localStream ? (
                      <video ref={localVideoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center text-slate-600 text-xs">
                        <span>Local Cam Loading...</span>
                      </div>
                    )}
                    <span className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/60 text-[9px] font-bold text-white uppercase">You (HR)</span>
                  </div>
                </div>

                {/* Call controls */}
                <div className="flex justify-center space-x-3">
                  <button onClick={toggleMute}
                    className={`p-3 rounded-xl border transition-all text-xs font-bold uppercase ${
                      isMuted
                        ? 'bg-red-500/20 border-red-500/30 text-red-400'
                        : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:text-white'
                    }`}>
                    {isMuted ? 'Unmute Mic' : 'Mute Mic'}
                  </button>
                  <button onClick={toggleVideoEnabled}
                    className={`p-3 rounded-xl border transition-all text-xs font-bold uppercase ${
                      isVideoStopped
                        ? 'bg-red-500/20 border-red-500/30 text-red-400'
                        : 'bg-white/5 border-white/10 text-slate-300 hover:bg-white/10 hover:text-white'
                    }`}>
                    {isVideoStopped ? 'Start Cam' : 'Stop Cam'}
                  </button>
                </div>
              </div>
            )}

            {/* Supervision Controls */}
            <div className="bg-[#0a0f1e]/60 border border-white/5 rounded-3xl p-6 space-y-5">
              <span className="text-xs font-bold text-slate-400 uppercase tracking-widest block">Oversight & Whisper Control</span>
              
              {/* Mode Selectors */}
              <div className="grid grid-cols-2 gap-3">
                <button onClick={() => handleSetMode('ai_only')}
                  className={`py-3 px-4 rounded-xl text-[10px] font-black uppercase tracking-wider border transition-all ${
                    supervisorMode === 'ai_only'
                      ? 'bg-purple-600/10 border-purple-500/30 text-purple-400 shadow-md'
                      : 'bg-white/5 border-white/5 text-slate-500 hover:text-white hover:bg-white/10'
                  }`}>
                  Autonomous AI
                </button>
                <button onClick={() => handleSetMode('hr_takeover')}
                  className={`py-3 px-4 rounded-xl text-[10px] font-black uppercase tracking-wider border transition-all ${
                    supervisorMode === 'hr_takeover'
                      ? 'bg-red-600/10 border-red-500/30 text-red-400 shadow-md'
                      : 'bg-white/5 border-white/5 text-slate-500 hover:text-white hover:bg-white/10'
                  }`}>
                  HR Takeover
                </button>
              </div>

              {/* Whisper Input */}
              <div className="space-y-3">
                <textarea rows={3} value={instruction} onChange={e => setInstruction(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded-2xl px-4 py-3 text-sm text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all resize-none"
                  placeholder="Whisper a directive to the AI interviewer... (e.g., 'Probe their database scaling knowledge next')" />
                
                <div className="flex space-x-3">
                  <button onClick={handleSendWhisper} disabled={loading || !instruction.trim()}
                    className="flex-1 bg-purple-600 hover:bg-purple-500 text-white font-bold py-3 px-6 rounded-2xl transition-all shadow-xl shadow-purple-900/30 text-xs uppercase tracking-wider flex items-center justify-center space-x-2">
                    {loading ? <Loader2 className="animate-spin" size={16} /> : <><Send size={14} /><span>Whisper to AI</span></>}
                  </button>
                  <button onClick={handleForceClose}
                    className="bg-red-600 hover:bg-red-500 text-white font-bold px-5 rounded-2xl transition-all hover:shadow-xl hover:shadow-red-900/30 flex items-center justify-center"
                    title="Force Terminate Interview">
                    <AlertTriangle size={16} />
                  </button>
                </div>
              </div>
            </div>

          </div>
        </div>

      </motion.div>
    </div>
  );
};

/* ── CANDIDATE LIST MODAL ── */
const CandidateListModal = ({ drive, onClose }) => {
  const [candidates, setCandidates] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiClient.get(`/hr/drives/${drive.id}/candidates`)
      .then(res => {
        setCandidates(res.data.candidates || []);
      })
      .catch(() => alert('Failed to fetch candidates'))
      .finally(() => setLoading(false));
  }, [drive.id]);

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[200] flex items-center justify-center p-6">
      <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}
        className="bg-[#0f172a] border border-white/10 rounded-[2rem] w-full max-w-2xl overflow-hidden shadow-2xl flex flex-col max-h-[80vh]">
        <div className="px-8 py-6 border-b border-white/5 flex justify-between items-center bg-white/2">
          <div>
            <h2 className="text-xl font-bold text-white">Drive Participants</h2>
            <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest mt-0.5">{drive.title}</p>
          </div>
          <button onClick={onClose} className="text-slate-500 hover:text-white transition-colors"><X size={20} /></button>
        </div>
        
        <div className="flex-1 overflow-y-auto p-8">
          {loading ? (
            <div className="flex justify-center py-20"><Loader2 className="animate-spin text-purple-500" size={32} /></div>
          ) : candidates.length === 0 ? (
            <div className="text-center py-20 text-slate-500">No candidates invited yet.</div>
          ) : (
            <div className="space-y-4">
              {candidates.map((c, i) => {
                let badgeClass = 'bg-amber-500/10 border-amber-500/20 text-amber-400';
                let statusLabel = 'Pending';
                
                if (c.status === 'completed') {
                  badgeClass = 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400';
                  statusLabel = 'Completed';
                } else if (c.status === 'in_progress') {
                  badgeClass = 'bg-blue-500/10 border-blue-500/20 text-blue-400';
                  statusLabel = 'In Progress';
                } else if (c.status === 'scheduled') {
                  badgeClass = 'bg-purple-500/10 border-purple-500/20 text-purple-400';
                  statusLabel = 'Scheduled';
                } else if (c.status === 'expired') {
                  badgeClass = 'bg-red-500/10 border-red-500/20 text-red-400';
                  statusLabel = 'Expired';
                }

                return (
                  <div key={i} className="bg-white/5 border border-white/10 rounded-2xl p-4 flex items-center justify-between group">
                    <div>
                      <p className="text-white font-bold">{c.email}</p>
                      <div className="flex items-center space-x-3 mt-1">
                        <span className={`text-[9px] font-black uppercase tracking-tighter px-2 py-0.5 rounded-md border ${badgeClass}`}>
                          {statusLabel}
                        </span>
                        <span className="text-[9px] text-slate-500 font-bold uppercase">Expires: {new Date(c.expires_at).toLocaleDateString()}</span>
                      </div>
                    </div>
                    {c.score !== null && (
                      <div className="text-right">
                        <p className="text-[10px] text-slate-500 font-black uppercase tracking-widest">Score</p>
                        <p className="text-lg font-black text-purple-400">{c.score.toFixed(1)}</p>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </motion.div>
    </div>
  );
};

/* ── DRIVE SETTINGS TAB ── */
const DriveSettingsTab = ({ onProfileUpdated }) => {
  const { user } = useAuthStore();
  const [profile, setProfile] = useState({ company_name: '', department: '', position: '' });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  // Username change state
  const [newUsername, setNewUsername] = useState('');
  const [usernameSaving, setUsernameSaving] = useState(false);
  const [usernameSuccess, setUsernameSuccess] = useState(false);
  const [usernameError, setUsernameError] = useState('');

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordSaving, setPasswordSaving] = useState(false);
  const [passwordSuccess, setPasswordSuccess] = useState(false);
  const [passwordError, setPasswordError] = useState('');

  useEffect(() => {
    apiClient.get('/hr/profile')
      .then(r => setProfile({ company_name: r.data.company_name || '', department: r.data.department || '', position: r.data.position || '' }))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSave = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      await apiClient.put('/hr/profile', profile);
      setSaved(true);
      if (onProfileUpdated) onProfileUpdated();
      setTimeout(() => setSaved(false), 2500);
    } catch { alert('Failed to save profile.'); }
    finally { setSaving(false); }
  };

  const handleUsernameChange = async (e) => {
    e.preventDefault();
    setUsernameError('');
    if (!newUsername || newUsername.length < 3) {
      setUsernameError('Username must be at least 3 characters');
      return;
    }
    setUsernameSaving(true);
    try {
      await apiClient.put('/users/username', { new_username: newUsername });
      setUsernameSuccess(true);
      setNewUsername('');
      setTimeout(() => setUsernameSuccess(false), 2500);
    } catch (err) {
      setUsernameError(err.response?.data?.detail || 'Failed to change username');
    } finally {
      setUsernameSaving(false);
    }
  };

  const handlePasswordChange = async (e) => {
    e.preventDefault();
    setPasswordError('');
    if (!currentPassword || !newPassword) {
      setPasswordError('Please fill in all password fields');
      return;
    }
    if (newPassword.length < 4) {
      setPasswordError('New password must be at least 4 characters');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('New passwords do not match');
      return;
    }
    setPasswordSaving(true);
    try {
      await apiClient.post('/users/change-password', {
        current_password: currentPassword,
        new_password: newPassword
      });
      setPasswordSuccess(true);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
      setTimeout(() => setPasswordSuccess(false), 2500);
    } catch (err) {
      setPasswordError(err.response?.data?.detail || 'Failed to change password');
    } finally {
      setPasswordSaving(false);
    }
  };

  if (loading) return <div className="flex justify-center py-20"><Loader2 className="animate-spin text-purple-500" size={36} /></div>;

  return (
    <div className="max-w-xl space-y-10">
      {/* Company Profile */}
      <div>
        <h2 className="text-2xl font-black text-white mb-2">HR Profile Settings</h2>
        <p className="text-slate-500 mb-6 text-sm">Update your company and role information.</p>
        <form onSubmit={handleSave} className="space-y-5">
          {[
            { label: 'Company Name', key: 'company_name', placeholder: 'e.g. Acme Corp' },
            { label: 'Department', key: 'department', placeholder: 'e.g. Engineering' },
            { label: 'Your Position', key: 'position', placeholder: 'e.g. Senior Recruiter' },
          ].map(({ label, key, placeholder }) => (
            <div key={key}>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">{label}</label>
              <input
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder={placeholder}
                value={profile[key]}
                onChange={e => setProfile({ ...profile, [key]: e.target.value })}
              />
            </div>
          ))}
          <button type="submit" disabled={saving}
            className={`flex items-center space-x-2 px-8 py-4 rounded-2xl font-bold text-sm transition-all ${
              saved ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-purple-600 text-white hover:bg-purple-500 shadow-xl shadow-purple-900/30'
            } disabled:opacity-50`}>
            {saving ? <Loader2 className="animate-spin" size={16} /> : saved ? <CheckCircle2 size={16} /> : null}
            <span>{saving ? 'Saving...' : saved ? 'Saved!' : 'Save Changes'}</span>
          </button>
        </form>
      </div>

      {/* Username Change */}
      <div className="border-t border-white/10 pt-8">
        <h3 className="text-xl font-bold text-white mb-2">Change Username</h3>
        <p className="text-slate-500 mb-4 text-sm">Your current username: <span className="text-purple-400 font-mono">@{user?.username}</span></p>
        {usernameSuccess ? (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded-xl text-sm font-bold">
            Username changed successfully!
          </div>
        ) : (
          <form onSubmit={handleUsernameChange} className="space-y-4">
            {usernameError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-sm">{usernameError}</div>
            )}
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">New Username</label>
              <input
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder="Enter new username"
                value={newUsername}
                onChange={e => setNewUsername(e.target.value)}
              />
            </div>
            <button type="submit" disabled={usernameSaving}
              className="flex items-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/10 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50">
              {usernameSaving && <Loader2 className="animate-spin" size={14} />}
              <span>{usernameSaving ? 'Changing...' : 'Change Username'}</span>
            </button>
          </form>
        )}
      </div>

      {/* Password Change */}
      <div className="border-t border-white/10 pt-8">
        <h3 className="text-xl font-bold text-white mb-2">Change Password</h3>
        <p className="text-slate-500 mb-4 text-sm">Update your account password.</p>
        {passwordSuccess ? (
          <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 px-4 py-3 rounded-xl text-sm font-bold">
            Password changed successfully!
          </div>
        ) : (
          <form onSubmit={handlePasswordChange} className="space-y-4">
            {passwordError && (
              <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-2 rounded-xl text-sm">{passwordError}</div>
            )}
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Current Password</label>
              <input
                type="password"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder="Enter current password"
                value={currentPassword}
                onChange={e => setCurrentPassword(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">New Password</label>
              <input
                type="password"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder="Enter new password"
                value={newPassword}
                onChange={e => setNewPassword(e.target.value)}
              />
            </div>
            <div>
              <label className="block text-xs font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">Confirm New Password</label>
              <input
                type="password"
                className="w-full bg-white/5 border border-white/10 rounded-xl px-4 py-3 text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                placeholder="Confirm new password"
                value={confirmPassword}
                onChange={e => setConfirmPassword(e.target.value)}
              />
            </div>
            <button type="submit" disabled={passwordSaving}
              className="flex items-center space-x-2 px-6 py-3 bg-white/10 hover:bg-white/20 border border-white/10 text-white rounded-xl font-bold text-sm transition-all disabled:opacity-50">
              {passwordSaving && <Loader2 className="animate-spin" size={14} />}
              <span>{passwordSaving ? 'Changing...' : 'Change Password'}</span>
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

/* ── MAIN HR DASHBOARD ── */
const HRDashboard = () => {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const [drives, setDrives] = useState([]);
  const [interviews, setInterviews] = useState([]);
  const [liveSessions, setLiveSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [profileCompletion, setProfileCompletion] = useState(0);
  const [activeTab, setActiveTab] = useState('Active Drives');
  const [isSidebarOpen, setIsSidebarOpen] = useState(false);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [editDrive, setEditDrive] = useState(null);
  const [deleteDrive, setDeleteDrive] = useState(null);
  const [viewCandidatesDrive, setViewCandidatesDrive] = useState(null);
  const [bulkInviteDrive, setBulkInviteDrive] = useState(null);
  const [takeoverSession, setTakeoverSession] = useState(null);
  const [copiedId, setCopiedId] = useState(null);
  const [activeMenuId, setActiveMenuId] = useState(null);

  // Phase 1A: Track dismissed advisor suggestions
  const [dismissedAdvisors, setDismissedAdvisors] = useState(new Set());

  const handleViewReport = (sessionId) => {
    navigate(`/report/${sessionId}`);
  };

  const handleViewReplay = (sessionId) => {
    navigate(`/replay/${sessionId}`);
  };

  const handleViewSkillGap = (sessionId) => {
    navigate(`/skill-gap/${sessionId}`);
  };

  const handleExportCSV = async () => {
    try {
      const res = await apiClient.get('/hr/analytics/export/csv', { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', 'vedrix_interviews_export.csv');
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch {
      alert('Export failed. Ensure you have HR permissions.');
    }
  };

  // Phase 1A: Extract advisor suggestions from live sessions (derived state)
  const advisorSuggestions = useMemo(() => {
    return liveSessions
      .filter(s => s.advisor_ready_to_close && !s.advisor_action_taken && !dismissedAdvisors.has(s.id))
      .map(s => ({
        sessionId: s.id,
        candidateName: s.candidate_name || s.candidate_email || `Session #${s.id}`,
        ready_to_close: true,
        confidence: s.advisor_confidence || 0,
        reason: s.advisor_reason || 'AI suggests this interview is ready to close.',
        reason_category: s.advisor_reason_category || 'strong_performance',
      }));
  }, [liveSessions, dismissedAdvisors]);

  // Phase 1A: Handle closing an interview from advisor badge
  const handleCloseInterview = async (sessionId) => {
    try {
      await apiClient.post(`/hr/interviews/${sessionId}/close`, {
        message: 'Interview closed by HR via AI Advisor suggestion',
      });
      // Refresh data
      fetchData();
    } catch (err) {
      console.error('Failed to close interview:', err);
      alert('Failed to close interview. Please try again.');
    }
  };

  const handleDismissAdvisor = (sessionId) => {
    setDismissedAdvisors(prev => new Set([...prev, sessionId]));
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [drivesRes, interviewsRes] = await Promise.all([
        apiClient.get('/hr/drives'),
        apiClient.get('/hr/interviews')
      ]);
      // Normalize drives response shape in case API returns data under a nested key
      const possibleDrives = drivesRes?.data?.drives ?? drivesRes?.data ?? [];
      setDrives(Array.isArray(possibleDrives) ? possibleDrives : []);
      // Normalize interviews response shape
      const allInterviews = Array.isArray(interviewsRes?.data) ? interviewsRes.data : (interviewsRes?.data?.interviews ?? []);
      setInterviews(allInterviews.filter(i => i.status === 'completed'));
      setLiveSessions(allInterviews.filter(i => i.status === 'in_progress'));
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleToggleDrive = async (driveId) => {
    try {
      await apiClient.patch(`/hr/drives/${driveId}/toggle`);
      fetchData();
      setActiveMenuId(null);
    } catch {
      alert('Failed to toggle drive status');
    }
  };

  const fetchProfileCheck = async () => {
    try {
      const res = await apiClient.get('/hr/profile-check');
      setProfileCompletion(res.data?.completion ?? 0);
    } catch {
      setProfileCompletion(0);
    }
  };

  // Preflight HR profile check
  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    fetchProfileCheck();
  }, []);

  useEffect(() => { 
    fetchData(); 
    // Basic polling for live sessions could be added here
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, []);

  const handleGenerateLink = async (driveId) => {
    try {
      const res = await apiClient.post(`/hr/drives/${driveId}/magic-link`, {});
      await navigator.clipboard.writeText(res.data.link);
      setCopiedId(driveId);
      setTimeout(() => setCopiedId(null), 2000);
    } catch {
      alert('Failed to generate link');
    }
  };

  const [sortConfig, setSortConfig] = useState({ key: 'overall_score', direction: 'desc' });

  const sortedInterviews = useMemo(() => {
    let sortableInterviews = [...interviews];
    sortableInterviews.sort((a, b) => {
      let aValue = a[sortConfig.key];
      let bValue = b[sortConfig.key];
      
      if (['technical_accuracy', 'communication_clarity', 'depth_of_knowledge'].includes(sortConfig.key)) {
        aValue = a.ai_feedback?.[sortConfig.key] || 0;
        bValue = b.ai_feedback?.[sortConfig.key] || 0;
      }
      
      if (aValue < bValue) return sortConfig.direction === 'asc' ? -1 : 1;
      if (aValue > bValue) return sortConfig.direction === 'asc' ? 1 : -1;
      return 0;
    });
    return sortableInterviews;
  }, [interviews, sortConfig]);

  const requestSort = (key) => {
    let direction = 'desc';
    if (sortConfig.key === key && sortConfig.direction === 'desc') {
      direction = 'asc';
    }
    setSortConfig({ key, direction });
  };

  return (
    <div className="min-h-screen bg-[#020617] flex font-sans">
      <AnimatePresence>
        {showCreateModal && <DriveModal onClose={() => setShowCreateModal(false)} onSaved={fetchData} />}
        {editDrive && <DriveModal drive={editDrive} onClose={() => setEditDrive(null)} onSaved={fetchData} />}
        {deleteDrive && <DeleteModal drive={deleteDrive} onClose={() => setDeleteDrive(null)} onDeleted={fetchData} />}
        {viewCandidatesDrive && <CandidateListModal drive={viewCandidatesDrive} onClose={() => setViewCandidatesDrive(null)} />}
        {bulkInviteDrive && <BulkInviteModal drive={bulkInviteDrive} onClose={() => setBulkInviteDrive(null)} />}
        {takeoverSession && <TakeoverModal session={takeoverSession} onClose={() => setTakeoverSession(null)} />}
      </AnimatePresence>

      {/* Phase 1A: Advisor Badges for each session ready to close */}
      {advisorSuggestions.map(suggestion => (
        <AdvisorBadge
          key={suggestion.sessionId}
          suggestion={suggestion}
          onCloseInterview={() => handleCloseInterview(suggestion.sessionId)}
          onDismiss={() => handleDismissAdvisor(suggestion.sessionId)}
        />
      ))}

      {/* Sidebar Overlay Backdrop on Mobile */}
      {isSidebarOpen && (
        <div 
          onClick={() => setIsSidebarOpen(false)} 
          className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[90] lg:hidden"
        />
      )}

      {/* Sidebar */}
      <div className={`w-72 bg-[#0a0f1e] border-r border-white/5 p-8 flex-col space-y-10 fixed inset-y-0 left-0 z-[100] lg:relative lg:translate-x-0 transition-transform duration-300 lg:flex ${
        isSidebarOpen ? 'translate-x-0 flex' : '-translate-x-full lg:flex hidden'
      }`}>
        <div className="flex justify-between items-center lg:block">
          <Link to="/home" className="flex items-center space-x-3 hover:opacity-80 transition-opacity">
            <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-900/30">
              <Briefcase size={20} />
            </div>
            <span className="text-xl font-bold tracking-tight text-white">Autergo <span className="text-purple-400">HR</span></span>
          </Link>
          <button 
            onClick={() => setIsSidebarOpen(false)} 
            className="lg:hidden p-2 text-slate-400 hover:text-white bg-white/5 rounded-xl border border-white/10"
          >
            <X size={16} />
          </button>
        </div>

        <nav className="flex-1 space-y-2">
          <Link to="/home"
            className="w-full flex items-center space-x-3 px-5 py-4 rounded-2xl transition-all text-sm font-bold text-slate-500 hover:text-white hover:bg-white/5">
            <Home size={18} />
            <span>Home</span>
          </Link>
          {[
            { label: 'Active Drives', icon: LayoutDashboard },
            { label: 'Live Monitoring', icon: Radio },
            { label: 'Evaluation Reports', icon: Activity },
            { label: 'Skill Matrix', icon: Briefcase },
            { label: 'Drive Settings', icon: Settings },
          ].map(item => (
            <button key={item.label}
              onClick={() => { setActiveTab(item.label); setIsSidebarOpen(false); }}
              className={`w-full flex items-center space-x-3 px-5 py-4 rounded-2xl transition-all text-sm font-bold ${
                activeTab === item.label ? 'bg-purple-600/10 text-purple-400 border border-purple-500/20' : 'text-slate-500 hover:text-white hover:bg-white/5'
              }`}>
              <item.icon size={18} />
              <span>{item.label}</span>
              {item.label === 'Live Monitoring' && liveSessions.length > 0 && (
                <span className="ml-auto bg-red-500 text-white text-[10px] font-black px-2 py-0.5 rounded-full animate-pulse">
                  {liveSessions.length}
                </span>
              )}
            </button>
          ))}
        </nav>

        <button onClick={logout}
          className="flex items-center space-x-3 px-5 py-4 rounded-2xl text-slate-500 hover:text-red-400 hover:bg-red-500/5 transition-all border border-transparent hover:border-red-500/10">
          <LogOut size={18} />
          <span className="text-sm font-bold uppercase tracking-wider">Logout</span>
        </button>
      </div>

      {/* Main Content */}
      <div className="flex-1 p-6 md:p-12 overflow-y-auto">
        {/* Ambient glow */}
        <div className="fixed top-0 right-0 w-[40%] h-[40%] bg-purple-600/5 blur-[150px] rounded-full pointer-events-none" />

        <header className="flex flex-col md:flex-row justify-between items-start md:items-center mb-12 gap-6 relative">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsSidebarOpen(true)}
              className="lg:hidden p-3 bg-white/5 border border-white/10 rounded-2xl text-slate-400 hover:text-white transition-all"
            >
              <Menu size={20} />
            </button>
            <div>
              <h1 className="text-4xl font-extrabold text-white tracking-tight">
                {activeTab === 'Active Drives' ? 'Recruitment Orchestration' : 
                 activeTab === 'Live Monitoring' ? 'Live Session Oversight' : 
                 activeTab === 'Evaluation Reports' ? 'Assessment Insights' :
                 activeTab === 'Skill Matrix' ? 'Skill Matrix Analytics' : 'HR Profile Settings'}
              </h1>
              <p className="text-slate-500 text-lg mt-1 font-medium italic">Welcome back, {user?.first_name}</p>
            </div>
          </div>
          {activeTab === 'Active Drives' && (
            <div className="flex flex-col sm:flex-row sm:items-center sm:gap-3">
              <div className="rounded-3xl bg-white/5 border border-white/10 px-4 py-3 text-sm text-slate-300">
                <p className="uppercase tracking-[0.2em] text-[10px] text-slate-500 font-black">HR Profile Completion</p>
                <p className="text-lg font-black text-white">{profileCompletion}%</p>
              </div>
              <button onClick={() => setActiveTab('Drive Settings')}
                className="bg-white/5 border border-white/10 text-white px-6 py-3 rounded-2xl font-bold hover:bg-white/10 transition-all">
                Edit Profile
              </button>
              <button onClick={() => setShowCreateModal(true)}
                className={`bg-purple-600 text-white px-8 py-4 rounded-2xl font-bold hover:bg-purple-500 transition-all shadow-xl shadow-purple-900/30 flex items-center space-x-2 active:scale-95 ${profileCompletion < 50 ? 'opacity-50 cursor-not-allowed' : ''}`}
                disabled={profileCompletion < 50}>
                <Plus size={20} />
                <span>Launch Drive</span>
              </button>
            </div>
          )}
          {activeTab === 'Active Drives' && profileCompletion < 50 && (
            <div className="mt-4 text-sm text-slate-400">Complete at least 50% of your HR profile before launching a drive. Click <button onClick={() => setActiveTab('Drive Settings')} className="text-purple-400 underline">Edit Profile</button> to continue.</div>
          )}
        </header>

        {loading && !drives.length ? (
          <div className="flex justify-center items-center h-64">
            <div className="space-y-3 w-full max-w-2xl">
              {[1,2,3].map(i => <div key={i} className="skeleton h-20 rounded-2xl" />)}
            </div>
          </div>
        ) : activeTab === 'Active Drives' ? (
          <>
            {/* Stats Cards with Sparklines */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
              {[
                { label: 'Total Drives', value: drives.length, icon: Briefcase, color: 'text-purple-400', sparkColor: '#7c3aed', data: [3,5,4,7,6,8,drives.length].map(v => ({v})) },
                { label: 'Active Drives', value: drives.filter(d => d.is_active).length, icon: Layers, color: 'text-emerald-400', sparkColor: '#34d399', data: [1,2,3,2,4,3,drives.filter(d => d.is_active).length].map(v => ({v})) },
                { label: 'Total Candidates', value: drives.reduce((sum, d) => sum + (d.participant_count || 0), 0), icon: Users, color: 'text-blue-400', sparkColor: '#60a5fa', data: [10,15,20,18,25,30,drives.reduce((sum, d) => sum + (d.participant_count || 0), 0)].map(v => ({v})) },
                { label: 'Live Sessions', value: liveSessions.length, icon: Radio, color: 'text-red-400', sparkColor: '#f87171', data: [0,1,2,1,0,1,liveSessions.length].map(v => ({v})) },
              ].map(stat => (
                <div key={stat.label} className="glass-card rounded-2xl p-5 relative overflow-hidden">
                  <div className="flex items-center justify-between mb-2">
                    <stat.icon size={16} className={stat.color} />
                    <div className="w-16"><MiniSparkline data={stat.data} color={stat.sparkColor} /></div>
                  </div>
                  <p className="text-2xl font-black text-white"><AnimatedStat value={stat.value} /></p>
                  <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mt-1">{stat.label}</p>
                </div>
              ))}
            </div>

            {/* Recent Interviews Quick View */}
            {interviews.length > 0 && (
              <div className="glass-card rounded-3xl p-6 mb-10">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-xs font-black uppercase text-slate-400 tracking-widest flex items-center gap-2">
                    <TrendingUp size={14} className="text-purple-400" /> Top Candidates
                  </h3>
                  <button onClick={() => setActiveTab('Evaluation Reports')} className="text-xs text-purple-400 font-bold hover:text-purple-300 transition-colors">View All →</button>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  {interviews.slice(0, 3).map(interview => (
                    <div key={interview.id} className="bg-white/5 border border-white/5 rounded-2xl p-4 flex items-center space-x-3 hover:bg-white/10 transition-all cursor-pointer" onClick={() => handleViewReport(interview.id)}>
                      <div className="w-10 h-10 bg-purple-600/20 rounded-xl flex items-center justify-center text-purple-400 font-black text-sm">
                        {interview.overall_score ? interview.overall_score.toFixed(1) : '—'}
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="text-white text-sm font-bold truncate">{interview.candidate_name || interview.candidate_email || `#${interview.id}`}</p>
                        <p className="text-slate-500 text-[10px] font-bold uppercase tracking-widest">{interview.job_role || 'Unknown'}</p>
                      </div>
                      <ChevronRight size={14} className="text-slate-600" />
                    </div>
                  ))}
                </div>
              </div>
            )}

          {drives.length === 0 ? (
            <div className="bg-white/2 border-2 border-dashed border-white/10 rounded-[2.5rem] p-20 text-center space-y-6">
              <div className="w-20 h-20 bg-white/5 rounded-full flex items-center justify-center mx-auto text-slate-600">
                <Briefcase size={40} />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white">No active drives detected</h2>
                <p className="text-slate-500 mt-2">Create your first hiring drive to start inviting candidates and collecting interview results.</p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 xl:grid-cols-2 gap-8">
              {drives.map(drive => (
                <motion.div layout key={drive.id}
                  className="bg-white/2 border border-white/5 p-10 rounded-[2.5rem] hover:border-purple-500/20 hover:bg-white/5 transition-all group relative overflow-hidden">
                  <div className="absolute top-0 right-0 w-32 h-32 bg-purple-600/5 blur-[60px] rounded-full group-hover:bg-purple-600/10 transition-all" />

                  <div className="flex justify-between items-start mb-8 relative">
                    <div>
                      <div className="flex items-center space-x-3 mb-2">
                        <span className={`${drive.is_active ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' : 'bg-red-500/10 text-red-400 border-red-500/20'} text-[10px] font-black uppercase tracking-widest px-3 py-1 rounded-full border`}>
                          {drive.is_active ? 'Open' : 'Closed'}
                        </span>
                        <span className="flex items-center text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                          <Clock size={12} className="mr-1" /> {new Date(drive.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <h2 className="text-2xl font-bold text-white cursor-pointer hover:text-purple-400 transition-colors" onClick={() => setViewCandidatesDrive(drive)}>{drive.title}</h2>
                      <p className="text-slate-400 font-medium">{drive.job_role}</p>
                    </div>
                    <div className="relative">
                      <button onClick={() => setActiveMenuId(activeMenuId === drive.id ? null : drive.id)}
                        className="text-slate-600 hover:text-white transition-colors p-2 hover:bg-white/5 rounded-xl"><MoreVertical size={20} /></button>
                      
                      <AnimatePresence>
                        {activeMenuId === drive.id && (
                          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 10 }}
                            className="absolute right-0 mt-2 w-48 bg-[#1e293b] border border-white/10 rounded-2xl shadow-2xl z-50 overflow-hidden">
                            <button onClick={() => { setEditDrive(drive); setActiveMenuId(null); }}
                              className="w-full text-left px-5 py-3 text-xs font-bold text-slate-300 hover:bg-white/5 hover:text-white transition-all flex items-center space-x-3">
                              <Settings size={14} /> <span>Edit Details</span>
                            </button>
                            <button onClick={() => handleToggleDrive(drive.id)}
                              className="w-full text-left px-5 py-3 text-xs font-bold text-slate-300 hover:bg-white/5 hover:text-white transition-all flex items-center space-x-3">
                              <Activity size={14} /> <span>{drive.is_active ? 'Close Drive' : 'Re-open Drive'}</span>
                            </button>
                            <button onClick={() => { setDeleteDrive(drive); setActiveMenuId(null); }}
                              className="w-full text-left px-5 py-3 text-xs font-bold text-red-400 hover:bg-red-500/10 transition-all flex items-center space-x-3">
                              <X size={14} /> <span>Delete Forever</span>
                            </button>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 gap-4 mb-8">
                    <div className="bg-white/5 p-5 rounded-2xl border border-white/5 text-center cursor-pointer hover:bg-white/10 transition-all" onClick={() => setViewCandidatesDrive(drive)}>
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Candidates</p>
                      <p className="text-2xl font-black text-white">{drive.participant_count ?? 0}</p>
                    </div>
                    <div className="bg-white/5 p-5 rounded-2xl border border-white/5 text-center">
                      <p className="text-[10px] font-black text-slate-500 uppercase tracking-widest mb-1">Avg. Score</p>
                      <p className="text-2xl font-black text-white">{drive.avg_score ? drive.avg_score.toFixed(1) : '—'}</p>
                    </div>
                  </div>

                  <div className="flex items-center space-x-3">
                    <button
                      onClick={() => navigate(`/hr/drives/${drive.id}/hiring-workflow`)}
                      className="flex items-center justify-center space-x-2 bg-cyan-500/10 border border-cyan-500/30 text-cyan-300 px-4 py-4 rounded-2xl font-bold hover:bg-cyan-500/20 transition-all text-sm"
                    >
                      <Briefcase size={16} />
                      <span>Hiring Flow</span>
                    </button>
                    <button onClick={() => handleGenerateLink(drive.id)}
                      className={`flex-1 flex items-center justify-center space-x-2 py-4 rounded-2xl font-bold transition-all text-sm ${
                        copiedId === drive.id ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-purple-600 text-white hover:bg-purple-500 shadow-lg shadow-purple-900/20'
                      }`}>
                      {copiedId === drive.id ? <CheckCircle2 size={18} /> : <LinkIcon size={18} />}
                      <span>{copiedId === drive.id ? 'Link Copied' : 'Copy Invite Link'}</span>
                    </button>

                    <button onClick={() => setBulkInviteDrive(drive)}
                      className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-5 py-4 rounded-2xl font-bold hover:bg-white/10 hover:text-white transition-all text-sm">
                      <Mail size={16} />
                      <span>Bulk Invite</span>
                    </button>

                    <button 
                      onClick={() => setViewCandidatesDrive(drive)}
                      className="bg-white/5 border border-white/10 text-slate-400 px-4 py-4 rounded-2xl hover:bg-white/10 transition-all">
                      <ChevronRight size={18} />
                    </button>
                  </div>
                </motion.div>
              ))}
            </div>
          )}
          </>
        ) : activeTab === 'Live Monitoring' ? (
          <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden">
            <div className="px-10 py-6 border-b border-white/5 bg-white/2">
              <div className="grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500">
                <div className="col-span-4">Candidate / Session</div>
                <div className="col-span-4">Role / Drive</div>
                <div className="col-span-2 text-center">Status</div>
                <div className="col-span-2 text-right">Actions</div>
              </div>
            </div>
            <div className="divide-y divide-white/5">
              {liveSessions.length === 0 ? (
                <div className="p-20 text-center">
                  <Radio size={48} className="mx-auto text-slate-700 mb-6" />
                  <p className="text-slate-500 font-medium">No live sessions currently in progress.</p>
                </div>
              ) : (
                liveSessions.map(session => (
                  <div key={session.id} className="px-10 py-8 grid grid-cols-12 gap-4 items-center hover:bg-white/5 transition-all group">
                    <div className="col-span-4 flex items-center space-x-4">
                      <div className="w-12 h-12 bg-red-500/10 border border-red-500/20 rounded-2xl flex items-center justify-center text-red-400 font-black relative">
                        <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full border-2 border-[#0a0f1e] -mt-1 -mr-1 animate-ping" />
                        <Radio size={20} />
                      </div>
                      <div>
                        <p className="text-white font-bold">Session #{session.id}</p>
                        <p className="text-xs text-slate-500 font-medium">{session.candidate_name || session.candidate_email || `Candidate #${session.candidate_id}`}</p>
                      </div>
                    </div>
                    <div className="col-span-4">
                      <p className="text-slate-300 font-bold text-sm">{session.job_role || 'Unknown Role'}</p>
                      <p className="text-[10px] text-slate-600 font-bold uppercase tracking-widest mt-0.5">{session.drive_title || 'Unknown Drive'}</p>
                    </div>
                    <div className="col-span-2 text-center">
                      <span className="text-red-400 text-xs font-black uppercase tracking-widest px-3 py-1 bg-red-500/10 rounded-full border border-red-500/20 inline-block">
                        Active Now
                      </span>
                    </div>
                    <div className="col-span-2 text-right flex justify-end">
                      <button 
                        onClick={() => setTakeoverSession(session)}
                        className="bg-red-600 hover:bg-red-500 text-white text-[10px] font-black uppercase tracking-widest px-4 py-2 rounded-xl transition-all shadow-lg shadow-red-900/30 flex items-center space-x-2">
                        <MessageSquareText size={14} />
                        <span>Guide</span>
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        ) : activeTab === 'Evaluation Reports' ? (
          <div className="space-y-6">
            {/* Export bar */}
            <div className="flex justify-end">
              <button
                onClick={handleExportCSV}
                className="flex items-center space-x-2 bg-white/5 border border-white/10 text-slate-300 px-5 py-2.5 rounded-xl text-sm font-bold hover:bg-white/10 transition-all"
              >
                <Download size={16} />
                <span>Export CSV</span>
              </button>
            </div>
            <div className="bg-white/2 border border-white/5 rounded-[2.5rem] overflow-hidden overflow-x-auto scrollbar-thin">
              <div className="min-w-[900px] lg:min-w-0">
                <div className="px-8 py-6 border-b border-white/5 bg-white/2">
                  <div className="grid grid-cols-12 gap-4 text-[10px] font-black uppercase tracking-[0.2em] text-slate-500 items-center">
                    <div className="col-span-3">Candidate</div>
                    <div className="col-span-2">Role / Drive</div>
                    <div className="col-span-1 text-center cursor-pointer hover:text-white transition-colors" onClick={() => requestSort('overall_score')}>Score {sortConfig.key === 'overall_score' && (sortConfig.direction === 'asc' ? '↑' : '↓')}</div>
                    <div className="col-span-1 text-center cursor-pointer hover:text-white transition-colors" onClick={() => requestSort('technical_accuracy')}>Tech</div>
                    <div className="col-span-1 text-center cursor-pointer hover:text-white transition-colors" onClick={() => requestSort('communication_clarity')}>Comm</div>
                    <div className="col-span-1 text-center">Actions</div>
                    <div className="col-span-3"></div>
                  </div>
                </div>
                <div className="divide-y divide-white/5">
                  {sortedInterviews.length === 0 ? (
                    <div className="p-20 text-center">
                      <p className="text-slate-500 font-medium">No evaluation reports generated yet.</p>
                    </div>
                  ) : (
                    sortedInterviews.map(interview => (
                      <div key={interview.id} className="px-8 py-6 grid grid-cols-12 gap-4 items-center hover:bg-white/5 transition-all group">
                        <div className="col-span-3 flex items-center space-x-4">
                          <div className="w-10 h-10 bg-purple-600/10 border border-purple-500/20 rounded-2xl flex items-center justify-center text-purple-400 font-black text-sm shrink-0">
                            {(interview.candidate_name || interview.candidate_email || '#').charAt(0).toUpperCase()}
                          </div>
                          <div className="truncate">
                            <p className="text-white font-bold text-sm truncate">{interview.candidate_name || 'Guest Candidate'}</p>
                            <p className="text-[10px] text-slate-500 font-medium truncate">{interview.candidate_email || `ID #${interview.candidate_id}`}</p>
                          </div>
                        </div>
                        <div className="col-span-2 truncate">
                          <p className="text-slate-300 font-bold text-xs truncate">{interview.job_role || 'Unknown Role'}</p>
                          <p className="text-[9px] text-slate-600 font-bold uppercase tracking-widest mt-0.5 truncate">{interview.drive_title || 'Unknown Drive'}</p>
                        </div>
                        <div className="col-span-1 text-center">
                          <span className={`text-lg font-black ${
                            interview.overall_score >= 8 ? 'text-emerald-400' : 
                            interview.overall_score >= 5 ? 'text-purple-400' : 'text-amber-400'
                          }`}>
                            {interview.overall_score?.toFixed(1) || '—'}
                          </span>
                        </div>
                        <div className="col-span-1 text-center">
                          <span className="text-sm font-bold text-slate-300">
                            {interview.ai_feedback?.technical_accuracy?.toFixed(1) || '—'}
                          </span>
                        </div>
                        <div className="col-span-1 text-center">
                          <span className="text-sm font-bold text-slate-300">
                            {interview.ai_feedback?.communication_clarity?.toFixed(1) || '—'}
                          </span>
                        </div>
                        <div className="col-span-1 text-center">
                          <div className="flex items-center justify-center space-x-1">
                            <button 
                              onClick={(e) => { e.stopPropagation(); handleViewReplay(interview.id); }}
                              className="p-1.5 bg-white/5 border border-white/10 rounded-lg text-slate-400 hover:text-blue-400 hover:bg-blue-600/10 transition-all"
                              title="Replay"
                            >
                              <Play size={12} />
                            </button>
                            <button 
                              onClick={(e) => { e.stopPropagation(); handleViewSkillGap(interview.id); }}
                              className="p-1.5 bg-white/5 border border-white/10 rounded-lg text-slate-400 hover:text-amber-400 hover:bg-amber-600/10 transition-all"
                              title="Skill Gap"
                            >
                              <Target size={12} />
                            </button>
                          </div>
                        </div>
                        <div className="col-span-3 text-right">
                          <button 
                            onClick={() => handleViewReport(interview.id)}
                            className="px-4 py-2 bg-white/5 border border-white/10 rounded-xl text-slate-400 hover:text-white hover:bg-purple-600 transition-all text-xs font-bold">
                            View Report
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </div>
          </div>
        ) : activeTab === 'Skill Matrix' ? (
          <SkillMatrixTab interviews={interviews} />
        ) : (
          activeTab === 'Drive Settings' ? (
            <DriveSettingsTab onProfileUpdated={fetchProfileCheck} />
          ) : (
          <div className="p-20 text-center">
            <h2 className="text-2xl font-bold text-white">{activeTab}</h2>
            <p className="text-slate-500 mt-2">This module is coming soon in the next update.</p>
          </div>
          )
        )}
      </div>
    </div>
  );
};

export default HRDashboard;
