import { useState, useEffect, useRef, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, X, Send, Minimize2, Bot } from 'lucide-react';
import useAuthStore from '../store/useAuthStore';

const SUGGESTIONS = [
  'How do I start an interview?',
  'Explain my last score',
  'What skills should I improve?',
  'Show me my growth plan',
];

// Cosmetic-only canned answers — keyed by simple keyword match
const CANNED_RESPONSES = [
  {
    match: ['start', 'begin', 'launch'],
    text:
      'You can start an interview from your dashboard. Click "Start Interview" or use the command palette (Cmd/Ctrl+K) and type "Start an Interview".',
  },
  {
    match: ['score', 'last', 'recent'],
    text:
      'Your latest score blends technical accuracy, communication, and confidence. Open the report from your dashboard for a per-section breakdown.',
  },
  {
    match: ['skill', 'improve', 'grow', 'weakness'],
    text:
      'Based on past sessions, focus on system design fundamentals and clarity in trade-off discussion. Your coaching plan has tailored exercises.',
  },
  {
    match: ['plan', 'coaching', 'growth'],
    text:
      'Your growth plan adapts each week. Review it on the Coaching page and check off practice tasks to keep momentum.',
  },
  {
    match: ['help', 'how', 'what'],
    text:
      'I can help you navigate Autergo, summarize sessions, or surface coaching tips. Try a suggestion below or just ask a question.',
  },
];

const pickResponse = (q) => {
  const text = q.toLowerCase();
  for (const r of CANNED_RESPONSES) {
    if (r.match.some((kw) => text.includes(kw))) return r.text;
  }
  return "Got it. I'm a preview assistant for now — once the AI backend is wired up, I'll give you a tailored answer based on your sessions.";
};

const TypingDots = () => (
  <div className="flex items-center gap-1 py-2 px-3">
    {[0, 1, 2].map((i) => (
      <motion.span
        key={i}
        className="w-1.5 h-1.5 rounded-full bg-purple-400"
        animate={{ y: [0, -3, 0], opacity: [0.4, 1, 0.4] }}
        transition={{ duration: 0.9, repeat: Infinity, delay: i * 0.12 }}
      />
    ))}
  </div>
);

const AIAssistant = () => {
  const { user, isAuthenticated } = useAuthStore();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    if (open && messages.length === 0) {
      const name = user?.first_name ? `, ${user.first_name}` : '';
      Promise.resolve().then(() => {
        setMessages([
          {
            id: 'greet',
            role: 'assistant',
            text: `Hey${name} — I'm Vedra, your AI assistant. Ask me anything, or pick a quick prompt below.`,
          },
        ]);
      });
    }
  }, [open, messages.length, user]);

  // Auto-scroll on new messages
  useEffect(() => {
    if (!scrollRef.current) return;
    scrollRef.current.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth',
    });
  }, [messages, typing]);

  // Listen for global open events (from command palette etc.)
  useEffect(() => {
    const handler = () => setOpen(true);
    window.addEventListener('vedrix:open-assistant', handler);
    return () => window.removeEventListener('vedrix:open-assistant', handler);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) setTimeout(() => inputRef.current?.focus(), 250);
  }, [open]);

  const sendMessage = useCallback((text) => {
    const trimmed = text.trim();
    if (!trimmed) return;
    const userMsg = {
      id: `u-${Date.now()}`,
      role: 'user',
      text: trimmed,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setTyping(true);

    // Simulated typing delay
    const replyText = pickResponse(trimmed);
    setTimeout(() => {
      setTyping(false);
      setMessages((prev) => [
        ...prev,
        {
          id: `a-${Date.now()}`,
          role: 'assistant',
          text: replyText,
        },
      ]);
    }, 700 + Math.min(replyText.length * 4, 600));
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    sendMessage(input);
  };

  // Don't render if not authenticated (App.jsx already gates, but defensive)
  if (!isAuthenticated) return null;

  return (
    <>
      {/* Collapsed bubble */}
      <AnimatePresence>
        {!open && (
          <motion.button
            type="button"
            key="bubble"
            initial={{ scale: 0, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            exit={{ scale: 0, opacity: 0 }}
            transition={{ type: 'spring', damping: 18, stiffness: 280 }}
            onClick={() => setOpen(true)}
            aria-label="Open Vedra AI assistant"
            className="fixed floating-safe z-[9990] w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-500 text-white flex items-center justify-center ai-bubble-pulse hover:scale-110 active:scale-95 transition-transform"
          >
            <Sparkles size={22} />
          </motion.button>
        )}
      </AnimatePresence>

      {/* Expanded panel */}
      <AnimatePresence>
        {open && (
          <motion.div
            key="panel"
            initial={{ opacity: 0, y: 24, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 24, scale: 0.96 }}
            transition={{ type: 'spring', damping: 24, stiffness: 280 }}
            className="fixed inset-x-4 bottom-[var(--floating-panel-bottom)] sm:left-auto sm:right-[var(--floating-panel-right)] z-[9990] w-auto sm:w-[400px] sm:max-w-[calc(100vw-2rem)] h-[min(600px,calc(100svh-var(--nav-height)-2rem))] max-h-[calc(100svh-2rem)] flex flex-col bg-[#0a0f1e]/95 backdrop-blur-2xl border border-white/10 rounded-3xl shadow-2xl shadow-black/60 overflow-hidden"
            role="dialog"
            aria-label="AI assistant chat"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/5 bg-gradient-to-r from-purple-600/10 to-indigo-500/10">
              <div className="flex items-center gap-3">
                <div className="relative w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-500 flex items-center justify-center text-white shadow-lg shadow-purple-900/40">
                  <Sparkles size={18} />
                  <span className="absolute -bottom-0.5 -right-0.5 w-3 h-3 rounded-full bg-emerald-400 border-2 border-[#0a0f1e] pulse-glow" />
                </div>
                <div>
                  <p className="text-white font-bold text-sm leading-tight">Vedra</p>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                    Online
                  </p>
                </div>
              </div>
              <div className="flex items-center gap-1">
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  aria-label="Minimize assistant"
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/5 transition-all active:scale-95"
                >
                  <Minimize2 size={14} />
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setOpen(false);
                    setMessages([]);
                  }}
                  aria-label="Close assistant"
                  className="w-8 h-8 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/5 transition-all active:scale-95"
                >
                  <X size={16} />
                </button>
              </div>
            </div>

            {/* Messages */}
            <div ref={scrollRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3">
              {messages.map((m) => (
                <motion.div
                  key={m.id}
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                  className={`flex items-end gap-2 ${
                    m.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {m.role === 'assistant' && (
                    <div className="shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-500 flex items-center justify-center text-white">
                      <Bot size={13} />
                    </div>
                  )}
                  <div
                    className={`max-w-[78%] px-4 py-2.5 rounded-2xl text-sm leading-relaxed ${
                      m.role === 'user'
                        ? 'bg-purple-600 text-white rounded-br-md'
                        : 'bg-white/5 text-slate-200 border border-white/10 rounded-bl-md'
                    }`}
                  >
                    {m.text}
                  </div>
                </motion.div>
              ))}

              {typing && (
                <motion.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex items-end gap-2"
                >
                  <div className="shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-purple-600 to-indigo-500 flex items-center justify-center text-white">
                    <Bot size={13} />
                  </div>
                  <div className="bg-white/5 border border-white/10 rounded-2xl rounded-bl-md">
                    <TypingDots />
                  </div>
                </motion.div>
              )}
            </div>

            {/* Suggestions */}
            {messages.length <= 1 && !typing && (
              <div className="px-4 pb-2">
                <p className="text-[10px] font-bold uppercase tracking-widest text-slate-500 mb-2">
                  Try asking
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onClick={() => sendMessage(s)}
                      className="text-[11px] font-bold px-3 py-1.5 rounded-full bg-white/5 hover:bg-purple-500/15 hover:text-purple-300 border border-white/10 hover:border-purple-500/30 text-slate-300 transition-all active:scale-95"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Input */}
            <form
              onSubmit={handleSubmit}
              className="flex items-center gap-2 px-3 py-3 border-t border-white/5 bg-white/[0.015]"
            >
              <input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask Vedra anything..."
                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-3.5 py-2.5 text-sm text-white placeholder-slate-500 outline-none focus:border-purple-500/50 focus:ring-2 focus:ring-purple-500/30 transition-all"
                aria-label="Message Vedra"
              />
              <button
                type="submit"
                disabled={!input.trim()}
                aria-label="Send message"
                className="shrink-0 w-10 h-10 rounded-xl bg-purple-600 hover:bg-purple-500 disabled:bg-white/5 disabled:text-slate-600 text-white flex items-center justify-center transition-all active:scale-95 shadow-lg shadow-purple-900/30 disabled:shadow-none"
              >
                <Send size={15} />
              </button>
            </form>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
};

export default AIAssistant;
