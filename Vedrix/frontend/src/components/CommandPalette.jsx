import { useState, useEffect, useMemo, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Search,
  Home,
  LayoutDashboard,
  Users,
  Briefcase,
  Settings,
  LogOut,
  FileText,
  Activity,
  Shield,
  Sparkles,
  Brain,
  BarChart3,
  Clock,
  ArrowRight,
  Command as CmdIcon,
  Calendar,
  Eye,
  Cpu,
  TrendingUp,
  ClipboardList,
  Workflow,
} from 'lucide-react';
import useAuthStore from '../store/useAuthStore';
import useToastStore from '../store/useToastStore';

const RECENTS_KEY = 'vedrix:cmdk:recents';
const MAX_RECENTS = 5;

/**
 * Linear/Notion-style command palette.
 * Triggered by Cmd+K (mac) / Ctrl+K (win).
 */
const CommandPalette = () => {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [activeIndex, setActiveIndex] = useState(0);
  const [recents, setRecents] = useState(() => {
    try {
      const stored = localStorage.getItem(RECENTS_KEY);
      return stored ? JSON.parse(stored) : [];
    } catch {
      return [];
    }
  });
  const inputRef = useRef(null);
  const listRef = useRef(null);
  const navigate = useNavigate();
  const { user, isAuthenticated, logout } = useAuthStore();
  const addToast = useToastStore((s) => s.addToast);

  const persistRecent = useCallback((id) => {
    setRecents((prev) => {
      const next = [id, ...prev.filter((x) => x !== id)].slice(0, MAX_RECENTS);
      try {
        localStorage.setItem(RECENTS_KEY, JSON.stringify(next));
      } catch {
        // ignore
      }
      return next;
    });
  }, []);

  const dashboardPath = useMemo(() => {
    if (user?.user_type === 'admin') return '/admin';
    if (user?.user_type === 'hr') return '/hr';
    return '/dashboard';
  }, [user]);

  // Build commands list — filtered by auth/role
  const allCommands = useMemo(() => {
    const items = [];

    // Navigation
    items.push({
      id: 'nav-home',
      label: 'Go to Home',
      category: 'Navigation',
      icon: Home,
      shortcut: 'G H',
      action: () => navigate('/home'),
      keywords: 'home landing',
    });

    if (isAuthenticated) {
      items.push({
        id: 'nav-dashboard',
        label: 'Open Dashboard',
        category: 'Navigation',
        icon: LayoutDashboard,
        shortcut: 'Ctrl D',
        action: () => navigate(dashboardPath),
        keywords: 'dashboard overview',
      });
      items.push({
        id: 'nav-settings',
        label: 'Settings',
        category: 'Navigation',
        icon: Settings,
        action: () => navigate('/settings'),
        keywords: 'preferences profile account',
      });

      if (user?.user_type === 'student') {
        items.push({
          id: 'nav-profile',
          label: 'My Skill Profile',
          category: 'Navigation',
          icon: TrendingUp,
          action: () => navigate('/dashboard/profile'),
          keywords: 'skills strengths growth',
        });
        items.push({
          id: 'nav-coaching',
          label: 'Coaching Plan',
          category: 'Navigation',
          icon: Brain,
          action: () => navigate('/dashboard/coaching/latest'),
          keywords: 'plan growth practice improve',
        });
      }

      if (user?.user_type === 'hr' || user?.user_type === 'admin') {
        items.push({
          id: 'nav-pipeline',
          label: 'Candidate Pipeline',
          category: 'Navigation',
          icon: Workflow,
          action: () => navigate('/hr/pipeline'),
          keywords: 'pipeline kanban candidates',
        });
        items.push({
          id: 'nav-schedule',
          label: 'Schedule',
          category: 'Navigation',
          icon: Calendar,
          action: () => navigate('/hr/schedule'),
          keywords: 'calendar interview booking',
        });
      }

      if (user?.user_type === 'admin') {
        items.push({
          id: 'nav-audit',
          label: 'Audit Trail',
          category: 'Navigation',
          icon: ClipboardList,
          action: () => navigate('/admin/audit-trail'),
          keywords: 'audit logs trace',
        });
        items.push({
          id: 'nav-qa',
          label: 'QA Monitor',
          category: 'Navigation',
          icon: Eye,
          action: () => navigate('/admin/qa-monitor'),
          keywords: 'quality monitor review',
        });
        items.push({
          id: 'nav-health',
          label: 'System Health',
          category: 'Navigation',
          icon: Activity,
          action: () => navigate('/admin/health'),
          keywords: 'health metrics uptime',
        });
        items.push({
          id: 'nav-supervisor',
          label: 'AI Supervisor',
          category: 'Navigation',
          icon: Shield,
          action: () => navigate('/admin/supervisor'),
          keywords: 'agents control supervisor',
        });
        items.push({
          id: 'nav-team-analytics',
          label: 'Team Analytics',
          category: 'Navigation',
          icon: BarChart3,
          action: () => navigate('/analytics/team'),
          keywords: 'team metrics analytics dashboard',
        });
      }
    }

    // Quick Actions
    if (isAuthenticated) {
      if (user?.user_type === 'student') {
        items.push({
          id: 'qa-start-interview',
          label: 'Start an Interview',
          category: 'Quick Actions',
          icon: Sparkles,
          action: () => navigate('/interview'),
          keywords: 'begin interview practice mock',
        });
      }

      if (user?.user_type === 'hr' || user?.user_type === 'admin') {
        items.push({
          id: 'qa-view-candidates',
          label: 'View Candidates',
          category: 'Quick Actions',
          icon: Users,
          action: () => navigate('/hr/pipeline'),
          keywords: 'candidates pipeline applicants',
        });
        items.push({
          id: 'qa-create-drive',
          label: 'New Hiring Drive',
          category: 'Quick Actions',
          icon: Briefcase,
          action: () => {
            navigate('/hr');
            addToast({
              type: 'info',
              title: 'Open the dashboard',
              message: 'Use the "+ New Drive" button to create one.',
            });
          },
          keywords: 'drive job opening create',
        });
      }

      items.push({
        id: 'qa-logout',
        label: 'Sign Out',
        category: 'Quick Actions',
        icon: LogOut,
        action: async () => {
          await logout();
          navigate('/');
          addToast({ type: 'success', title: 'Signed out', message: 'See you soon.' });
        },
        keywords: 'logout signout exit',
      });
    } else {
      items.push({
        id: 'qa-login',
        label: 'Sign In',
        category: 'Quick Actions',
        icon: ArrowRight,
        action: () => navigate('/login'),
        keywords: 'sign in login',
      });
      items.push({
        id: 'qa-register',
        label: 'Create Account',
        category: 'Quick Actions',
        icon: Sparkles,
        action: () => navigate('/register'),
        keywords: 'register signup join',
      });
    }

    // AI Tools
    items.push({
      id: 'ai-assistant',
      label: 'Ask Vedra (AI Assistant)',
      category: 'AI Tools',
      icon: Sparkles,
      action: () => {
        window.dispatchEvent(new CustomEvent('vedrix:open-assistant'));
      },
      keywords: 'ai chat assistant help vedra',
    });
    if (isAuthenticated && user?.user_type === 'student') {
      items.push({
        id: 'ai-skill-coach',
        label: 'Generate Coaching Plan',
        category: 'AI Tools',
        icon: Brain,
        action: () => navigate('/dashboard/coaching/latest'),
        keywords: 'coach growth recommendations ai',
      });
    }
    if (isAuthenticated) {
      items.push({
        id: 'ai-summarize',
        label: 'Summarize Last Session',
        category: 'AI Tools',
        icon: FileText,
        action: () => {
          addToast({
            type: 'info',
            title: 'AI summary coming up',
            message: 'Open your dashboard and pick a session to summarize.',
          });
          navigate(dashboardPath);
        },
        keywords: 'summary session ai',
      });
    }

    // Settings
    items.push({
      id: 'set-toggle-theme',
      label: 'Toggle Theme (Coming Soon)',
      category: 'Settings',
      icon: Cpu,
      action: () =>
        addToast({
          type: 'info',
          title: 'Theme switcher',
          message: 'Light mode is on the roadmap.',
        }),
      keywords: 'theme dark light mode',
    });

    return items;
  }, [isAuthenticated, user, navigate, dashboardPath, logout, addToast]);

  // Filter by query
  const filtered = useMemo(() => {
    if (!query.trim()) return allCommands;
    const q = query.toLowerCase().trim();
    return allCommands.filter((c) => {
      const haystack = `${c.label} ${c.category} ${c.keywords || ''}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [allCommands, query]);

  // Group: recents first (only when no query), then by category
  const grouped = useMemo(() => {
    if (query.trim()) {
      const groups = {};
      for (const cmd of filtered) {
        if (!groups[cmd.category]) groups[cmd.category] = [];
        groups[cmd.category].push(cmd);
      }
      return groups;
    }

    const recentSet = new Set(recents);
    const recentItems = recents
      .map((id) => allCommands.find((c) => c.id === id))
      .filter(Boolean);
    const others = allCommands.filter((c) => !recentSet.has(c.id));

    const groups = {};
    if (recentItems.length) groups['Recent'] = recentItems;
    for (const cmd of others) {
      if (!groups[cmd.category]) groups[cmd.category] = [];
      groups[cmd.category].push(cmd);
    }
    return groups;
  }, [filtered, query, recents, allCommands]);

  // Flat order for keyboard nav
  const flatItems = useMemo(() => {
    const out = [];
    for (const [, items] of Object.entries(grouped)) {
      out.push(...items);
    }
    return out;
  }, [grouped]);

  // Reset active index when filter changes
  useEffect(() => {
    Promise.resolve().then(() => {
      setActiveIndex(0);
    });
  }, [query, open]);

  // Open/close hotkey
  useEffect(() => {
    const onKeyDown = (e) => {
      const isToggle = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k';
      if (isToggle) {
        e.preventDefault();
        setOpen((o) => !o);
      }
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, []);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      // Defer to next tick so animation kicks in cleanly
      setTimeout(() => inputRef.current?.focus(), 30);
    } else {
      Promise.resolve().then(() => {
        setQuery('');
      });
    }
  }, [open]);

  // Scroll active item into view
  useEffect(() => {
    if (!open) return;
    const node = listRef.current?.querySelector(`[data-cmd-index="${activeIndex}"]`);
    if (node) node.scrollIntoView({ block: 'nearest' });
  }, [activeIndex, open]);

  const runCommand = useCallback(
    (cmd) => {
      if (!cmd) return;
      persistRecent(cmd.id);
      setOpen(false);
      // Slight delay so the close animation feels right before navigation
      setTimeout(() => cmd.action(), 60);
    },
    [persistRecent]
  );

  const handleKeyDown = (e) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      setOpen(false);
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setActiveIndex((i) => Math.min(i + 1, flatItems.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActiveIndex((i) => Math.max(i - 1, 0));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      runCommand(flatItems[activeIndex]);
    }
  };

  const highlightMatch = (text) => {
    if (!query.trim()) return text;
    const q = query.trim();
    const idx = text.toLowerCase().indexOf(q.toLowerCase());
    if (idx === -1) return text;
    return (
      <>
        {text.slice(0, idx)}
        <span className="text-purple-300 font-bold">{text.slice(idx, idx + q.length)}</span>
        {text.slice(idx + q.length)}
      </>
    );
  };

  // Build the running item index across groups for keyboard nav alignment
  let runningIndex = -1;

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          className="fixed inset-0 z-[10000] flex items-start justify-center pt-[12vh] px-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          transition={{ duration: 0.18 }}
          aria-modal="true"
          role="dialog"
          aria-label="Command palette"
        >
          {/* Backdrop */}
          <div
            className="absolute inset-0 bg-[#020617]/70 backdrop-blur-md"
            onClick={() => setOpen(false)}
          />

          {/* Modal */}
          <motion.div
            className="relative w-full max-w-2xl bg-[#0a0f1e]/95 backdrop-blur-2xl border border-white/10 rounded-2xl shadow-2xl shadow-black/60 overflow-hidden"
            initial={{ opacity: 0, scale: 0.96, y: -8 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: -8 }}
            transition={{ type: 'spring', damping: 26, stiffness: 320 }}
          >
            {/* Top: search input */}
            <div className="flex items-center gap-3 px-5 py-4 border-b border-white/5">
              <Search size={18} className="text-slate-500 shrink-0" />
              <input
                ref={inputRef}
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Search commands, pages, or ask Vedra..."
                className="flex-1 bg-transparent border-none outline-none text-white placeholder-slate-600 text-sm font-medium"
                aria-label="Search commands"
                autoComplete="off"
              />
              <span className="kbd-key">esc</span>
            </div>

            {/* Results */}
            <div ref={listRef} className="max-h-[60vh] overflow-y-auto py-2">
              {flatItems.length === 0 ? (
                <div className="px-6 py-12 text-center">
                  <div className="text-slate-500 text-sm">
                    No results for{' '}
                    <span className="text-white font-bold">"{query}"</span>
                  </div>
                  <p className="text-slate-600 text-xs mt-2">
                    Try a different keyword or check your spelling.
                  </p>
                </div>
              ) : (
                Object.entries(grouped).map(([category, items]) => (
                  <div key={category} className="px-2 pb-1">
                    <div className="px-3 pt-2 pb-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-500 flex items-center gap-2">
                      {category === 'Recent' && <Clock size={10} />}
                      {category}
                    </div>
                    {items.map((cmd) => {
                      runningIndex += 1;
                      const isActive = runningIndex === activeIndex;
                      const Icon = cmd.icon;
                      return (
                        <button
                          key={cmd.id}
                          type="button"
                          data-cmd-index={runningIndex}
                          onClick={() => runCommand(cmd)}
                          onMouseEnter={() => setActiveIndex(runningIndex)}
                          className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all ${
                            isActive
                              ? 'bg-purple-500/15 text-white'
                              : 'text-slate-300 hover:bg-white/5'
                          }`}
                        >
                          <span
                            className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all ${
                              isActive
                                ? 'bg-purple-500/25 text-purple-300'
                                : 'bg-white/5 text-slate-400'
                            }`}
                          >
                            <Icon size={15} />
                          </span>
                          <span className="flex-1 text-sm font-bold truncate">
                            {highlightMatch(cmd.label)}
                          </span>
                          <span className="text-[10px] font-bold uppercase tracking-widest text-slate-500 hidden sm:inline">
                            {cmd.category}
                          </span>
                          {cmd.shortcut && (
                            <span className="hidden sm:flex items-center gap-1">
                              {cmd.shortcut.split(' ').map((k) => (
                                <span key={k} className="kbd-key">
                                  {k}
                                </span>
                              ))}
                            </span>
                          )}
                          {isActive && <ArrowRight size={12} className="text-purple-400" />}
                        </button>
                      );
                    })}
                  </div>
                ))
              )}
            </div>

            {/* Footer hints */}
            <div className="flex items-center justify-between px-5 py-3 border-t border-white/5 bg-white/[0.015]">
              <div className="flex items-center gap-3 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                <span className="flex items-center gap-1">
                  <span className="kbd-key">↑</span>
                  <span className="kbd-key">↓</span>
                  Navigate
                </span>
                <span className="flex items-center gap-1">
                  <span className="kbd-key">↵</span>
                  Select
                </span>
                <span className="flex items-center gap-1">
                  <span className="kbd-key">esc</span>
                  Close
                </span>
              </div>
              <div className="flex items-center gap-1.5 text-[10px] font-bold uppercase tracking-widest text-slate-500">
                <CmdIcon size={10} />
                Autergo Command
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </AnimatePresence>
  );
};

export default CommandPalette;
