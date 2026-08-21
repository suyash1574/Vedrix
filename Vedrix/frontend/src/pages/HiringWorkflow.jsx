import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import apiClient from '../services/api';

const STATES = [
  'screening',
  'assessment_assigned',
  'assessment_in_progress',
  'assessment_review',
  'cheat_review',
  'ai_interview_scheduled',
  'ai_interview_in_progress',
  'ai_interview_review',
  'human_interview_scheduled',
  'human_interview',
  'final_review',
  'decided',
  'interview_scheduled',
  'manual_interview',
  'in_progress',
  'evaluated',
  'shortlisted',
];

const PIPELINE_STAGES = ['Assessment + proctoring', 'AI interview', 'Human interview', 'Final decision'];

const emptyManual = {
  interview_type: 'manual_interview',
  score: '',
  recommendation: 'pending',
  duration_minutes: 45,
  notes: '',
};

function formatDate(value) {
  if (!value) return '—';
  return new Date(value).toLocaleString();
}

function stateLabel(value) {
  return String(value || 'unknown').replaceAll('_', ' ');
}

export default function HiringWorkflow() {
  const { driveId } = useParams();
  const [applications, setApplications] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [report, setReport] = useState(null);
  const [audit, setAudit] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [assessment, setAssessment] = useState({ title: 'Role assessment', duration_minutes: 45, passing_score: 70, proctoring_enabled: true });
  const [manual, setManual] = useState(emptyManual);
  const [override, setOverride] = useState({ target_state: 'interview_scheduled', rationale: '' });
  const [decision, setDecision] = useState({ decision: 'on_hold', rationale: '' });
  const [aiInterview, setAiInterview] = useState({ start_time: '', duration_minutes: 30, rationale: '' });
  const [aiReview, setAiReview] = useState({ session_id: '', status: 'approved', confidence: '', rationale: '' });
  const [humanSchedule, setHumanSchedule] = useState({ interviewer_id: '', scheduled_at: '', interview_type: 'human_interview', rationale: '' });
  const [humanReview, setHumanReview] = useState({ schedule_id: '', score: '', recommendation: 'pending', duration_minutes: 45, notes: '' });

  const selected = useMemo(
    () => applications.find((application) => application.id === selectedId) || applications[0],
    [applications, selectedId],
  );

  const loadApplications = useCallback(async () => {
    setLoading(true);
    try {
      const response = await apiClient.get(`/hiring/drives/${driveId}/applications`);
      setApplications(response.data || []);
      setSelectedId((current) => current || response.data?.[0]?.id || null);
      setError('');
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load applications.');
    } finally {
      setLoading(false);
    }
  }, [driveId]);

  useEffect(() => { loadApplications(); }, [loadApplications]);

  const runAction = async (action, successMessage) => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      setNotice(successMessage);
      await loadApplications();
      if (selected) await loadReport(selected.id);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'The action could not be completed.');
    } finally {
      setBusy(false);
    }
  };

  const loadReport = async (applicationId) => {
    if (!applicationId) return;
    try {
      const response = await apiClient.get(`/hiring/drives/${driveId}/applications/${applicationId}/report`);
      setReport(response.data);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load the candidate report.');
    }
  };

  const loadAudit = async (candidateId) => {
    try {
      const response = await apiClient.get(`/hiring/drives/${driveId}/audit`, { params: { candidate_id: candidateId } });
      setAudit(response.data || []);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not load the audit timeline.');
    }
  };

  useEffect(() => {
    if (selected?.id) {
      loadReport(selected.id);
      loadAudit(selected.candidate_id);
    }
  }, [selected?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  const assignAssessment = () => runAction(
    () => apiClient.post(`/hiring/drives/${driveId}/applications/${selected.id}/assessment`, {
      application_id: selected.id,
      title: assessment.title,
      duration_minutes: Number(assessment.duration_minutes),
      passing_score: Number(assessment.passing_score),
      proctoring_enabled: assessment.proctoring_enabled,
      config: {},
    }),
    'Assessment assigned and the candidate moved into the assessment stage.',
  );

  const saveManualInterview = () => runAction(
    () => apiClient.post(`/hiring/drives/${driveId}/applications/${selected.id}/manual-interview`, {
      application_id: selected.id,
      interview_type: manual.interview_type,
      score: manual.score === '' ? null : Number(manual.score),
      recommendation: manual.recommendation,
      duration_minutes: Number(manual.duration_minutes),
      notes: { text: manual.notes },
      rubric: {},
    }),
    'Manual interview record saved to the candidate trace.',
  );

  const applyOverride = () => runAction(
    () => apiClient.post(`/hiring/drives/${driveId}/workflow/${selected.candidate_id}/override`, override),
    'Recruiter override recorded with rationale.',
  );

  const saveDecision = () => runAction(
    () => apiClient.post(`/hiring/drives/${driveId}/workflow/${selected.candidate_id}/decision`, decision),
    'Recruiter decision recorded.',
  );

  const scheduleAIInterview = () => runAction(
    () => apiClient.post(`/hiring/applications/${selected.id}/ai-interview`, {
      start_time: aiInterview.start_time || null,
      duration_minutes: Number(aiInterview.duration_minutes),
      rationale: aiInterview.rationale || null,
    }),
    'AI interview stage scheduled after the assessment gate.',
  );

  const reviewAIInterview = () => runAction(
    () => apiClient.post(`/hiring/applications/${selected.id}/ai-interview/review`, {
      session_id: Number(aiReview.session_id),
      status: aiReview.status,
      confidence: aiReview.confidence === '' ? null : Number(aiReview.confidence),
      rationale: aiReview.rationale,
    }),
    'AI interview review recorded; human scheduling is now policy-gated.',
  );

  const scheduleHumanInterview = () => runAction(
    () => apiClient.post(`/hiring/applications/${selected.id}/human-interview`, {
      interviewer_id: Number(humanSchedule.interviewer_id),
      interview_type: humanSchedule.interview_type,
      scheduled_at: humanSchedule.scheduled_at || null,
      rationale: humanSchedule.rationale || null,
    }),
    'Human interview scheduled after the AI interview gate.',
  );

  const submitHumanInterview = () => runAction(
    () => apiClient.post(`/hiring/applications/${selected.id}/human-interview/submit`, {
      schedule_id: Number(humanReview.schedule_id),
      score: humanReview.score === '' ? null : Number(humanReview.score),
      recommendation: humanReview.recommendation,
      duration_minutes: Number(humanReview.duration_minutes),
      notes: { text: humanReview.notes },
    }),
    'Human interview submitted; candidate moved to final review.',
  );

  if (loading) return <div className="min-h-screen bg-slate-950 p-8 text-slate-200">Loading hiring workflow…</div>;

  return (
    <div className="min-h-screen bg-slate-950 px-4 py-8 text-slate-100 sm:px-8">
      <div className="mx-auto max-w-7xl space-y-6">
        <header className="flex flex-col justify-between gap-4 border-b border-slate-800 pb-6 md:flex-row md:items-end">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.24em] text-cyan-400">Recruiter control center</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Hiring workflow</h1>
            <p className="mt-2 max-w-3xl text-sm text-slate-400">Run the complete process from JD-aligned intake to assessment review, manual interview capture, final decision, and an immutable candidate timeline.</p>
          </div>
          <div className="rounded-xl border border-slate-800 bg-slate-900 px-4 py-3 text-right text-xs text-slate-400">
            <div>Drive ID</div><div className="mt-1 font-mono text-slate-200">{driveId}</div>
          </div>
        </header>

        {error && <div className="rounded-lg border border-rose-900 bg-rose-950/50 px-4 py-3 text-sm text-rose-200">{error}</div>}
        {notice && <div className="rounded-lg border border-emerald-900 bg-emerald-950/50 px-4 py-3 text-sm text-emerald-200">{notice}</div>}

        <section className="grid gap-6 lg:grid-cols-[1.05fr_1.6fr]">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-4 shadow-xl shadow-black/20">
            <div className="mb-4 flex items-center justify-between">
              <div><h2 className="font-semibold">ATS applications</h2><p className="text-xs text-slate-500">JD match is a recommendation, not an automatic rejection.</p></div>
              <span className="rounded-full bg-slate-800 px-3 py-1 text-xs text-slate-300">{applications.length} candidates</span>
            </div>
            <div className="space-y-2">
              {applications.map((application) => (
                <button
                  key={application.id}
                  type="button"
                  onClick={() => setSelectedId(application.id)}
                  className={`w-full rounded-xl border p-3 text-left transition ${selected?.id === application.id ? 'border-cyan-500 bg-cyan-950/30' : 'border-slate-800 bg-slate-950/50 hover:border-slate-600'}`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div><div className="font-medium">{application.candidate_name || application.candidate_email}</div><div className="text-xs text-slate-500">{application.candidate_email}</div></div>
                    <div className="text-right"><div className="text-sm font-semibold text-cyan-300">{application.match_score == null ? '—' : `${Math.round(application.match_score)}%`}</div><div className="text-[10px] uppercase text-slate-500">JD match</div></div>
                  </div>
                  <div className="mt-3 flex items-center justify-between text-xs"><span className="rounded-full bg-slate-800 px-2 py-1 capitalize text-slate-300">{stateLabel(application.workflow_state)}</span><span className="text-slate-500">{formatDate(application.updated_at)}</span></div>
                </button>
              ))}
              {!applications.length && <div className="rounded-xl border border-dashed border-slate-700 p-8 text-center text-sm text-slate-500">No applications yet. Generate an invite link or open the public application form.</div>}
            </div>
          </div>

          <div className="space-y-6">
            {selected ? <>
              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5 shadow-xl shadow-black/20">
                <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start"><div><p className="text-xs uppercase tracking-widest text-cyan-400">Candidate dossier</p><h2 className="mt-1 text-2xl font-semibold">{selected.candidate_name}</h2><p className="text-sm text-slate-400">{selected.candidate_email}</p></div><span className="rounded-full border border-cyan-800 bg-cyan-950/40 px-3 py-1 text-xs capitalize text-cyan-200">{stateLabel(selected.workflow_state)}</span></div>
                <div className="mt-5 grid gap-3 sm:grid-cols-3"><div className="rounded-xl bg-slate-950/70 p-3"><div className="text-xs text-slate-500">ATS match</div><div className="mt-1 text-xl font-semibold">{selected.match_score == null ? '—' : `${Math.round(selected.match_score)}%`}</div></div><div className="rounded-xl bg-slate-950/70 p-3"><div className="text-xs text-slate-500">Consent</div><div className="mt-1 text-xl font-semibold">{selected.consent_granted ? 'Granted' : 'Missing'}</div></div><div className="rounded-xl bg-slate-950/70 p-3"><div className="text-xs text-slate-500">Submitted</div><div className="mt-1 text-sm font-semibold">{formatDate(selected.submitted_at)}</div></div></div>
                <div className="mt-5 flex flex-wrap gap-2"><button type="button" onClick={() => loadReport(selected.id)} className="rounded-lg bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950">Open full report</button><button type="button" onClick={() => loadAudit(selected.candidate_id)} className="rounded-lg border border-slate-700 px-3 py-2 text-sm text-slate-200">Refresh trace</button></div>
              </section>

              <section className="grid gap-6 xl:grid-cols-2">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><h3 className="font-semibold">Assign online test</h3><p className="mt-1 text-xs text-slate-500">Recruiter chooses duration, pass mark, and whether proctoring is required.</p><div className="mt-4 space-y-3"><input value={assessment.title} onChange={(event) => setAssessment({ ...assessment, title: event.target.value })} className="field" placeholder="Assessment title" /><div className="grid grid-cols-2 gap-3"><input type="number" value={assessment.duration_minutes} onChange={(event) => setAssessment({ ...assessment, duration_minutes: event.target.value })} className="field" placeholder="Minutes" /><input type="number" value={assessment.passing_score} onChange={(event) => setAssessment({ ...assessment, passing_score: event.target.value })} className="field" placeholder="Pass score" /></div><label className="flex items-center gap-2 text-sm text-slate-300"><input type="checkbox" checked={assessment.proctoring_enabled} onChange={(event) => setAssessment({ ...assessment, proctoring_enabled: event.target.checked })} /> Enable proctoring evidence capture</label><button disabled={busy} type="button" onClick={assignAssessment} className="w-full rounded-lg bg-indigo-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Assign assessment</button></div></div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><h3 className="font-semibold">Manual interview entry</h3><p className="mt-1 text-xs text-slate-500">Record offline, phone, panel, or recruiter-led interviews in the same dossier.</p><div className="mt-4 space-y-3"><div className="grid grid-cols-2 gap-3"><input type="number" value={manual.score} onChange={(event) => setManual({ ...manual, score: event.target.value })} className="field" placeholder="Score / 10" /><input type="number" value={manual.duration_minutes} onChange={(event) => setManual({ ...manual, duration_minutes: event.target.value })} className="field" placeholder="Minutes" /></div><select value={manual.recommendation} onChange={(event) => setManual({ ...manual, recommendation: event.target.value })} className="field"><option value="pending">Pending</option><option value="strong_yes">Strong yes</option><option value="yes">Yes</option><option value="no">No</option><option value="strong_no">Strong no</option></select><textarea value={manual.notes} onChange={(event) => setManual({ ...manual, notes: event.target.value })} className="field min-h-24" placeholder="Interview notes, evidence, and concerns" /><button disabled={busy} type="button" onClick={saveManualInterview} className="w-full rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">Save manual interview</button></div></div>
              </section>

              <section className="rounded-2xl border border-cyan-900/70 bg-cyan-950/10 p-5">
                <h3 className="font-semibold">Canonical hiring sequence</h3>
                <p className="mt-1 text-xs text-slate-500">The default gate is online test and proctor review, then AI interview, then human interview, then final decision.</p>
                <div className="mt-4 grid gap-2 sm:grid-cols-4">{PIPELINE_STAGES.map((stage, index) => <div key={stage} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs"><div className="text-cyan-400">0{index + 1}</div><div className="mt-1 text-slate-200">{stage}</div></div>)}</div>
              </section>

              <section className="grid gap-6 xl:grid-cols-2">
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                  <h3 className="font-semibold">AI interview gate</h3>
                  <p className="mt-1 text-xs text-slate-500">Schedule the AI interview after assessment clearance, then explicitly approve it before human scheduling.</p>
                  <div className="mt-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3"><input type="datetime-local" value={aiInterview.start_time} onChange={(event) => setAiInterview({ ...aiInterview, start_time: event.target.value })} className="field" /><input type="number" value={aiInterview.duration_minutes} onChange={(event) => setAiInterview({ ...aiInterview, duration_minutes: event.target.value })} className="field" placeholder="Minutes" /></div>
                    <textarea value={aiInterview.rationale} onChange={(event) => setAiInterview({ ...aiInterview, rationale: event.target.value })} className="field min-h-16" placeholder="Scheduling rationale (optional)" />
                    <button disabled={busy} type="button" onClick={scheduleAIInterview} className="w-full rounded-lg bg-cyan-500 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">Schedule AI interview</button>
                    <select value={aiReview.session_id} onChange={(event) => setAiReview({ ...aiReview, session_id: event.target.value })} className="field"><option value="">Select completed AI session</option>{(report?.ai_interviews || []).map((session) => <option key={session.id} value={session.id}>Session #{session.id} · {session.status}</option>)}</select>
                    <div className="grid grid-cols-2 gap-3"><select value={aiReview.status} onChange={(event) => setAiReview({ ...aiReview, status: event.target.value })} className="field"><option value="approved">Approve for human interview</option><option value="follow_up">Request AI follow-up</option><option value="hold">Put on hold</option><option value="rejected">Reject</option></select><input type="number" min="0" max="1" step="0.01" value={aiReview.confidence} onChange={(event) => setAiReview({ ...aiReview, confidence: event.target.value })} className="field" placeholder="Confidence 0–1" /></div>
                    <textarea value={aiReview.rationale} onChange={(event) => setAiReview({ ...aiReview, rationale: event.target.value })} className="field min-h-16" placeholder="AI review rationale" />
                    <button disabled={busy || !aiReview.session_id || !aiReview.rationale.trim()} type="button" onClick={reviewAIInterview} className="w-full rounded-lg border border-cyan-700 bg-cyan-950/50 px-3 py-2 text-sm font-semibold text-cyan-200 disabled:opacity-50">Record AI review</button>
                  </div>
                </div>
                <div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5">
                  <h3 className="font-semibold">Human interview gate</h3>
                  <p className="mt-1 text-xs text-slate-500">Human scheduling is rejected by the API until the AI interview is completed and reviewed, unless a recruiter override is recorded.</p>
                  <div className="mt-4 space-y-3">
                    <div className="grid grid-cols-2 gap-3"><input type="number" value={humanSchedule.interviewer_id} onChange={(event) => setHumanSchedule({ ...humanSchedule, interviewer_id: event.target.value })} className="field" placeholder="Interviewer user ID" /><input type="datetime-local" value={humanSchedule.scheduled_at} onChange={(event) => setHumanSchedule({ ...humanSchedule, scheduled_at: event.target.value })} className="field" /></div>
                    <input value={humanSchedule.interview_type} onChange={(event) => setHumanSchedule({ ...humanSchedule, interview_type: event.target.value })} className="field" placeholder="Interview type" />
                    <textarea value={humanSchedule.rationale} onChange={(event) => setHumanSchedule({ ...humanSchedule, rationale: event.target.value })} className="field min-h-16" placeholder="Scheduling rationale" />
                    <button disabled={busy || !humanSchedule.interviewer_id} type="button" onClick={scheduleHumanInterview} className="w-full rounded-lg bg-emerald-500 px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-50">Schedule human interview</button>
                    <div className="grid grid-cols-2 gap-3"><input type="number" value={humanReview.schedule_id} onChange={(event) => setHumanReview({ ...humanReview, schedule_id: event.target.value })} className="field" placeholder="Schedule ID" /><input type="number" value={humanReview.score} onChange={(event) => setHumanReview({ ...humanReview, score: event.target.value })} className="field" placeholder="Score" /></div>
                    <select value={humanReview.recommendation} onChange={(event) => setHumanReview({ ...humanReview, recommendation: event.target.value })} className="field"><option value="pending">Pending</option><option value="strong_yes">Strong yes</option><option value="yes">Yes</option><option value="no">No</option><option value="strong_no">Strong no</option></select>
                    <textarea value={humanReview.notes} onChange={(event) => setHumanReview({ ...humanReview, notes: event.target.value })} className="field min-h-16" placeholder="Human interview notes" />
                    <button disabled={busy || !humanReview.schedule_id} type="button" onClick={submitHumanInterview} className="w-full rounded-lg border border-emerald-700 bg-emerald-950/50 px-3 py-2 text-sm font-semibold text-emerald-200 disabled:opacity-50">Submit human interview</button>
                  </div>
                </div>
              </section>

              <section className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><h3 className="font-semibold">Recruiter authority</h3><p className="mt-1 text-xs text-slate-500">Every override and decision requires a rationale and is written to the audit timeline.</p><div className="mt-4 grid gap-3 md:grid-cols-2"><div className="space-y-3"><select value={override.target_state} onChange={(event) => setOverride({ ...override, target_state: event.target.value })} className="field">{STATES.map((state) => <option key={state} value={state}>{stateLabel(state)}</option>)}</select><textarea value={override.rationale} onChange={(event) => setOverride({ ...override, rationale: event.target.value })} className="field min-h-20" placeholder="Why is this override appropriate?" /><button disabled={busy || !override.rationale.trim()} type="button" onClick={applyOverride} className="w-full rounded-lg border border-amber-700 bg-amber-950/40 px-3 py-2 text-sm font-semibold text-amber-200 disabled:opacity-50">Apply stage override</button></div><div className="space-y-3"><select value={decision.decision} onChange={(event) => setDecision({ ...decision, decision: event.target.value })} className="field"><option value="on_hold">On hold</option><option value="hired">Hire</option><option value="rejected">Reject</option><option value="withdrawn">Withdraw</option></select><textarea value={decision.rationale} onChange={(event) => setDecision({ ...decision, rationale: event.target.value })} className="field min-h-20" placeholder="Decision rationale" /><button disabled={busy || !decision.rationale.trim()} type="button" onClick={saveDecision} className="w-full rounded-lg bg-rose-500 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50">Record decision</button></div></div></section>
            </> : <div className="rounded-2xl border border-dashed border-slate-700 p-12 text-center text-slate-500">Select an application to manage its hiring journey.</div>}
          </div>
        </section>

        {selected && <section className="grid gap-6 lg:grid-cols-2"><div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><h2 className="font-semibold">Unified report</h2><p className="mt-1 text-xs text-slate-500">ATS, assessments, proctor review, AI interviews, and manual entries in one view.</p>{report ? <div className="mt-4 space-y-3 text-sm"><div className="rounded-lg bg-slate-950/70 p-3">Assessments: <strong>{report.assessments?.length || 0}</strong> · Manual interviews: <strong>{report.manual_interviews?.length || 0}</strong> · AI interviews: <strong>{report.ai_interviews?.length || 0}</strong></div>{report.assessments?.map(({ assignment, attempts }) => <div key={assignment.id} className="rounded-lg border border-slate-800 p-3"><div className="font-medium">{assignment.title}</div>{attempts.map((attempt) => <div key={attempt.id} className="mt-2 flex flex-wrap justify-between gap-2 text-xs text-slate-400"><span>Attempt {attempt.attempt_number}: {attempt.status}</span><span>Score: {attempt.score ?? '—'}</span><span>Cheat review: {attempt.cheating_status}</span></div>)}</div>)}<p className="text-xs text-amber-300">{report.review_guidance}</p></div> : <div className="mt-4 text-sm text-slate-500">Open the report to load the dossier.</div>}</div><div className="rounded-2xl border border-slate-800 bg-slate-900/70 p-5"><h2 className="font-semibold">Traceability timeline</h2><p className="mt-1 text-xs text-slate-500">Immutable business events, recruiter actions, candidate actions, and system transitions.</p><div className="mt-4 max-h-80 space-y-2 overflow-auto">{audit.map((event) => <div key={event.id} className="rounded-lg border border-slate-800 bg-slate-950/50 p-3 text-xs"><div className="flex justify-between gap-2"><span className="font-medium text-cyan-300">{stateLabel(event.action)}</span><span className="text-slate-500">{formatDate(event.occurred_at)}</span></div><div className="mt-1 text-slate-400">{event.actor_type} · {event.rationale || 'No rationale recorded'}</div>{event.from_state && <div className="mt-1 text-slate-500">{stateLabel(event.from_state)} → {stateLabel(event.to_state)}</div>}</div>)}{!audit.length && <div className="text-sm text-slate-500">No audit events loaded.</div>}</div></div></section>}
      </div>
    </div>
  );
}
