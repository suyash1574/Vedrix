import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { CheckCircle2, XCircle, Award, Calendar, Target, ChevronLeft } from 'lucide-react';
import apiClient from '../services/api';

/**
 * CertificateVerification — Public page to verify certificate authenticity.
 * Accessible without authentication via /verify/{token}
 */
const CertificateVerification = () => {
  const { token } = useParams();
  const navigate = useNavigate();
  const [verification, setVerification] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!token) return;
    const verify = async () => {
      try {
        const res = await apiClient.get(`/users/verify/${token}`);
        setVerification(res.data);
      } catch (err) {
        setError(err.response?.data?.detail || 'Invalid verification token');
      } finally {
        setLoading(false);
      }
    };
    verify();
  }, [token]);

  if (loading) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center">
        <div className="text-center space-y-4">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto" />
          <p className="text-purple-400 font-bold tracking-widest uppercase text-xs">Verifying Certificate...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-[#020617] flex items-center justify-center p-6">
        <div className="max-w-md w-full bg-white/5 border border-red-500/20 rounded-[2.5rem] p-10 text-center">
          <div className="w-20 h-20 bg-red-500/10 rounded-3xl flex items-center justify-center mx-auto mb-6">
            <XCircle size={40} className="text-red-400" />
          </div>
          <h1 className="text-2xl font-black text-white mb-3">Invalid Certificate</h1>
          <p className="text-slate-400 mb-8">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="bg-purple-600 text-white px-8 py-3 rounded-xl text-sm font-bold hover:bg-purple-500 transition-all"
          >
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[#020617] font-sans">
      {/* HEADER */}
      <header className="bg-[#0a0f1e] border-b border-white/5">
        <div className="max-w-4xl mx-auto px-6 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button onClick={() => navigate('/')} className="p-2 hover:bg-white/5 rounded-xl transition-colors text-slate-500 hover:text-white">
              <ChevronLeft size={24} />
            </button>
            <div className="h-8 w-px bg-white/5" />
            <div>
              <h1 className="text-xl font-bold text-white">Certificate Verification</h1>
              <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Autergo AI Interview Platform</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 mt-10">
        {/* Verification Status */}
        <div className="bg-white/2 border border-emerald-500/20 rounded-[2.5rem] p-10 mb-8">
          <div className="flex items-center space-x-4 mb-8">
            <div className="w-16 h-16 bg-emerald-500/10 rounded-3xl flex items-center justify-center">
              <CheckCircle2 size={32} className="text-emerald-400" />
            </div>
            <div>
              <h2 className="text-2xl font-black text-white">Certificate Verified</h2>
              <p className="text-sm text-emerald-400 font-bold">This certificate is authentic and valid</p>
            </div>
          </div>

          {/* Certificate Details */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-white/5 rounded-2xl p-6 border border-white/5">
              <div className="flex items-center space-x-3 mb-3">
                <Award size={18} className="text-purple-400" />
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Candidate</span>
              </div>
              <p className="text-xl font-bold text-white">{verification?.candidate_name}</p>
            </div>

            <div className="bg-white/5 rounded-2xl p-6 border border-white/5">
              <div className="flex items-center space-x-3 mb-3">
                <Target size={18} className="text-purple-400" />
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Role</span>
              </div>
              <p className="text-xl font-bold text-white">{verification?.job_role}</p>
            </div>

            <div className="bg-white/5 rounded-2xl p-6 border border-white/5">
              <div className="flex items-center space-x-3 mb-3">
                <Award size={18} className="text-emerald-400" />
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Score</span>
              </div>
              <p className="text-3xl font-black text-emerald-400">{verification?.overall_score}/10</p>
            </div>

            <div className="bg-white/5 rounded-2xl p-6 border border-white/5">
              <div className="flex items-center space-x-3 mb-3">
                <Calendar size={18} className="text-purple-400" />
                <span className="text-[10px] font-black text-slate-500 uppercase tracking-widest">Completed</span>
              </div>
              <p className="text-xl font-bold text-white">{verification?.date_completed || 'N/A'}</p>
            </div>
          </div>

          {/* Verification timestamp */}
          <div className="mt-8 pt-6 border-t border-white/5">
            <p className="text-xs text-slate-500 font-medium">
              Verified at: {new Date(verification?.verified_at).toLocaleString()}
            </p>
          </div>
        </div>

        {/* Call to action */}
        <div className="text-center">
          <p className="text-slate-500 text-sm mb-4">Want to take your own AI-powered interview?</p>
          <button
            onClick={() => navigate('/register')}
            className="bg-purple-600 text-white px-8 py-3 rounded-xl text-sm font-bold hover:bg-purple-500 transition-all shadow-lg shadow-purple-900/30"
          >
            Get Started with Autergo
          </button>
        </div>
      </main>
    </div>
  );
};

export default CertificateVerification;
