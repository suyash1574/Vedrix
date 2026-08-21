import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../services/api';

const initialForm = { first_name: '', last_name: '', phone: '', resume_text: '', portfolio_url: '', availability: '' };

export default function CandidateApplicationForm() {
  const { token } = useParams();
  const [form, setForm] = useState(initialForm);
  const [meta, setMeta] = useState(null);
  const [consent, setConsent] = useState(false);
  const [status, setStatus] = useState({ loading: true, submitting: false, error: '', success: null });

  useEffect(() => {
    let mounted = true;
    apiClient.get(`/hiring/apply/${token}`)
      .then((response) => { if (mounted) { setMeta(response.data); setForm((current) => ({ ...current, candidate_email: response.data.candidate_email || '' })); } })
      .catch((error) => { if (mounted) setStatus({ loading: false, submitting: false, error: error.response?.data?.detail || 'This application link is no longer available.', success: null }); })
      .finally(() => { if (mounted) setStatus((current) => ({ ...current, loading: false })); });
    return () => { mounted = false; };
  }, [token]);

  const submit = async (event) => {
    event.preventDefault();
    if (!consent) { setStatus((current) => ({ ...current, error: 'Consent is required before submitting.' })); return; }
    setStatus({ loading: false, submitting: true, error: '', success: null });
    try {
      const response = await apiClient.post(`/hiring/apply/${token}`, {
        candidate_email: form.candidate_email,
        candidate_first_name: form.first_name,
        candidate_last_name: form.last_name,
        source: 'application_form',
        form_data: form,
        resume_text: form.resume_text,
        consent_granted: consent,
      });
      setStatus({ loading: false, submitting: false, error: '', success: response.data });
    } catch (error) {
      setStatus({ loading: false, submitting: false, error: error.response?.data?.detail || 'Could not submit your application.', success: null });
    }
  };

  if (status.loading) return <div className="min-h-screen bg-slate-950 p-8 text-slate-200">Loading application form…</div>;
  if (status.error && !meta) return <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6"><div className="max-w-md rounded-2xl border border-rose-900 bg-rose-950/40 p-8 text-center text-rose-200">{status.error}</div></div>;
  if (status.success) return <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6"><div className="max-w-lg rounded-2xl border border-emerald-900 bg-emerald-950/30 p-8 text-center"><div className="text-xs font-semibold uppercase tracking-[0.24em] text-emerald-400">Application received</div><h1 className="mt-3 text-3xl font-semibold text-white">Thank you, {form.first_name || 'candidate'}.</h1><p className="mt-3 text-slate-300">Your application has been submitted for recruiter review. Your JD match score is {Math.round(status.success.match_score || 0)}%.</p><p className="mt-5 text-sm text-slate-500">The recruiter will contact you about the next step.</p></div></div>;

  const fields = meta?.form_fields || [];
  return (
    <main className="min-h-screen bg-slate-950 px-4 py-10 text-slate-100 sm:px-6">
      <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[0.85fr_1.15fr]">
        <aside className="rounded-3xl border border-cyan-900/60 bg-gradient-to-br from-cyan-950/60 via-slate-900 to-indigo-950/60 p-8"><p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-300">Autergo application</p><h1 className="mt-4 text-4xl font-semibold tracking-tight">{meta?.drive?.title}</h1><p className="mt-2 text-lg text-cyan-100">{meta?.drive?.job_role}</p><div className="mt-8 space-y-4 text-sm text-slate-300"><p>{meta?.drive?.description || 'Complete this application so the recruiting team can evaluate your experience against the role requirements.'}</p><div className="rounded-2xl border border-white/10 bg-black/20 p-4"><div className="text-xs uppercase tracking-widest text-slate-500">Role requirements</div><div className="mt-2">{meta?.drive?.skills_required || 'See the role description for requirements.'}</div></div><div className="rounded-2xl border border-white/10 bg-black/20 p-4"><div className="text-xs uppercase tracking-widest text-slate-500">What happens next</div><div className="mt-2">Your application is matched to the JD, reviewed by a recruiter, and may lead to an online test or interview.</div></div></div></aside>
        <form onSubmit={submit} className="rounded-3xl border border-slate-800 bg-slate-900/80 p-6 shadow-2xl shadow-black/20 sm:p-8"><div><h2 className="text-2xl font-semibold">Tell us about yourself</h2><p className="mt-1 text-sm text-slate-400">Fields marked required are used for initial ATS screening.</p></div>{status.error && <div className="mt-5 rounded-lg border border-rose-900 bg-rose-950/40 px-4 py-3 text-sm text-rose-200">{status.error}</div>}<div className="mt-6 grid gap-4 sm:grid-cols-2">{fields.map((field) => { const value = form[field.name] || ''; const isResume = field.name === 'resume_text'; return <label key={field.name} className={isResume ? 'sm:col-span-2' : ''}><span className="mb-1.5 block text-sm font-medium text-slate-300">{field.label}{field.required && <span className="text-cyan-400"> *</span>}</span>{isResume ? <textarea required={field.required} value={value} onChange={(event) => setForm({ ...form, [field.name]: event.target.value })} className="field min-h-40" placeholder="Paste your resume, experience, projects, or a concise professional summary" /> : <input required={field.required} type={field.name === 'phone' ? 'tel' : 'text'} value={value} onChange={(event) => setForm({ ...form, [field.name]: event.target.value })} className="field" placeholder={field.label} />}</label>; })}</div><label className="mt-6 flex items-start gap-3 rounded-xl border border-slate-800 bg-slate-950/60 p-4 text-sm text-slate-300"><input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-1" /><span>I consent to Autergo processing my application, interview, assessment, and proctoring data for this hiring process. I understand that proctoring signals are review evidence and not an automatic rejection.</span></label><button disabled={status.submitting} type="submit" className="mt-6 w-full rounded-xl bg-cyan-400 px-4 py-3 font-semibold text-slate-950 transition hover:bg-cyan-300 disabled:cursor-not-allowed disabled:opacity-50">{status.submitting ? 'Submitting…' : 'Submit application'}</button></form>
      </div>
    </main>
  );
}
