import { Zap, Cpu, Activity } from 'lucide-react'

const LandingSections = () => {
  const features = [
    { title: 'Autonomous Interview Orchestrator', desc: 'Orchestrates end-to-end interviews with adaptive AI.', Icon: Zap },
    { title: 'Adaptive Questioning', desc: 'Dynamic follow-ups based on responses for depth.', Icon: Cpu },
    { title: 'Voice & Code Evaluation', desc: 'Voice transcripts and live code evaluation.', Icon: Activity },
  ]

  return (
    <>
      <section id="about" className="py-20 bg-gradient-to-br from-white/5 to-white/10">
        <div className="max-w-7xl mx-auto px-8 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
          <div>
            <h2 className="text-3xl font-extrabold text-white mb-4">About Autergo</h2>
            <p className="text-slate-200 text-lg leading-relaxed">
              Autergo is an autonomous AI-powered interview orchestration platform designed to accelerate hiring with agentic intelligence.
            </p>
            <p className="text-slate-200 text-lg leading-relaxed mt-4">
              Built for modern teams, Autergo blends a robust backend, adaptive interviewing, live evaluation, and instant feedback to shorten the hiring cycle.
            </p>
          </div>
          <div className="space-y-4">
            <div className="p-5 rounded-xl border border-white/10 bg-white/5">
              <div className="flex items-center space-x-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-400" />
                <span className="font-bold text-white">Mine</span>
              </div>
              <div className="text-white font-semibold">Name: Your Name</div>
              <div className="text-slate-300 text-sm">Role: Founder & Lead Engineer</div>
              <div className="flex space-x-3 mt-2">
                <a href="#" className="text-purple-400 font-semibold" target="_blank" rel="noreferrer">GitHub</a>
                <a href="#" className="text-purple-400 font-semibold" target="_blank" rel="noreferrer">LinkedIn</a>
              </div>
            </div>
            <div className="p-5 rounded-xl border border-white/10 bg-white/5">
              <div className="flex items-center space-x-2 mb-2">
                <div className="w-6 h-6 rounded-full bg-gradient-to-tr from-purple-600 to-indigo-400" />
                <span className="font-bold text-white">Our Mission</span>
              </div>
              <p className="text-slate-300 text-sm">To empower teams with autonomous, AI-driven hiring that’s fast, fair, and insightful.</p>
            </div>
          </div>
        </div>
      </section>

      <section id="features" className="py-20 bg-gradient-to-br from-white/5 to-white/10">
        <div className="max-w-7xl mx-auto px-8">
          <h2 className="text-3xl font-extrabold text-white mb-6">Key Features</h2>
          <p className="text-slate-300 mb-6">A quick tour of Autergo capabilities</p>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((f, i) => (
              <div key={i} className="p-5 rounded-xl border border-white/10 bg-white/5 hover:bg-white/10 transition">
                <div className="mb-2 text-purple-300">{f.Icon ? <f.Icon size={28} /> : null}</div>
                <div className="text-white font-semibold">{f.title}</div>
                <div className="text-slate-300 text-sm mt-1">{f.desc}</div>
              </div>
            ))}
          </div>
        </div>
      </section>
    </>
  )
}

export default LandingSections
