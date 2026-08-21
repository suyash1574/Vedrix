import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import apiClient from '../services/api';

function formatTime(seconds) {
  const safe = Math.max(0, Number(seconds) || 0);
  const minutes = Math.floor(safe / 60).toString().padStart(2, '0');
  const remaining = Math.floor(safe % 60).toString().padStart(2, '0');
  return `${minutes}:${remaining}`;
}

export default function AssessmentRoom() {
  const { assignmentId } = useParams();
  const navigate = useNavigate();
  const [assessment, setAssessment] = useState(null);
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({});
  const [consent, setConsent] = useState(false);
  const [remaining, setRemaining] = useState(null);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');

  const loadAssessment = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/hiring/assignments/${assignmentId}`);
      setAssessment(response.data);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load the assessment.');
    } finally {
      setLoading(false);
    }
  }, [assignmentId]);

  useEffect(() => { loadAssessment(); }, [loadAssessment]);

  const startAttempt = async () => {
    if (!consent) {
      setError('Please confirm the assessment and proctoring notice before starting.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const response = await apiClient.post(`/hiring/assignments/${assignmentId}/attempt`);
      setAttempt(response.data);
      setRemaining((assessment?.assignment?.duration_minutes || 45) * 60);
      setNotice('Assessment started. Your answers autosave as you work.');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not start the assessment.');
    } finally {
      setBusy(false);
    }
  };

  const saveAnswer = async (questionId, value, finalize = false) => {
    if (!attempt) return;
    setAnswers((current) => ({ ...current, [questionId]: value }));
    try {
      await apiClient.post(`/hiring/assignments/${assignmentId}/responses`, {
        question_id: questionId,
        response_data: value,
        question_version: 1,
        idempotency_key: `${attempt.id}-${questionId}-${Date.now()}`,
        finalize,
      });
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Answer autosave failed; please retry.');
    }
  };

  const emitProctorEvent = useCallback(async (eventType, payload = {}) => {
    if (!attempt) return;
    try {
      await apiClient.post(`/hiring/attempts/${attempt.id}/events`, { event_type: eventType, payload });
    } catch (requestError) {
      setNotice(requestError.response?.data?.detail || 'A proctoring event could not be recorded.');
    }
  }, [attempt]);

  useEffect(() => {
    if (!attempt) return undefined;
    const onVisibilityChange = () => {
      if (document.visibilityState === 'hidden') emitProctorEvent('tab_switch');
    };
    document.addEventListener('visibilitychange', onVisibilityChange);
    return () => document.removeEventListener('visibilitychange', onVisibilityChange);
  }, [attempt, emitProctorEvent]);

  useEffect(() => {
    if (!attempt || remaining == null) return undefined;
    if (remaining <= 0) {
      setNotice('Time expired. Submit your saved responses now.');
      return undefined;
    }
    const timer = window.setInterval(() => setRemaining((value) => Math.max(0, (value || 0) - 1)), 1000);
    return () => window.clearInterval(timer);
  }, [attempt, remaining]);

  const submitAttempt = async () => {
    if (!attempt) return;
    setBusy(true);
    try {
      const response = await apiClient.post(`/hiring/attempts/${attempt.id}/submit`, {
        answers,
        result: 'submitted',
      });
      setNotice(`Assessment submitted. Score: ${response.data.score ?? 'pending recruiter review'}.`);
      setAttempt(null);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not submit the assessment.');
    } finally {
      setBusy(false);
    }
  };

  const questions = useMemo(() => assessment?.questions || [], [assessment]);

  if (loading) return <div className="min-h-screen bg-slate-950 p-8 text-slate-200">Loading assessment…</div>;

  return (
    <main className="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-8">
      <div className="mx-auto max-w-4xl space-y-6">
        <header className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
          <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-400">Autergo online assessment</p>
          <h1 className="mt-2 text-3xl font-semibold">{assessment?.assignment?.title || 'Online test'}</h1>
          <p className="mt-2 text-sm text-slate-400">{assessment?.assignment?.instructions || 'Answer each question carefully. Your responses are autosaved.'}</p>
          <div className="mt-4 flex flex-wrap gap-3 text-xs text-slate-300">
            <span className="rounded-full bg-slate-800 px-3 py-1">Duration: {assessment?.assignment?.duration_minutes || 45} minutes</span>
            <span className="rounded-full bg-slate-800 px-3 py-1">Questions: {questions.length}</span>
            {assessment?.assignment?.proctoring_enabled && <span className="rounded-full bg-amber-950/60 px-3 py-1 text-amber-200">Consent-based proctoring enabled</span>}
          </div>
        </header>

        {error && <div className="rounded-lg border border-rose-900 bg-rose-950/50 px-4 py-3 text-sm text-rose-200">{error}</div>}
        {notice && <div className="rounded-lg border border-emerald-900 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

        {!attempt ? (
          <section className="rounded-2xl border border-slate-800 bg-slate-900/80 p-6">
            <h2 className="text-lg font-semibold">Before you start</h2>
            <p className="mt-2 text-sm leading-6 text-slate-400">{assessment?.proctoring_notice}</p>
            <label className="mt-5 flex items-start gap-3 rounded-xl border border-slate-700 bg-slate-950/50 p-4 text-sm text-slate-300">
              <input type="checkbox" checked={consent} onChange={(event) => setConsent(event.target.checked)} className="mt-1" />
              <span>I understand the assessment rules and consent to the configured proctoring signals. I understand that signals are reviewable evidence and are not automatic rejection decisions.</span>
            </label>
            <button type="button" disabled={busy} onClick={startAttempt} className="mt-5 rounded-lg bg-cyan-500 px-5 py-3 text-sm font-semibold text-slate-950 disabled:opacity-50">Start assessment</button>
          </section>
        ) : (
          <section className="space-y-5">
            <div className="sticky top-4 z-10 flex items-center justify-between rounded-xl border border-cyan-800 bg-cyan-950/90 px-4 py-3 shadow-lg shadow-black/20">
              <span className="text-sm text-cyan-100">Attempt #{attempt.attempt_number} · Autosave on</span>
              <span className={`font-mono text-lg font-semibold ${remaining < 300 ? 'text-rose-300' : 'text-white'}`}>{formatTime(remaining)}</span>
            </div>
            {questions.map((question, index) => (
              <article key={question.id} className="rounded-2xl border border-slate-800 bg-slate-900/80 p-5">
                <div className="flex gap-3"><span className="text-sm text-cyan-400">{index + 1}.</span><h2 className="font-medium">{question.prompt}</h2></div>
                {question.question_type === 'multiple_choice' && question.options?.length ? (
                  <div className="mt-4 space-y-2">{question.options.map((option) => <label key={option} className="flex items-center gap-3 rounded-lg border border-slate-700 p-3 text-sm text-slate-300"><input type="radio" name={`question-${question.id}`} checked={answers[question.id] === option} onChange={() => saveAnswer(question.id, option)} />{option}</label>)}</div>
                ) : <textarea value={answers[question.id] || ''} onChange={(event) => saveAnswer(question.id, event.target.value)} className="field mt-4 min-h-28 w-full" placeholder="Type your response…" />}
              </article>
            ))}
            {!questions.length && <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">This assessment has no published questions yet. Contact the recruiter.</div>}
            <div className="flex flex-wrap justify-between gap-3"><button type="button" onClick={() => navigate('/dashboard')} className="rounded-lg border border-slate-700 px-4 py-2 text-sm text-slate-300">Save and exit</button><button type="button" disabled={busy} onClick={submitAttempt} className="rounded-lg bg-emerald-500 px-5 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">Submit assessment</button></div>
          </section>
        )}
      </div>
    </main>
  );
}
