import { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mail,
  Lock,
  User,
  Briefcase,
  Loader2,
  ArrowRight,
  ArrowLeft,
  Cpu,
  Check,
  AlertCircle,
  GraduationCap,
  Sparkles,
} from 'lucide-react';
import useAuthStore from '../store/useAuthStore';
import useToastStore from '../store/useToastStore';
import AnimatedBackground from '../components/AnimatedBackground';

const STEPS = [
  { id: 1, label: 'Account Type' },
  { id: 2, label: 'Personal Info' },
  { id: 3, label: 'Security' },
];

const Register = () => {
  const [step, setStep] = useState(1);
  const [direction, setDirection] = useState(1); // 1 = forward, -1 = back
  const [stepError, setStepError] = useState('');
  const [acceptedTerms, setAcceptedTerms] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    password: '',
    first_name: '',
    last_name: '',
    user_type: 'student',
    company_name: '',
  });

  const { register, isLoading, error, clearError } = useAuthStore();
  const addToast = useToastStore((s) => s.addToast);
  const navigate = useNavigate();

  useEffect(() => () => clearError(), [clearError]);

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
    setStepError('');
  };

  const validateStep = () => {
    if (step === 1) {
      if (!['student', 'hr'].includes(formData.user_type)) {
        setStepError('Pick an account type to continue.');
        return false;
      }
      return true;
    }
    if (step === 2) {
      if (!formData.first_name.trim() || !formData.last_name.trim()) {
        setStepError('Enter your full name.');
        return false;
      }
      if (!/^\S+@\S+\.\S+$/.test(formData.email)) {
        setStepError('Enter a valid email address.');
        return false;
      }
      if (formData.username.trim().length < 3) {
        setStepError('Username must be at least 3 characters.');
        return false;
      }
      if (formData.user_type === 'hr' && !formData.company_name.trim()) {
        setStepError('Company name is required for HR accounts.');
        return false;
      }
      return true;
    }
    if (step === 3) {
      if (formData.password.length < 8) {
        setStepError('Password must be at least 8 characters.');
        return false;
      }
      if (formData.password !== confirmPassword) {
        setStepError('Passwords do not match.');
        return false;
      }
      if (!acceptedTerms) {
        setStepError('Please accept the Terms of Service to continue.');
        return false;
      }
      return true;
    }
    return false;
  };

  const goNext = () => {
    if (!validateStep()) return;
    setDirection(1);
    setStep((s) => Math.min(s + 1, STEPS.length));
    setStepError('');
  };

  const goBack = () => {
    setDirection(-1);
    setStep((s) => Math.max(s - 1, 1));
    setStepError('');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!validateStep()) return;
    const success = await register(formData);
    if (success) {
      addToast({
        type: 'success',
        title: 'Welcome to Autergo',
        message: 'Your account is ready — sign in to get started.',
      });
      navigate('/login');
    }
  };

  // ── Slide variants for step transitions ─────────────────────────────────
  const slideVariants = {
    enter: (dir) => ({ x: dir > 0 ? 40 : -40, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (dir) => ({ x: dir > 0 ? -40 : 40, opacity: 0 }),
  };

  return (
    <div className="grid lg:grid-cols-5 bg-[#020617] min-h-[calc(100vh-5rem)]">
      {/* LEFT: Brand panel */}
      <div className="hidden lg:flex lg:col-span-2 relative overflow-hidden min-h-[calc(100vh-5rem)]">
        <AnimatedBackground variant="auth" />
        <div className="relative z-10 flex flex-col justify-between w-full p-12">
          <Link to="/home" className="inline-flex items-center gap-3 group">
            <div className="w-11 h-11 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-purple-900/30 group-hover:scale-110 transition-transform">
              <Cpu size={22} />
            </div>
            <span className="text-2xl font-black tracking-tighter text-white">
              Autergo <span className="text-purple-400 text-sm align-top ml-1">AI</span>
            </span>
          </Link>

          <div>
            <div className="inline-flex items-center gap-2 bg-purple-500/10 border border-purple-500/20 rounded-full px-3 py-1 mb-5 text-[11px] font-black uppercase tracking-widest text-purple-300">
              <Sparkles size={12} /> Join the platform
            </div>
            <h1 className="text-4xl xl:text-5xl font-black tracking-tighter leading-[1.05] text-white mb-4">
              Build the future of <span className="gradient-text">interviews</span>.
            </h1>
            <p className="text-slate-400 text-sm leading-relaxed max-w-md">
              Whether you're growing your career or hiring world-class talent — Autergo
              gives you a thoughtful, agentic AI partner.
            </p>
          </div>

          <div className="text-[11px] font-bold uppercase tracking-[0.2em] text-slate-500">
            Already a member?{' '}
            <Link to="/login" className="text-purple-400 hover:text-purple-300">
              Sign in
            </Link>
          </div>
        </div>
      </div>

      {/* RIGHT: Wizard */}
      <div className="lg:col-span-3 flex items-center justify-center px-6 py-10 sm:px-10">
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.4 }}
          className="w-full max-w-xl"
        >
          {/* Mobile logo */}
          <div className="lg:hidden flex items-center justify-center mb-6">
            <Link to="/home" className="inline-flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-400 flex items-center justify-center text-white">
                <Cpu size={20} />
              </div>
              <span className="text-xl font-black tracking-tighter text-white">
                Autergo <span className="text-purple-400 text-xs align-top ml-1">AI</span>
              </span>
            </Link>
          </div>

          {/* Step header */}
          <div className="mb-7">
            <div className="flex items-center gap-2 mb-4">
              {STEPS.map((s, idx) => {
                const isDone = step > s.id;
                const isActive = step === s.id;
                return (
                  <div key={s.id} className="flex items-center flex-1">
                    <div
                      className={`relative w-8 h-8 rounded-full flex items-center justify-center text-[11px] font-black transition-all ${
                        isActive
                          ? 'bg-purple-600 text-white ring-4 ring-purple-600/20'
                          : isDone
                          ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40'
                          : 'bg-white/5 text-slate-500 border border-white/10'
                      }`}
                    >
                      {isDone ? <Check size={14} /> : s.id}
                    </div>
                    {idx < STEPS.length - 1 && (
                      <div className="flex-1 h-1 mx-2 rounded-full bg-white/5 overflow-hidden">
                        <motion.div
                          initial={false}
                          animate={{ width: step > s.id ? '100%' : '0%' }}
                          transition={{ duration: 0.5, ease: 'easeOut' }}
                          className="h-full bg-gradient-to-r from-purple-500 to-indigo-400"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
            <p className="text-[10px] font-black uppercase tracking-[0.2em] text-purple-300">
              Step {step} of {STEPS.length}
            </p>
            <h2 className="text-3xl font-black tracking-tighter text-white mt-1">
              {step === 1 && 'How will you use Autergo?'}
              {step === 2 && 'Tell us about yourself'}
              {step === 3 && 'Secure your account'}
            </h2>
          </div>

          {/* Errors */}
          <AnimatePresence>
            {(stepError || error) && (
              <motion.div
                initial={{ opacity: 0, y: -8, height: 0 }}
                animate={{ opacity: 1, y: 0, height: 'auto' }}
                exit={{ opacity: 0, y: -8, height: 0 }}
                className="mb-5 overflow-hidden"
              >
                <div className="flex items-start gap-3 p-3.5 bg-red-500/10 border border-red-500/30 rounded-xl">
                  <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
                  <p className="text-red-300 text-xs leading-relaxed font-medium">
                    {stepError || error}
                  </p>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          <form onSubmit={handleSubmit}>
            <div className="relative min-h-[260px]">
              <AnimatePresence mode="wait" custom={direction}>
                {/* ── STEP 1: Account type ─────────────────────────────────── */}
                {step === 1 && (
                  <motion.div
                    key="step1"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                    className="grid sm:grid-cols-2 gap-4"
                  >
                    {[
                      {
                        value: 'student',
                        title: 'Student / Candidate',
                        desc: 'Practice mock interviews, get coaching, and grow your skills.',
                        icon: GraduationCap,
                      },
                      {
                        value: 'hr',
                        title: 'Recruiter / HR',
                        desc: 'Run hiring drives, screen candidates, and surface top talent.',
                        icon: Briefcase,
                      },
                    ].map((card) => {
                      const Icon = card.icon;
                      const selected = formData.user_type === card.value;
                      return (
                        <button
                          key={card.value}
                          type="button"
                          onClick={() => setFormData({ ...formData, user_type: card.value })}
                          className={`relative text-left p-5 rounded-2xl border-2 transition-all active:scale-[0.99] ${
                            selected
                              ? 'border-purple-500/60 bg-purple-500/10 shadow-[0_0_40px_rgba(124,58,237,0.2)]'
                              : 'border-white/10 bg-white/[0.02] hover:border-white/20 hover:bg-white/5'
                          }`}
                        >
                          <div
                            className={`w-12 h-12 rounded-xl flex items-center justify-center mb-4 transition-colors ${
                              selected
                                ? 'bg-purple-500/20 text-purple-300'
                                : 'bg-white/5 text-slate-400'
                            }`}
                          >
                            <Icon size={22} />
                          </div>
                          <p className="text-white font-black tracking-tight text-base mb-1">
                            {card.title}
                          </p>
                          <p className="text-slate-400 text-xs leading-relaxed">
                            {card.desc}
                          </p>
                          {selected && (
                            <span className="absolute top-3 right-3 w-6 h-6 rounded-full bg-purple-500 flex items-center justify-center text-white">
                              <Check size={12} />
                            </span>
                          )}
                        </button>
                      );
                    })}
                  </motion.div>
                )}

                {/* ── STEP 2: Personal info ────────────────────────────────── */}
                {step === 2 && (
                  <motion.div
                    key="step2"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                    className="space-y-4"
                  >
                    <div className="grid grid-cols-2 gap-3">
                      <div>
                        <label className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                          First Name
                        </label>
                        <input
                          name="first_name"
                          type="text"
                          required
                          value={formData.first_name}
                          onChange={handleChange}
                          className="block w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                          placeholder="John"
                          autoComplete="given-name"
                        />
                      </div>
                      <div>
                        <label className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                          Last Name
                        </label>
                        <input
                          name="last_name"
                          type="text"
                          required
                          value={formData.last_name}
                          onChange={handleChange}
                          className="block w-full px-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                          placeholder="Doe"
                          autoComplete="family-name"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                        Email
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                          <Mail size={16} />
                        </div>
                        <input
                          name="email"
                          type="email"
                          required
                          value={formData.email}
                          onChange={handleChange}
                          className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                          placeholder="john@example.com"
                          autoComplete="email"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                        Username
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                          <User size={16} />
                        </div>
                        <input
                          name="username"
                          type="text"
                          required
                          value={formData.username}
                          onChange={handleChange}
                          className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                          placeholder="johndoe"
                          autoComplete="username"
                        />
                      </div>
                    </div>

                    {formData.user_type === 'hr' && (
                      <div>
                        <label className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                          Company Name
                        </label>
                        <div className="relative">
                          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                            <Briefcase size={16} />
                          </div>
                          <input
                            name="company_name"
                            type="text"
                            required
                            value={formData.company_name}
                            onChange={handleChange}
                            className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-indigo-500/40 focus:border-indigo-500/50 outline-none transition-all"
                            placeholder="Acme Corp"
                            autoComplete="organization"
                          />
                        </div>
                      </div>
                    )}
                  </motion.div>
                )}

                {/* ── STEP 3: Security ─────────────────────────────────────── */}
                {step === 3 && (
                  <motion.div
                    key="step3"
                    custom={direction}
                    variants={slideVariants}
                    initial="enter"
                    animate="center"
                    exit="exit"
                    transition={{ duration: 0.28, ease: [0.22, 1, 0.36, 1] }}
                    className="space-y-4"
                  >
                    <div>
                      <label className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                        Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                          <Lock size={16} />
                        </div>
                        <input
                          name="password"
                          type="password"
                          required
                          minLength={8}
                          value={formData.password}
                          onChange={handleChange}
                          className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                          placeholder="At least 8 characters"
                          autoComplete="new-password"
                        />
                      </div>
                    </div>

                    <div>
                      <label className="block text-[10px] font-black uppercase text-slate-400 tracking-widest mb-1.5 ml-1">
                        Confirm Password
                      </label>
                      <div className="relative">
                        <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-500">
                          <Lock size={16} />
                        </div>
                        <input
                          name="confirm_password"
                          type="password"
                          required
                          minLength={8}
                          value={confirmPassword}
                          onChange={(e) => {
                            setConfirmPassword(e.target.value);
                            setStepError('');
                          }}
                          className="block w-full pl-10 pr-3 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500/40 focus:border-purple-500/50 outline-none transition-all"
                          placeholder="Re-enter password"
                          autoComplete="new-password"
                        />
                      </div>
                    </div>

                    <label className="flex items-start gap-3 p-4 rounded-xl border border-white/10 bg-white/[0.02] cursor-pointer hover:bg-white/5 transition-colors">
                      <input
                        type="checkbox"
                        checked={acceptedTerms}
                        onChange={(e) => {
                          setAcceptedTerms(e.target.checked);
                          setStepError('');
                        }}
                        className="mt-0.5 rounded border-white/10 bg-white/5 text-purple-600 focus:ring-purple-500"
                      />
                      <span className="text-xs text-slate-400 leading-relaxed">
                        I agree to the{' '}
                        <Link
                          to="/terms"
                          className="text-purple-400 font-bold hover:text-purple-300"
                        >
                          Terms of Service
                        </Link>{' '}
                        and{' '}
                        <Link
                          to="/privacy"
                          className="text-purple-400 font-bold hover:text-purple-300"
                        >
                          Privacy Policy
                        </Link>
                        .
                      </span>
                    </label>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>

            {/* Wizard nav */}
            <div className="flex items-center justify-between gap-3 mt-8">
              <button
                type="button"
                onClick={goBack}
                disabled={step === 1}
                className="inline-flex items-center gap-2 px-5 py-3 rounded-xl text-xs font-black uppercase tracking-widest text-slate-300 hover:text-white bg-white/5 hover:bg-white/10 border border-white/10 disabled:opacity-40 disabled:cursor-not-allowed transition-all active:scale-95"
              >
                <ArrowLeft size={14} /> Back
              </button>

              {step < STEPS.length ? (
                <button
                  type="button"
                  onClick={goNext}
                  className="inline-flex items-center gap-2 px-7 py-3 rounded-xl text-xs font-black uppercase tracking-widest bg-purple-600 text-white hover:bg-purple-500 shadow-[0_0_40px_rgba(147,51,234,0.3)] transition-all active:scale-95"
                >
                  Continue <ArrowRight size={14} />
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isLoading}
                  className="relative inline-flex items-center gap-2 px-7 py-3 rounded-xl text-xs font-black uppercase tracking-widest bg-purple-600 text-white hover:bg-purple-500 shadow-[0_0_40px_rgba(147,51,234,0.3)] transition-all active:scale-95 disabled:opacity-80 overflow-hidden"
                >
                  {isLoading && (
                    <span className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent animate-button-shimmer" />
                  )}
                  {isLoading ? (
                    <>
                      <Loader2 className="animate-spin" size={14} /> Creating...
                    </>
                  ) : (
                    <>
                      Create Account <ArrowRight size={14} />
                    </>
                  )}
                </button>
              )}
            </div>
          </form>

          <p className="lg:hidden mt-6 text-center text-sm text-slate-500">
            Already have an account?{' '}
            <Link to="/login" className="text-purple-400 font-bold hover:text-purple-300">
              Sign in
            </Link>
          </p>
        </motion.div>
      </div>
    </div>
  );
};

export default Register;
