import { Link } from 'react-router-dom';
import { Cpu, Globe, MessageCircle, Briefcase, Mail, Sparkles } from 'lucide-react';
import { useState } from 'react';

const Footer = () => {
  const [email, setEmail] = useState('');
  const [subscribed, setSubscribed] = useState(false);

  const handleSubscribe = (e) => {
    e.preventDefault();
    if (email.trim()) {
      setSubscribed(true);
      setEmail('');
      setTimeout(() => setSubscribed(false), 3000);
    }
  };

  const footerLinks = {
    Product: [
      { label: 'AI Interviews', to: '/home' },
      { label: 'For Recruiters', to: '/home' },
      { label: 'For Candidates', to: '/home' },
      { label: 'Pricing', to: '/home' },
    ],
    Company: [
      { label: 'About Us', to: '/home' },
      { label: 'Careers', to: '/home' },
      { label: 'Blog', to: '/home' },
      { label: 'Contact', to: '/home' },
    ],
    Resources: [
      { label: 'Documentation', to: '/home' },
      { label: 'API Reference', to: '/home' },
      { label: 'System Status', to: '/home' },
      { label: 'Changelog', to: '/home' },
    ],
    Legal: [
      { label: 'Privacy Policy', to: '/privacy' },
      { label: 'Terms of Service', to: '/terms' },
      { label: 'Data Processing', to: '/dpa' },
      { label: 'Accessibility', to: '/accessibility' },
    ],
  };

  return (
    <footer className="relative bg-[#0a0f1e] border-t border-white/5">
      {/* Animated gradient divider */}
      <div className="gradient-divider" />

      <div className="max-w-7xl mx-auto px-8 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-12">
          {/* Brand Column */}
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-900/20">
                <Cpu size={22} />
              </div>
              <span className="text-2xl font-black tracking-tighter text-white">Autergo <span className="text-purple-400 text-sm align-top ml-1">AI</span></span>
            </div>
            <p className="text-slate-400 text-sm leading-relaxed max-w-xs">
              AI-powered interview platform that conducts adaptive interviews, evaluates candidates in real-time, and delivers structured reports.
            </p>

            {/* Newsletter */}
            <div className="space-y-3">
              <p className="text-xs font-black uppercase text-slate-500 tracking-widest">Stay Updated</p>
              {subscribed ? (
                <p className="text-emerald-400 text-sm font-bold">Thanks for subscribing!</p>
              ) : (
                <form onSubmit={handleSubscribe} className="flex gap-2">
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="your@email.com"
                    className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-2.5 text-sm text-white placeholder-slate-600 focus:ring-2 focus:ring-purple-500 outline-none transition-all"
                    aria-label="Email for newsletter"
                  />
                  <button
                    type="submit"
                    className="bg-purple-600 hover:bg-purple-500 text-white px-4 py-2.5 rounded-xl font-bold text-sm transition-all active:scale-95"
                    aria-label="Subscribe to newsletter"
                  >
                    <Mail size={16} />
                  </button>
                </form>
              )}
            </div>

            {/* Social Icons */}
            <div className="flex items-center space-x-3">
              {[
                { icon: MessageCircle, label: 'Twitter', href: '#' },
                { icon: Globe, label: 'GitHub', href: '#' },
                { icon: Briefcase, label: 'LinkedIn', href: '#' },
              ].map(({ icon: Icon, label, href }) => (
                <a
                  key={label}
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="w-9 h-9 bg-white/5 border border-white/10 rounded-lg flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 hover:border-purple-500/30 transition-all"
                  aria-label={label}
                >
                  <Icon size={16} />
                </a>
              ))}
            </div>
          </div>

          {/* Link Columns */}
          {Object.entries(footerLinks).map(([title, links]) => (
            <div key={title} className="space-y-4">
              <h3 className="text-xs font-black uppercase text-slate-400 tracking-widest">{title}</h3>
              <ul className="space-y-2.5">
                {links.map(({ label, to }) => (
                  <li key={label}>
                    <Link to={to} className="text-slate-500 hover:text-white text-sm transition-colors">
                      {label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        {/* Bottom Bar */}
        <div className="mt-16 pt-8 border-t border-white/5 flex flex-col md:flex-row items-center justify-between gap-4">
          <p className="text-slate-600 text-xs font-bold">
            © {new Date().getFullYear()} Autergo. All rights reserved.
          </p>

          {/* Built with AI Badge */}
          <div className="flex items-center space-x-2 bg-purple-500/10 border border-purple-500/20 px-3 py-1.5 rounded-full">
            <Sparkles size={12} className="text-purple-400" />
            <span className="text-[10px] font-black uppercase tracking-widest text-purple-300">Built with AI</span>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
