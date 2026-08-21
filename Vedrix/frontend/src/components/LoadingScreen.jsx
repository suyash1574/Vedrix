import { motion } from 'framer-motion';
import { Cpu } from 'lucide-react';

/**
 * Premium full-screen loading indicator.
 * Use as a Suspense fallback or while bootstrapping auth.
 */
const LoadingScreen = ({ message = 'Loading your workspace...' }) => {
  return (
    <div
      role="status"
      aria-live="polite"
      className="fixed inset-0 z-[9998] flex items-center justify-center bg-[#020617]/90 backdrop-blur-xl"
    >
      {/* Soft mesh background */}
      <div className="absolute inset-0 gradient-mesh opacity-60 pointer-events-none" />

      <div className="relative flex flex-col items-center">
        {/* Logo with pulse + ring */}
        <div className="relative w-24 h-24 flex items-center justify-center">
          <motion.div
            className="absolute inset-0 rounded-3xl border border-purple-500/30"
            animate={{ scale: [1, 1.4, 1.4], opacity: [0.6, 0, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut' }}
          />
          <motion.div
            className="absolute inset-0 rounded-3xl border border-indigo-500/30"
            animate={{ scale: [1, 1.4, 1.4], opacity: [0.6, 0, 0] }}
            transition={{ duration: 2, repeat: Infinity, ease: 'easeOut', delay: 0.6 }}
          />
          <motion.div
            initial={{ scale: 0.85, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            className="relative w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-400 shadow-2xl shadow-purple-900/40 flex items-center justify-center"
          >
            <Cpu className="text-white" size={28} />
          </motion.div>
        </div>

        {/* Autergo wordmark */}
        <div className="mt-6 text-2xl font-black tracking-tighter text-white">
          Autergo <span className="text-purple-400 text-xs align-top ml-0.5">AI</span>
        </div>

        {/* Animated dots */}
        <div className="mt-5 flex items-center gap-1.5" aria-hidden="true">
          {[0, 1, 2].map((i) => (
            <motion.span
              key={i}
              className="w-2 h-2 rounded-full bg-purple-500"
              animate={{ y: [0, -6, 0], opacity: [0.4, 1, 0.4] }}
              transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
            />
          ))}
        </div>

        <p className="mt-4 text-xs font-bold uppercase tracking-[0.2em] text-slate-500">
          {message}
        </p>
      </div>
    </div>
  );
};

export default LoadingScreen;
