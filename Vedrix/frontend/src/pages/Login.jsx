import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mail,
  Lock,
  Loader2,
  ArrowRight,
  AlertCircle,
  Sparkles,
  Brain,
  ShieldCheck,
  TrendingUp,
  Cpu,
} from 'lucide-react';
import useAuthStore from '../store/useAuthStore';
import AnimatedBackground from '../components/AnimatedBackground';

const FEATURES = [
  {
    icon: Brain,
    title: 'Adaptive AI Interviews',
    desc: 'A 10-agent orchestrator tailors every question to the candidate.',
  },
  {
    icon: TrendingUp,
    title: 'Real Coaching, Not Scores',
    desc: 'Personalized growth plans built from every session.',
  },
  {
    icon: ShieldCheck,
    title: 'Enterprise-grade Trust',
    desc: 'Audit trails, proctoring, and SOC-ready by design.',
  },
];

const Login = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [featureIdx, setFeatureIdx] = useState(0);
  const { login, isLoading, error, clearError } = useAuthStore();
  const navigate = useNavigate();

  useEffect(() => {
    const id = setInterval(() => setFeatureIdx((i) => (i + 1) % FEATURES.length), 4500);
    return () => clearInterval(id);
  }, []);

  useEffect(() => {
    return () => clearError();
  }, [clearError]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    const success = await login(username, password);
    if (success) navigate('/');
  };

  const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';
  const ActiveIcon = FEATURES[featureIdx].icon;

  return (
    <div className="grid lg:grid-cols-5 bg-[#020617] min-h-[calc(100vh-5rem)]">
      {/* ── LEFT: Hero showcase (60% / 3 of 5) ─────────────────────────── */}
      <div className="hidden lg:flex lg:col-span-3 relative overflow-hidden min-h-[calc(100vh-5rem)]">
        <AnimatedBackground variant="auth" />

        <div className="relative z-10 flex flex-col justify-between w-full p-12 xl:p-16">
          {/* Logo + tagline */}
          <div>
            <Link to="/home" className="inline-flex items-center gap-3 group">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-purple-900/30 group-hover:scale-110 transition-transform">
                <Cpu size={22} />
              </div>
              <span className="text-2xl font-black tracking-tighter text-white">
                Autergo <span className="text-purple-400 text-sm align-top ml-1">AI</span>
              </span>
            </Link>
          </div>

          {/* Center: pitch + animated mockup */}
          <div className="max-w-xl">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 rounded-full px-3 py-1 mb-5 text-[11px] font-black uppercase tracking-widest text-purple-300"
            >
              <Sparkles size={12} />
              The next generation of hiring intelligence
            </motion.div>

            <h1 className="text-5xl xl:text-6xl font-black tracking-tighter leading-[1.05] text-white mb-5">
              Where talent meets <span className="gradient-text">an agentic AI</span>.
            </h1>
            <p className="text-slate-400 text-base leading-relaxed mb-8 max-w-lg">
              Sign in to run intelligent interviews, see live agent activity, and unlock
              coaching that adapts in real time.
            </p>

            {/* Animated AI mockup card */}
            <div className="cyber-border max-w-md p-5 rounded-2xl">
              <div className="flex items-center gap-3 mb-4">
                <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-500 flex items-center justify-center text-white">
                  <Sparkles size={16} />
                </div>
                <div>
                  <p className="text-white font-bold text-sm">Vedra · Live</p>
                  <p className="text-[10px] font-bold uppercase tracking-widest text-emerald-400">
                    10 agents online
                  </p>
                </div>
              </div>

              <AnimatePresence mode="wait">
                <motion.div
                  key={featureIdx}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -8 }}
                  transition={{ duration: 0.32 }}
                  className="flex items-start gap-3 bg-white/5 border border-white/5 rounded-xl p-3.5"
                >
                  <div className="shrink-0 w-9 h-9 rounded-lg bg-purple-500/15 text-purple-300 flex items-center justify-center">
                    <ActiveIcon size={16} />
                  </div>
                  <div className="min-w-0">
                    <p className="text-white font-bold text-sm leading-snug">
                      {FEATURES[featureIdx].title}
                    </p>
                    <p className="text-slate-400 text-xs leading-relaxed mt-0.5">
                      {FEATURES[featureIdx].desc}
                    </p>
                  </div>
                </motion.div>
              </AnimatePresence>

              {/* progress dots */}
              <div className="flex items-center gap-1.5 mt-4">
                {FEATURES.map((_, i) => (
                  <button
                    key={i}
                    type="button"
                    onClick={() => setFeatureIdx(i)}
                    aria-label={`Show feature ${i + 1}`}
                    className={`h-1 rounded-full transition-all ${
                      i === featureIdx ? 'w-8 bg-purple-400' : 'w-3 bg-white/15 hover:bg-white/30'
                    }`}
                  />
                ))}
              </div>
            </div>
          </div>

          {/* Trusted by */}
          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">
            Trusted by{' '}
            <span className="text-white">340+ companies</span> across 27 countries
          </div>
        </div>
      </div>

      {/* ── RIGHT: Form (40% / 2 of 5) ────────────────────────────────── */}
      <div className="lg:col-span-2 flex items-center justify-center px-6 py-10 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center mb-8">
            <Link to="/home" className="inline-flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-400 flex items-center justify-center text-white">
                <Cpu size={20} />
              </div>
              <span className="text-xl font-black tracking-tighter text-white">
                Autergo <span className="text-purple-400 text-xs align-top ml-1">AI</span>
              </span>
            </Link>
          </div>

          <div className="mb-8">
            <h2 className="text-3xl font-black tracking-tighter text-white mb-2">
              Welcome back
            </h2>
            <p className="text-slate-400 text-sm">
              Sign in to your Autergo workspace and pick up where you left off.
            </p>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                className="mb-5 overflow-hidden"
              >
                <div className="flex items-start gap-3 p-3.5 bg-red-500/10 border border-red-500/30 rounded-xl">
                  <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
                  <div className="text-red-300 text-xs leading-relaxed">
                    <p className="font-bold mb-0.5">We couldn't sign you in</p>
                    <p className="text-red-400/80">{error}</p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Social buttons (cosmetic, link to backend OAuth) */}
          <div className="grid grid-cols-2 gap-3 mb-5">
            <a
              href={`${API_BASE_URL}/auth/google/login`}
              className="flex items-center justify-center gap-2 py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all active:scale-95 text-slate-200 text-xs font-bold uppercase tracking-widest"
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24">
                <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-3.22 3.28-7.42 3.28-12.09z" fill="#4285F4" />
                <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853" />
                <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.16H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.84l3.66-2.75z" fill="#FBBC05" />
                <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.16l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335" />
              </svg>
              Google
            </a>
            <a
              href={`${API_BASE_URL}/auth/github/login`}
              className="flex items-center justify-center gap-2 py-3 bg-white/5 border border-white/10 rounded-xl hover:bg-white/10 transition-all active:scale-95 text-slate-200 text-xs font-bold uppercase tracking-widest"
            >
              <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              GitHub
            </a>
          </div>

          {/* Divider */}
          <div className="flex items-center gap-3 mb-5">
            <div className="flex-1 h-px bg-white/10" />
            <span className="text-[10px] font-black uppercase text-slate-500 tracking-[0.2em]">
              or continue with email
            </span>
            <div className="flex-1 h-px bg-white/10" />
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="login-username"
                className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1"
              >
                Username
              </label>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Mail size={16} />
                </div>
                <input
                  id="login-username"
                  type="text"
                  required
                  className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                  placeholder="Your username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoComplete="username"
                />
              </div>
            </div>

            <div>
              <div className="flex items-center justify-between mb-1.5 ml-1">
                <label
                  htmlFor="login-password"
                  className="block text-[10px] font-black uppercase text-slate-400 tracking-widest"
                >
                  Password
                </label>
                <Link
                  to="/forgot-password"
                  className="text-[10px] font-bold text-purple-400 hover:text-purple-300 uppercase tracking-widest"
                >
                  Forgot?
                </Link>
              </div>
              <div className="relative">
                <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                  <Lock size={16} />
                </div>
                <input
                  id="login-password"
                  type="password"
                  required
                  className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
            </div>

            <label className="flex items-center text-slate-400 text-xs font-bold cursor-pointer select-none">
              <input
                type="checkbox"
                className="rounded border-white/10 bg-white/5 text-purple-600 focus:ring-purple-500 mr-2"
              />
              Keep me signed in
            </label>

            <button
              type="submit"
              disabled={isLoading}
              className="relative w-full bg-purple-600 text-white py-3.5 px-4 rounded-xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 shadow-[0_0_40px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-80 overflow-hidden"
            >
              {isLoading && (
                <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-button-shimmer" />
              )}
              {isLoading ? (
                <>
                  <Loader2 className="animate-spin" size={18} />
                  <span>Signing in...</span>
                </>
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight size={18} />
                </>
              )}
            </button>
          </form>

          <p className="mt-7 text-center text-sm text-slate-500">
            Don't have an account?{' '}
            <Link
              to="/register"
              className="text-purple-400 font-bold hover:text-purple-300"
            >
              Create an account
            </Link>
          </p>

          {/* Mobile-only social proof */}
          <div className="lg:hidden mt-8 text-center text-[10px] font-bold uppercase tracking-[0.2em] text-slate-600">
            Trusted by 340+ companies
          </div>
        </motion.div>
      </div>
    </div>
  );
};

export default Login;
