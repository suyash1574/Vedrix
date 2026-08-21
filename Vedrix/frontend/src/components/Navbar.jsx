import { useState, useEffect, useRef, useCallback } from 'react';
import { Cpu, LogOut, Menu, X, ChevronDown, Bell, LayoutDashboard, Settings, User } from 'lucide-react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import useAuthStore from '../store/useAuthStore';

const Navbar = () => {
  const { isAuthenticated, user, logout } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const [dropdownOpen, setDropdownOpen] = useState(null);
  const [notificationCount] = useState(3);
  const [userMenuOpen, setUserMenuOpen] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const userMenuRef = useRef(null);

  const handleLogout = () => {
    logout();
    navigate('/');
  };

  const getDashboardPath = useCallback(() => {
    if (user?.user_type === 'hr') return '/hr';
    if (user?.user_type === 'admin') return '/admin';
    return '/dashboard';
  }, [user]);

  // Close user menu on outside click
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target)) {
        setUserMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Close mobile menu on route change
  useEffect(() => {
    Promise.resolve().then(() => {
      setIsOpen(false);
      setUserMenuOpen(false);
    });
  }, [location.pathname]);

  // Keyboard shortcuts
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (!isAuthenticated) return;
      if (e.ctrlKey && e.key === 'd') {
        e.preventDefault();
        navigate(getDashboardPath());
      }
      if (e.ctrlKey && e.key === 'h') {
        e.preventDefault();
        navigate('/home');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isAuthenticated, navigate, getDashboardPath]);

  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  const userInitial = user?.first_name?.charAt(0)?.toUpperCase() || 'U';

  return (
    <nav className="fixed top-0 left-0 right-0 z-[110]" role="navigation" aria-label="Main navigation">
      <div className="navbar-shell backdrop-blur-xl">
        <div className="navbar-surface max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex items-center justify-between gap-3">
          <Link
            to="/home"
            className="flex min-w-0 items-center space-x-3 cursor-pointer group"
            aria-label="Autergo AI - Home"
          >
            <div className="w-10 h-10 shrink-0 bg-gradient-to-tr from-purple-600 via-indigo-500 to-cyan-400 rounded-xl flex items-center justify-center text-white shadow-lg shadow-purple-900/20 group-hover:scale-110 transition-all">
              <Cpu size={22} />
            </div>
            <span className="truncate text-xl sm:text-2xl font-black tracking-tighter text-white">Autergo <span className="text-purple-400 text-sm align-top ml-1">AI</span></span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden lg:flex items-center gap-1 xl:gap-3">
            <Link
              to="/home"
              aria-current={isActive('/home') ? 'page' : undefined}
              className={`nav-link-futuristic px-2 xl:px-3 font-bold text-xs xl:text-sm uppercase tracking-widest transition-colors ${isActive('/home') ? 'text-white' : 'text-slate-400 hover:text-white'}`}
            >
              Home
              {isActive('/home') && (
                <motion.div layoutId="nav-indicator" className="absolute -bottom-1 left-0 right-0 h-0.5 bg-purple-500 rounded-full" />
              )}
            </Link>
            {isAuthenticated && (
              <>
                <Link
                  to={getDashboardPath()}
                  aria-current={isActive(getDashboardPath()) ? 'page' : undefined}
                  className={`nav-link-futuristic px-2 xl:px-3 font-bold text-xs xl:text-sm uppercase tracking-widest transition-colors ${isActive(getDashboardPath()) ? 'text-white' : 'text-slate-400 hover:text-white'}`}
                >
                  Dashboard
                  {isActive(getDashboardPath()) && (
                    <motion.div layoutId="nav-indicator" className="absolute -bottom-1 left-0 right-0 h-0.5 bg-purple-500 rounded-full" />
                  )}
                </Link>

                {/* Student-specific nav */}
                {user?.user_type === 'student' && (
                  <div className="relative" onMouseLeave={() => setDropdownOpen(null)}>
                    <button
                      onMouseEnter={() => setDropdownOpen('student')}
                      className="nav-link-futuristic px-2 xl:px-3 flex items-center gap-1 text-slate-400 hover:text-white font-bold text-xs xl:text-sm uppercase tracking-widest transition-colors"
                      aria-expanded={dropdownOpen === 'student'}
                      aria-haspopup="true"
                    >
                      Growth <ChevronDown size={12} className={`transition-transform ${dropdownOpen === 'student' ? 'rotate-180' : ''}`} />
                    </button>
                    <AnimatePresence>
                      {dropdownOpen === 'student' && (
                        <motion.div
                          initial={{ opacity: 0, y: 8, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 8, scale: 0.95 }}
                          transition={{ duration: 0.15 }}
                          className="absolute top-full left-0 mt-2 bg-[#0f172a]/95 backdrop-blur-xl border border-white/10 rounded-xl p-2 min-w-[200px] shadow-2xl z-[140]"
                        >
                          <Link to="/dashboard/profile" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>Skill Profile</span>
                          </Link>
                          <Link to="/dashboard/coaching/latest" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>Coaching Plan</span>
                          </Link>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {/* HR-specific nav */}
                {(user?.user_type === 'hr' || user?.user_type === 'admin') && (
                  <div className="relative" onMouseLeave={() => setDropdownOpen(null)}>
                    <button
                      onMouseEnter={() => setDropdownOpen('hr')}
                      className="nav-link-futuristic px-2 xl:px-3 flex items-center gap-1 text-slate-400 hover:text-white font-bold text-xs xl:text-sm uppercase tracking-widest transition-colors"
                      aria-expanded={dropdownOpen === 'hr'}
                      aria-haspopup="true"
                    >
                      HR Tools <ChevronDown size={12} className={`transition-transform ${dropdownOpen === 'hr' ? 'rotate-180' : ''}`} />
                    </button>
                    <AnimatePresence>
                      {dropdownOpen === 'hr' && (
                        <motion.div
                          initial={{ opacity: 0, y: 8, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 8, scale: 0.95 }}
                          transition={{ duration: 0.15 }}
                          className="absolute top-full left-0 mt-2 bg-[#0f172a]/95 backdrop-blur-xl border border-white/10 rounded-xl p-2 min-w-[200px] shadow-2xl z-[140]"
                        >
                          <Link to="/hr/pipeline" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>Pipeline</span>
                          </Link>
                          <Link to="/hr/schedule" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>Schedule</span>
                          </Link>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}

                {/* Admin-specific nav */}
                {user?.user_type === 'admin' && (
                  <div className="relative" onMouseLeave={() => setDropdownOpen(null)}>
                    <button
                      onMouseEnter={() => setDropdownOpen('admin')}
                      className="nav-link-futuristic px-2 xl:px-3 flex items-center gap-1 text-amber-400 hover:text-amber-300 font-bold text-xs xl:text-sm uppercase tracking-widest transition-colors"
                      aria-expanded={dropdownOpen === 'admin'}
                      aria-haspopup="true"
                    >
                      Admin <ChevronDown size={12} className={`transition-transform ${dropdownOpen === 'admin' ? 'rotate-180' : ''}`} />
                    </button>
                    <AnimatePresence>
                      {dropdownOpen === 'admin' && (
                        <motion.div
                          initial={{ opacity: 0, y: 8, scale: 0.95 }}
                          animate={{ opacity: 1, y: 0, scale: 1 }}
                          exit={{ opacity: 0, y: 8, scale: 0.95 }}
                          transition={{ duration: 0.15 }}
                          className="absolute top-full left-0 mt-2 bg-[#0f172a]/95 backdrop-blur-xl border border-white/10 rounded-xl p-2 min-w-[220px] shadow-2xl z-[140]"
                        >
                          <Link to="/admin" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>Overview</span>
                            <kbd className="text-[9px] bg-white/5 border border-white/10 px-1.5 py-0.5 rounded text-slate-500">Ctrl+D</kbd>
                          </Link>
                          <Link to="/admin/audit-trail" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>Audit Trail</span>
                          </Link>
                          <Link to="/admin/qa-monitor" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>QA Monitor</span>
                          </Link>
                          <Link to="/admin/health" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>System Health</span>
                          </Link>
                          <Link to="/admin/supervisor" className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                            <span>AI Supervisor</span>
                          </Link>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="hidden lg:flex items-center space-x-3">
            {!isAuthenticated ? (
              <>
                <Link to="/login" className="text-white font-bold px-6 py-2.5 rounded-xl hover:bg-white/5 transition-all">Sign In</Link>
                <Link to="/register" className="bg-purple-600 text-white font-bold px-8 py-2.5 rounded-xl hover:bg-purple-500 shadow-xl shadow-purple-900/30 transition-all active:scale-95">Register</Link>
              </>
            ) : (
              <div className="flex items-center space-x-3">
                {/* Notification Bell */}
                <button
                  className="relative w-10 h-10 bg-white/5 border border-white/10 rounded-xl flex items-center justify-center text-slate-400 hover:text-white hover:bg-white/10 transition-all"
                  aria-label={`Notifications: ${notificationCount} unread`}
                >
                  <Bell size={18} />
                  {notificationCount > 0 && (
                    <span className="absolute -top-1 -right-1 w-5 h-5 bg-purple-600 rounded-full flex items-center justify-center text-[10px] font-black text-white pulse-glow-purple">
                      {notificationCount}
                    </span>
                  )}
                </button>

                {/* User Avatar & Menu */}
                <div className="relative" ref={userMenuRef}>
                  <button
                    onClick={() => setUserMenuOpen(!userMenuOpen)}
                    className="flex items-center space-x-3 bg-white/5 border border-white/10 rounded-xl px-3 py-2 hover:bg-white/10 transition-all"
                    aria-expanded={userMenuOpen}
                    aria-haspopup="true"
                    aria-label="User menu"
                  >
                    <div className="w-8 h-8 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-lg flex items-center justify-center text-white font-black text-sm">
                      {userInitial}
                    </div>
                    <div className="flex flex-col text-left">
                      <span className="text-white font-bold text-sm leading-tight">{user?.first_name}</span>
                      <span className="text-slate-500 text-[10px] font-black uppercase tracking-widest">{user?.user_type}</span>
                    </div>
                    <ChevronDown size={14} className={`text-slate-500 transition-transform ${userMenuOpen ? 'rotate-180' : ''}`} />
                  </button>

                  <AnimatePresence>
                    {userMenuOpen && (
                      <motion.div
                        initial={{ opacity: 0, y: 8, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 8, scale: 0.95 }}
                        transition={{ duration: 0.15 }}
                        className="absolute top-full right-0 mt-2 bg-[#0f172a]/95 backdrop-blur-xl border border-white/10 rounded-xl p-2 min-w-[220px] shadow-2xl z-[140]"
                      >
                        <div className="px-4 py-3 border-b border-white/5 mb-2">
                          <p className="text-white font-bold text-sm">{user?.first_name} {user?.last_name}</p>
                          <p className="text-slate-500 text-xs">{user?.email}</p>
                        </div>
                        <Link to={getDashboardPath()} onClick={() => setUserMenuOpen(false)} className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                          <span className="flex items-center gap-2"><LayoutDashboard size={14} /> Dashboard</span>
                          <kbd className="text-[9px] bg-white/5 border border-white/10 px-1.5 py-0.5 rounded text-slate-500">Ctrl+D</kbd>
                        </Link>
                        <Link to="/profile" onClick={() => setUserMenuOpen(false)} className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                          <span className="flex items-center gap-2"><User size={14} /> My Profile</span>
                        </Link>
                        <Link to="/settings" onClick={() => setUserMenuOpen(false)} className="flex items-center justify-between px-4 py-2.5 text-slate-300 hover:text-white hover:bg-white/5 rounded-lg text-sm font-bold transition-all">
                          <span className="flex items-center gap-2"><Settings size={14} /> Settings</span>
                        </Link>
                        <button
                          onClick={() => { setUserMenuOpen(false); handleLogout(); }}
                          className="w-full flex items-center justify-between px-4 py-2.5 text-red-400 hover:text-red-300 hover:bg-red-500/5 rounded-lg text-sm font-bold transition-all"
                        >
                          <span className="flex items-center gap-2"><LogOut size={14} /> Logout</span>
                        </button>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            )}
          </div>

          {/* Mobile toggle */}
          <button
            className="lg:hidden text-white w-10 h-10 flex items-center justify-center rounded-xl hover:bg-white/5 transition-all"
            onClick={() => setIsOpen(!isOpen)}
            aria-label={isOpen ? 'Close menu' : 'Open menu'}
            aria-expanded={isOpen}
          >
            {isOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {/* Animated gradient border at bottom */}
      <div className="nav-border-animated" />

      {/* Mobile Menu - Slide from right */}
      <AnimatePresence>
        {isOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 bg-black/60 backdrop-blur-sm lg:hidden z-[120]"
              onClick={() => setIsOpen(false)}
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="fixed top-0 right-0 bottom-0 w-[min(86vw,340px)] bg-[#0a0f1e]/98 backdrop-blur-xl border-l border-white/10 lg:hidden z-[130] overflow-y-auto shadow-2xl shadow-black/60"
            >
              <div className="p-6 space-y-2">
                <div className="flex items-center justify-between mb-8">
                  <span className="text-lg font-black text-white">Menu</span>
                  <button onClick={() => setIsOpen(false)} className="text-slate-400 hover:text-white p-2 rounded-xl hover:bg-white/5 transition-all" aria-label="Close menu">
                    <X size={20} />
                  </button>
                </div>

                {isAuthenticated && (
                  <Link
                    to="/profile"
                    onClick={() => setIsOpen(false)}
                    className="flex items-center space-x-3 bg-white/5 border border-white/10 rounded-2xl p-4 mb-6 hover:bg-white/10 transition-all"
                  >
                    <div className="w-10 h-10 bg-gradient-to-tr from-purple-600 to-indigo-400 rounded-xl flex items-center justify-center text-white font-black">
                      {userInitial}
                    </div>
                    <div className="min-w-0">
                      <p className="text-white font-bold text-sm truncate">{user?.first_name} {user?.last_name}</p>
                      <p className="text-slate-500 text-xs capitalize">{user?.user_type} · View profile</p>
                    </div>
                  </Link>
                )}

                <Link onClick={() => setIsOpen(false)} to="/home"
                  className="block text-slate-300 hover:text-white font-bold text-sm py-3 px-4 rounded-xl hover:bg-white/5 transition-all">Home</Link>
                {isAuthenticated && (
                  <>
                    <Link onClick={() => setIsOpen(false)} to={getDashboardPath()}
                      className="block text-slate-300 hover:text-white font-bold text-sm py-3 px-4 rounded-xl hover:bg-white/5 transition-all">Dashboard</Link>
                    <Link onClick={() => setIsOpen(false)} to="/profile"
                      className="block text-slate-300 hover:text-white font-bold text-sm py-3 px-4 rounded-xl hover:bg-white/5 transition-all">My Profile</Link>
                    {user?.user_type === 'student' && (
                      <>
                        <Link onClick={() => setIsOpen(false)} to="/dashboard/profile"
                          className="block text-slate-400 hover:text-white font-bold text-sm py-3 px-4 pl-8 rounded-xl hover:bg-white/5 transition-all">Skill Profile</Link>
                        <Link onClick={() => setIsOpen(false)} to="/dashboard/coaching/latest"
                          className="block text-slate-400 hover:text-white font-bold text-sm py-3 px-4 pl-8 rounded-xl hover:bg-white/5 transition-all">Coaching</Link>
                      </>
                    )}
                    {(user?.user_type === 'hr' || user?.user_type === 'admin') && (
                      <>
                        <Link onClick={() => setIsOpen(false)} to="/hr/pipeline"
                          className="block text-slate-400 hover:text-white font-bold text-sm py-3 px-4 pl-8 rounded-xl hover:bg-white/5 transition-all">Pipeline</Link>
                        <Link onClick={() => setIsOpen(false)} to="/hr/schedule"
                          className="block text-slate-400 hover:text-white font-bold text-sm py-3 px-4 pl-8 rounded-xl hover:bg-white/5 transition-all">Schedule</Link>
                      </>
                    )}
                    {user?.user_type === 'admin' && (
                      <>
                        <div className="border-t border-white/5 my-3" />
                        <Link onClick={() => setIsOpen(false)} to="/admin/audit-trail"
                          className="block text-amber-400 hover:text-amber-300 font-bold text-sm py-3 px-4 rounded-xl hover:bg-amber-500/5 transition-all">Audit Trail</Link>
                        <Link onClick={() => setIsOpen(false)} to="/admin/qa-monitor"
                          className="block text-amber-400 hover:text-amber-300 font-bold text-sm py-3 px-4 rounded-xl hover:bg-amber-500/5 transition-all">QA Monitor</Link>
                        <Link onClick={() => setIsOpen(false)} to="/admin/health"
                          className="block text-amber-400 hover:text-amber-300 font-bold text-sm py-3 px-4 rounded-xl hover:bg-amber-500/5 transition-all">System Health</Link>
                      </>
                    )}
                  </>
                )}

                <div className="border-t border-white/5 my-3" />

                {!isAuthenticated ? (
                  <>
                    <Link onClick={() => setIsOpen(false)} to="/login" className="block text-white font-bold px-4 py-3 rounded-xl hover:bg-white/5 transition-all">Sign In</Link>
                    <Link onClick={() => setIsOpen(false)} to="/register" className="block bg-purple-600 text-white font-bold px-4 py-3 rounded-xl hover:bg-purple-500 transition-all text-center">Register</Link>
                  </>
                ) : (
                  <button onClick={() => { setIsOpen(false); handleLogout(); }}
                    className="w-full text-left text-red-400 hover:text-red-300 font-bold px-4 py-3 rounded-xl hover:bg-red-500/10 transition-all flex items-center gap-2">
                    <LogOut size={16} /> Logout
                  </button>
                )}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </nav>
  );
};

export default Navbar;
