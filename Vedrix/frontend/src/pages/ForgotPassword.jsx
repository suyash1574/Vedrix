import { useState } from 'react';
import { Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Mail, Loader2, ArrowRight, AlertCircle, Sparkles, Cpu, CheckCircle } from 'lucide-react';
import apiClient from '../services/api';
import AnimatedBackground from '../components/AnimatedBackground';

const ForgotPassword = () => {
  const [email, setEmail] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);
    try {
      await apiClient.post('/auth/forgot-password', { email });
      setSuccess(true);
    } catch (err) {
      setError(err.response?.data?.detail || 'Something went wrong. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="grid lg:grid-cols-5 bg-[#020617] min-h-[calc(100vh-5rem)] w-full">
      {/* ── LEFT: Visual presentation ─────────────────────────── */}
      <div className="hidden lg:flex lg:col-span-3 relative overflow-hidden min-h-[calc(100vh-5rem)]">
        <AnimatedBackground variant="auth" />

        <div className="relative z-10 flex flex-col justify-between w-full p-12 xl:p-16">
          <div>
            <Link to="/" className="inline-flex items-center gap-3 group">
              <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-purple-900/30 group-hover:scale-110 transition-transform">
                <Cpu size={22} />
              </div>
              <span className="text-2xl font-black tracking-tighter text-white">
                Autergo <span className="text-purple-400 text-sm align-top ml-1">AI</span>
              </span>
            </Link>
          </div>

          <div className="max-w-xl">
            <motion.div
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6 }}
              className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 rounded-full px-3 py-1 mb-5 text-[11px] font-black uppercase tracking-widest text-purple-300"
            >
              <Sparkles size={12} />
              Account Security Center
            </motion.div>

            <h1 className="text-5xl xl:text-6xl font-black tracking-tighter leading-[1.05] text-white mb-5">
              Secure password <span className="gradient-text">recovery</span>.
            </h1>
            <p className="text-slate-400 text-base leading-relaxed mb-8 max-w-lg">
              If you have forgotten your credentials, enter your registered email address and we'll send you a secure link to reset it.
            </p>
          </div>

          <div className="text-slate-500 text-[11px] font-bold uppercase tracking-[0.2em]">
            Autergo AI Security Framework
          </div>
        </div>
      </div>

      {/* ── RIGHT: Forgot Password Form ─────────────────────────── */}
      <div className="lg:col-span-2 flex items-center justify-center px-6 py-10 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-md"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center mb-8">
            <Link to="/" className="inline-flex items-center gap-3">
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
              Reset Password
            </h2>
            <p className="text-slate-400 text-sm">
              Enter your email address below to request a secure password reset link.
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
                    <p className="font-bold mb-0.5">Request Failed</p>
                    <p className="text-red-400/80">{error}</p>
                  </div>
                </div>
              </motion.div>
            )}

            {success && (
              <motion.div
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                className="mb-5 overflow-hidden"
              >
                <div className="flex items-start gap-3 p-4 bg-emerald-500/10 border border-emerald-500/30 rounded-xl">
                  <CheckCircle size={16} className="text-emerald-400 shrink-0 mt-0.5" />
                  <div className="text-emerald-300 text-xs leading-relaxed">
                    <p className="font-bold mb-0.5">Check Your Inbox</p>
                    <p className="text-emerald-400/80">
                      If the email exists in our system, a password reset link has been sent to you.
                    </p>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {!success && (
            <form onSubmit={handleSubmit} className="space-y-5">
              <div>
                <label
                  htmlFor="forgot-email"
                  className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1"
                >
                  Email Address
                </label>
                <div className="relative">
                  <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                    <Mail size={16} />
                  </div>
                  <input
                    id="forgot-email"
                    type="email"
                    required
                    className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                    placeholder="you@example.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="relative w-full bg-purple-600 text-white py-3.5 px-4 rounded-xl font-black uppercase tracking-widest text-sm hover:bg-purple-500 shadow-[0_0_40px_rgba(147,51,234,0.3)] transition-all flex items-center justify-center gap-2 active:scale-95 disabled:opacity-80 overflow-hidden"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="animate-spin" size={18} />
                    <span>Sending Reset Link...</span>
                  </>
                ) : (
                  <>
                    <span>Send Reset Link</span>
                    <ArrowRight size={18} />
                  </>
                )}
              </button>
            </form>
          )}

          <p className="mt-7 text-center text-sm text-slate-500">
            Remembered your password?{' '}
            <Link
              to="/login"
              className="text-purple-400 font-bold hover:text-purple-300"
            >
              Sign In
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
};

export default ForgotPassword;
