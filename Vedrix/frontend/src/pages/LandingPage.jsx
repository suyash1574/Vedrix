import { useState, useEffect, useRef } from 'react';
import { Mic, BarChart3, ShieldCheck, ChevronRight, BrainCircuit, User, LogOut, Star, Check, X as XIcon, Building2 } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { motion, useInView } from 'framer-motion';
import useAuthStore from '../store/useAuthStore';

/* ── Animated Counter Hook ─────────────────────────────────────────────────── */
const useCountUp = (end, duration = 2000, inView = true) => {
  const [count, setCount] = useState(0);
  const started = useRef(false);

  useEffect(() => {
    if (!inView) return;
    if (started.current) return;
    started.current = true;

    let startTime = null;
    const animate = (timestamp) => {
      if (!startTime) startTime = timestamp;
      const progress = Math.min((timestamp - startTime) / duration, 1);
      setCount(Math.floor(progress * end));
      if (progress < 1) requestAnimationFrame(animate);
    };
    requestAnimationFrame(animate);
  }, [end, duration, inView]);

  return count;
};

/* ── Typewriter Effect ─────────────────────────────────────────────────────── */
const TypewriterText = ({ text, speed = 40 }) => {
  const [displayed, setDisplayed] = useState('');
  const ref = useRef(null);
  const inView = useInView(ref, { once: true });
  const started = useRef(false);

  useEffect(() => {
    if (!inView || started.current) return;
    started.current = true;
    let i = 0;
    const interval = setInterval(() => {
      setDisplayed(text.slice(0, i + 1));
      i++;
      if (i >= text.length) clearInterval(interval);
    }, speed);
    return () => clearInterval(interval);
  }, [inView, text, speed]);

  return (
    <span ref={ref}>
      {displayed}
      {displayed.length < text.length && <span className="typewriter-cursor" />}
    </span>
  );
};

/* ── Scroll Fade-In Section ────────────────────────────────────────────────── */
const FadeInSection = ({ children, delay = 0, className = '' }) => {
  const ref = useRef(null);
  const inView = useInView(ref, { once: true, margin: '-50px' });

  return (
    <motion.div
      ref={ref}
      initial={{ opacity: 0, y: 30 }}
      animate={inView ? { opacity: 1, y: 0 } : {}}
      transition={{ duration: 0.6, delay, ease: 'easeOut' }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

const LandingPage = () => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/home');
  };

  const getDashboardPath = () => {
    if (user?.user_type === 'hr') return '/hr';
    if (user?.user_type === 'admin') return '/admin';
    return '/dashboard';
  };

  const containerRef = useRef(null);
  const inView = useInView(containerRef, { once: true });

  const interviewCount = useCountUp(12847, 2500, inView);
  const companyCount = useCountUp(340, 2000, inView);
  const satisfactionCount = useCountUp(97, 1800, inView);

  return (
    <div className="bg-[#020617] overflow-hidden">

      {/* ── HERO ─────────────────────────────────────────────────────────── */}
      <section className="relative min-h-[calc(100vh-80px)] flex items-center px-6 md:px-12">
        {/* Gradient mesh background */}
        <div className="absolute inset-0 gradient-mesh pointer-events-none" />

        {/* Ambient glows */}
        <div className="absolute top-0 left-[-10%] w-[50%] h-[70%] bg-purple-900/20 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute bottom-0 right-[-10%] w-[50%] h-[60%] bg-indigo-900/15 blur-[120px] rounded-full pointer-events-none" />

        {/* Floating particles */}
        <div className="absolute inset-0 pointer-events-none overflow-hidden">
          <div className="particle particle-1" style={{ top: '15%', left: '10%' }} />
          <div className="particle particle-2" style={{ top: '25%', right: '15%' }} />
          <div className="particle particle-3" style={{ top: '60%', left: '20%' }} />
          <div className="particle particle-4" style={{ top: '40%', right: '25%' }} />
          <div className="particle particle-5" style={{ top: '75%', left: '60%' }} />
          <div className="particle particle-6" style={{ top: '10%', right: '40%' }} />
          <div className="particle particle-7" style={{ top: '85%', left: '35%' }} />
          <div className="particle particle-8" style={{ top: '50%', left: '80%' }} />
        </div>

        <div className="max-w-7xl mx-auto w-full grid grid-cols-1 lg:grid-cols-2 gap-16 items-center relative z-10 py-16">

          {/* Left */}
          <motion.div
            initial={{ opacity: 0, x: -30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, ease: 'easeOut' }}
            className="space-y-8"
          >
            <div className="inline-flex items-center space-x-2 bg-purple-500/10 border border-purple-500/20 px-4 py-2 rounded-full">
              <span className="w-2 h-2 bg-purple-400 rounded-full pulse-glow-purple" />
              <span className="text-xs font-bold uppercase tracking-widest text-purple-300">AI-Powered Interview Platform</span>
            </div>

            <h1 className="text-5xl md:text-6xl lg:text-7xl font-black text-white leading-[1.0] tracking-tight">
              Smarter Interviews.<br />
              <span className="gradient-text">
                Better Hires.
              </span>
            </h1>

            <p className="text-lg text-slate-400 max-w-xl leading-relaxed">
              Autergo conducts adaptive AI interviews, evaluates candidates in real-time, and delivers structured reports — so your team can focus on the right people.
            </p>

            <div className="flex flex-wrap gap-4">
              {isAuthenticated ? (
                <>
                  <div className="inline-flex items-center space-x-3 bg-white/5 border border-white/10 px-6 py-3 rounded-2xl">
                    <div className="w-10 h-10 bg-purple-600 rounded-full flex items-center justify-center">
                      <User size={18} className="text-white" />
                    </div>
                    <div className="text-left">
                      <p className="text-white font-bold text-sm">{user?.first_name} {user?.last_name}</p>
                      <p className="text-slate-400 text-xs capitalize">{user?.user_type}</p>
                    </div>
                  </div>
                  <Link to={getDashboardPath()}
                    className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-8 py-4 rounded-2xl transition-all shadow-[0_0_40px_rgba(124,58,237,0.35)] active:scale-95">
                    <span>Go to Dashboard</span>
                    <ChevronRight size={18} />
                  </Link>
                  <button onClick={handleLogout}
                    className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-8 py-4 rounded-2xl transition-all">
                    <span>Logout</span>
                    <LogOut size={18} />
                  </button>
                </>
              ) : (
                <>
                  <Link to="/register"
                    className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-bold px-8 py-4 rounded-2xl transition-all shadow-[0_0_40px_rgba(124,58,237,0.35)] active:scale-95">
                    <span>Get Started Free</span>
                    <ChevronRight size={18} />
                  </Link>
                  <Link to="/login"
                    className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-8 py-4 rounded-2xl transition-all">
                    <span>Sign In</span>
                  </Link>
                </>
              )}
            </div>

            <div className="flex items-center space-x-8 pt-4 border-t border-white/5">
              {[
                { val: 'Adaptive', label: 'AI Questions' },
                { val: 'Real-time', label: 'Evaluation' },
                { val: 'Instant', label: 'Reports' },
              ].map(s => (
                <div key={s.label}>
                  <p className="text-white font-black text-lg">{s.val}</p>
                  <p className="text-slate-500 text-xs font-bold uppercase tracking-widest">{s.label}</p>
                </div>
              ))}
            </div>
          </motion.div>

          {/* Right — mockup card */}
          <motion.div
            initial={{ opacity: 0, x: 30 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease: 'easeOut' }}
            className="relative hidden lg:block"
          >
            <div className="absolute inset-0 bg-purple-600/15 blur-[80px] rounded-full" />
            <div className="relative bg-white/[0.03] border border-white/10 rounded-[2rem] p-8 shadow-2xl backdrop-blur-sm border-gradient">
              {/* Fake browser chrome */}
              <div className="flex items-center space-x-2 mb-6">
                <div className="w-3 h-3 rounded-full bg-red-500/60" />
                <div className="w-3 h-3 rounded-full bg-amber-500/60" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/60" />
                <div className="ml-4 flex-1 h-6 bg-white/5 rounded-lg" />
              </div>

              {/* AI interviewer card */}
              <div className="bg-white/5 border border-white/10 rounded-2xl p-6 mb-4">
                <div className="flex items-center space-x-3 mb-4">
                  <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center">
                    <BrainCircuit size={20} className="text-white" />
                  </div>
                  <div>
                    <p className="text-white font-bold text-sm">Autergo AI Interviewer</p>
                    <div className="flex items-center space-x-1">
                      <div className="w-1.5 h-1.5 bg-emerald-400 rounded-full pulse-glow" />
                      <p className="text-emerald-400 text-[10px] font-bold uppercase tracking-widest">Live</p>
                    </div>
                  </div>
                </div>
                <div className="bg-white/5 rounded-xl p-4 text-sm text-slate-300 italic leading-relaxed">
                  "<TypewriterText text="Can you walk me through how you'd design a scalable REST API for a high-traffic application?" speed={35} />"
                </div>
              </div>

              {/* Score bars */}
              <div className="space-y-3">
                {[
                  { label: 'Technical Accuracy', pct: 88, color: 'bg-purple-500' },
                  { label: 'Communication', pct: 74, color: 'bg-indigo-400' },
                  { label: 'Depth of Knowledge', pct: 91, color: 'bg-violet-500' },
                ].map(b => (
                  <div key={b.label}>
                    <div className="flex justify-between mb-1">
                      <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">{b.label}</span>
                      <span className="text-[10px] font-black text-white">{b.pct}%</span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <motion.div
                        initial={{ width: 0 }}
                        animate={{ width: `${b.pct}%` }}
                        transition={{ duration: 1.5, delay: 0.8, ease: 'easeOut' }}
                        className={`h-full ${b.color} rounded-full`}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ── LIVE COUNTER SECTION ───────────────────────────────────────────── */}
      <section className="py-16 px-6 md:px-12 border-t border-white/5">
        <div className="max-w-5xl mx-auto">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8" ref={containerRef}>
            {[
              { count: interviewCount, suffix: '+', label: 'Interviews Conducted', color: 'text-purple-400' },
              { count: companyCount, suffix: '+', label: 'Companies Trust Us', color: 'text-indigo-400' },
              { count: satisfactionCount, suffix: '%', label: 'Satisfaction Rate', color: 'text-emerald-400' },
            ].map((stat) => (
              <FadeInSection key={stat.label} className="text-center">
                <p className={`text-5xl md:text-6xl font-black ${stat.color} count-up`}>
                  {stat.count.toLocaleString()}{stat.suffix}
                </p>
                <p className="text-slate-500 text-xs font-black uppercase tracking-widest mt-2">{stat.label}</p>
              </FadeInSection>
            ))}
          </div>
        </div>
      </section>

      {/* ── TRUSTED BY ─────────────────────────────────────────────────────── */}
      <section className="py-12 px-6 md:px-12 border-t border-white/5">
        <div className="max-w-5xl mx-auto">
          <p className="text-center text-xs font-black uppercase text-slate-600 tracking-widest mb-8">Trusted by innovative teams</p>
          <div className="flex flex-wrap items-center justify-center gap-8 md:gap-12 opacity-40">
            {['TechCorp', 'InnovateLab', 'DataFlow', 'CloudScale', 'NexGen'].map((name) => (
              <div key={name} className="flex items-center space-x-2">
                <Building2 size={20} className="text-slate-500" />
                <span className="text-slate-500 font-bold text-sm">{name}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ── FEATURES ─────────────────────────────────────────────────────── */}
      <section className="py-24 px-6 md:px-12 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <FadeInSection className="text-center mb-16">
            <p className="text-purple-400 text-xs font-black uppercase tracking-[0.3em] mb-3">What Autergo Does</p>
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight">
              Everything you need to hire better
            </h2>
          </FadeInSection>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {[
              {
                icon: BrainCircuit,
                title: 'Adaptive AI',
                desc: 'Questions evolve based on every answer. No two interviews are the same.',
                color: 'text-purple-400',
                bg: 'bg-purple-500/10 border-purple-500/20',
              },
              {
                icon: Mic,
                title: 'Voice-First',
                desc: 'Candidates speak naturally. Groq Whisper transcribes in under 300ms.',
                color: 'text-indigo-400',
                bg: 'bg-indigo-500/10 border-indigo-500/20',
              },
              {
                icon: BarChart3,
                title: 'Live Scoring',
                desc: 'Real-time evaluation across accuracy, clarity, depth, and communication.',
                color: 'text-violet-400',
                bg: 'bg-violet-500/10 border-violet-500/20',
              },
              {
                icon: ShieldCheck,
                title: 'Fair & Unbiased',
                desc: 'Every candidate gets the same structured, objective assessment.',
                color: 'text-emerald-400',
                bg: 'bg-emerald-500/10 border-emerald-500/20',
              },
            ].map((f, i) => (
              <FadeInSection key={f.title} delay={i * 0.1}>
                <div className="glass-card rounded-3xl p-8 h-full group">
                  <div className={`w-12 h-12 ${f.bg} border rounded-2xl flex items-center justify-center mb-6`}>
                    <f.icon size={22} className={f.color} />
                  </div>
                  <h3 className="text-white font-black text-lg mb-2">{f.title}</h3>
                  <p className="text-slate-400 text-sm leading-relaxed">{f.desc}</p>
                </div>
              </FadeInSection>
            ))}
          </div>
        </div>
      </section>

      {/* ── TESTIMONIALS ───────────────────────────────────────────────────── */}
      <section className="py-24 px-6 md:px-12 border-t border-white/5">
        <div className="max-w-7xl mx-auto">
          <FadeInSection className="text-center mb-16">
            <p className="text-purple-400 text-xs font-black uppercase tracking-[0.3em] mb-3">What People Say</p>
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight">
              Loved by recruiters & candidates
            </h2>
          </FadeInSection>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {[
              {
                name: 'Sarah Chen',
                role: 'Head of Talent, TechCorp',
                text: 'Autergo cut our screening time by 70%. The AI interviews are remarkably natural and the reports are incredibly detailed.',
                stars: 5,
              },
              {
                name: 'Marcus Johnson',
                role: 'Software Engineer',
                text: 'Best interview experience I\'ve had. The AI adapted to my answers and the feedback helped me improve for future interviews.',
                stars: 5,
              },
              {
                name: 'Priya Patel',
                role: 'VP Engineering, DataFlow',
                text: 'We hired 3x faster with better quality candidates. The bias-free evaluation gives us confidence in every decision.',
                stars: 5,
              },
            ].map((t, i) => (
              <FadeInSection key={t.name} delay={i * 0.15}>
                <div className="glass-card rounded-3xl p-8 h-full flex flex-col">
                  <div className="flex items-center space-x-1 mb-4">
                    {Array.from({ length: t.stars }).map((_, j) => (
                      <Star key={j} size={14} className="text-amber-400 fill-amber-400" />
                    ))}
                  </div>
                  <p className="text-slate-300 text-sm leading-relaxed flex-1 italic">"{t.text}"</p>
                  <div className="mt-6 pt-4 border-t border-white/5">
                    <p className="text-white font-bold text-sm">{t.name}</p>
                    <p className="text-slate-500 text-xs">{t.role}</p>
                  </div>
                </div>
              </FadeInSection>
            ))}
          </div>
        </div>
      </section>

      {/* ── COMPARISON TABLE ───────────────────────────────────────────────── */}
      <section className="py-24 px-6 md:px-12 border-t border-white/5">
        <div className="max-w-4xl mx-auto">
          <FadeInSection className="text-center mb-16">
            <p className="text-purple-400 text-xs font-black uppercase tracking-[0.3em] mb-3">Why Autergo</p>
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight">
              Autergo vs Traditional Interviews
            </h2>
          </FadeInSection>

          <FadeInSection>
            <div className="glass-card rounded-3xl overflow-hidden">
              <table className="w-full text-left">
                <thead>
                  <tr className="border-b border-white/5">
                    <th className="px-6 py-5 text-xs font-black uppercase text-slate-500 tracking-widest">Feature</th>
                    <th className="px-6 py-5 text-xs font-black uppercase text-purple-400 tracking-widest text-center">Autergo AI</th>
                    <th className="px-6 py-5 text-xs font-black uppercase text-slate-500 tracking-widest text-center">Traditional</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {[
                    { feature: 'Scheduling overhead', vedrix: true, traditional: false },
                    { feature: 'Consistent evaluation', vedrix: true, traditional: false },
                    { feature: 'Available 24/7', vedrix: true, traditional: false },
                    { feature: 'Instant detailed reports', vedrix: true, traditional: false },
                    { feature: 'Bias-free assessment', vedrix: true, traditional: false },
                    { feature: 'Scales to 1000+ candidates', vedrix: true, traditional: false },
                    { feature: 'Adaptive difficulty', vedrix: true, traditional: false },
                  ].map((row) => (
                    <tr key={row.feature} className="hover:bg-white/[0.02] transition-colors">
                      <td className="px-6 py-4 text-sm text-slate-300 font-medium">{row.feature}</td>
                      <td className="px-6 py-4 text-center">
                        <Check size={18} className="text-emerald-400 mx-auto" />
                      </td>
                      <td className="px-6 py-4 text-center">
                        <XIcon size={18} className="text-red-400/60 mx-auto" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </FadeInSection>
        </div>
      </section>

      {/* ── HOW IT WORKS ─────────────────────────────────────────────────── */}
      <section className="py-24 px-6 md:px-12 border-t border-white/5">
        <div className="max-w-4xl mx-auto">
          <FadeInSection className="text-center mb-16">
            <p className="text-purple-400 text-xs font-black uppercase tracking-[0.3em] mb-3">Simple Process</p>
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight">How it works</h2>
          </FadeInSection>

          <div className="space-y-4">
            {[
              { n: '01', title: 'HR creates a drive', desc: 'Set the job role, required skills, and generate invite links for candidates.' },
              { n: '02', title: 'Candidate joins the room', desc: 'Opens the link, passes hardware check, and the AI interviewer begins immediately.' },
              { n: '03', title: 'AI conducts the interview', desc: 'Adaptive questions across warmup, technical, stress, and behavioral phases.' },
              { n: '04', title: 'Instant report delivered', desc: 'Scores, strengths, weaknesses, and full transcript sent to HR and candidate by email.' },
            ].map((step, i) => (
              <FadeInSection key={step.n} delay={i * 0.1}>
                <div className="flex items-start space-x-6 glass-card rounded-2xl p-6">
                  <span className="text-3xl font-black text-purple-500/40 shrink-0 w-12">{step.n}</span>
                  <div>
                    <h3 className="text-white font-black text-lg mb-1">{step.title}</h3>
                    <p className="text-slate-400 text-sm leading-relaxed">{step.desc}</p>
                  </div>
                </div>
              </FadeInSection>
            ))}
          </div>
        </div>
      </section>

      {/* ── CTA ──────────────────────────────────────────────────────────── */}
      <section className="py-24 px-6 md:px-12 border-t border-white/5">
        <div className="max-w-3xl mx-auto text-center">
          <FadeInSection>
            <h2 className="text-4xl md:text-5xl font-black text-white tracking-tight mb-6">
              Ready to transform your hiring?
            </h2>
            <p className="text-slate-400 text-lg mb-10">
              Join teams using Autergo to run faster, fairer, and more insightful interviews.
            </p>
            <div className="flex flex-wrap justify-center gap-4">
              {isAuthenticated ? (
                <>
                  <Link to={getDashboardPath()}
                    className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-black px-10 py-5 rounded-2xl transition-all shadow-[0_0_50px_rgba(124,58,237,0.4)] active:scale-95 text-sm uppercase tracking-widest">
                    <span>Go to Dashboard</span>
                    <ChevronRight size={18} />
                  </Link>
                  <button onClick={handleLogout}
                    className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-10 py-5 rounded-2xl transition-all text-sm">
                    <span>Logout</span>
                    <LogOut size={18} />
                  </button>
                </>
              ) : (
                <>
                  <Link to="/register"
                    className="inline-flex items-center space-x-2 bg-purple-600 hover:bg-purple-500 text-white font-black px-10 py-5 rounded-2xl transition-all shadow-[0_0_50px_rgba(124,58,237,0.4)] active:scale-95 text-sm uppercase tracking-widest">
                    <span>Start for Free</span>
                    <ChevronRight size={18} />
                  </Link>
                  <Link to="/login"
                    className="inline-flex items-center space-x-2 bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold px-10 py-5 rounded-2xl transition-all text-sm">
                    <span>Sign In</span>
                  </Link>
                </>
              )}
            </div>
          </FadeInSection>
        </div>
      </section>

    </div>
  );
};

export default LandingPage;
