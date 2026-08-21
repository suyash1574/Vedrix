# Autergo End-to-End Hiring Workflow

## Purpose

Autergo now supports a recruiter-controlled hiring process from JD-specific candidate intake through ATS screening, online assessments, proctoring evidence review, AI or manual interviews, recruiter decisions, and a unified audit timeline.

> **Important fairness rule:** Proctoring signals are evidence for human review. A tab switch, paste event, camera anomaly, or typing anomaly does not automatically reject a candidate. Recruiters must record the review outcome and rationale.

## Workflow

| Stage | Meaning | Recruiter controls |
|---|---|---|
| `screening` | Candidate submitted the recruiter-configured application form and received an explainable JD match score. | Review form data, resume context, match terms, missing terms, and screening notes. |
| `assessment_assigned` | An online test has been assigned. | Choose title, duration, pass score, assessment configuration, deadline, and proctoring requirement. |
| `assessment_in_progress` | Candidate started an assessment attempt. | Monitor attempt state and captured proctoring evidence. |
| `assessment_review` | Candidate submitted the assessment. | Review score, answers, evidence, and risk summary. Pass, flag suspected cheating, request a retake, route to interview, or reject. |
| `cheat_review` | Proctoring signals require an explicit human review. | Clear the signal, confirm cheating with rationale, request a retake, or route to a manual interview. |
| `interview_scheduled` | Candidate is ready for an interview. | Schedule the AI interview, manual interview, or another recruiter-defined step. |
| `in_progress` | A live AI interview is running. | Monitor, whisper, take over, close, and later review the AI transcript and report. |
| `manual_interview` | A recruiter, panel, phone, or offline interview is being captured manually. | Enter rubric scores, notes, recommendation, duration, and evidence. |
| `evaluated` | Interview and assessment evidence are available for review. | Add manual feedback, shortlist, reject, or route back to a manual interview. |
| `shortlisted` | Candidate passed the review gate. | Hire or reject with rationale. |
| `decided` | A final recruiter decision has been recorded. | Final state is immutable through ordinary transitions; use the explicit override endpoint if policy permits reopening. |

Existing legacy transitions (`invited → scheduled → in_progress → evaluated → shortlisted → decided`) remain supported for backward compatibility.

## Candidate intake and ATS matching

Recruiters configure the application form on a job drive through `application_form_config`. The public form is available at `/apply/{token}` and returns the drive description, skills, custom fields, assessment policy, and workflow policy. A submitted application stores structured form data, resume text or URL, consent, source, timestamps, and a deterministic explainable match result.

The current baseline scorer uses token overlap across the JD title, description, role, experience, and skills against the application’s resume and form data. It returns a bounded score, matched terms, missing terms, and the scoring method. It is intentionally a recommendation layer so recruiters can override it.

## Online assessment and proctoring

Recruiters assign assessments with a duration, passing score, configuration object, deadline, and `proctoring_enabled` flag. Candidate attempts record encrypted answers, score, result, timestamps, and a structured proctor summary. The proctor-event endpoint stores capped event history, event counts, risk score, and risk level.

Assessment attempts support `not_started`, `started`, and `submitted` states. The recruiter review endpoint accepts `not_reviewed`, `cleared`, `suspected`, or `confirmed`. A suspected signal routes the workflow to `cheat_review`; only an explicit `confirmed` review records a final cheating disposition.

## Manual interviews and unified reports

Recruiters can add manual interview entries for phone screens, panel interviews, offline meetings, or any external interview. Each entry stores interviewer identity, interview type, occurrence time, duration, rubric, encrypted notes, score, and recommendation.

The unified report endpoint combines the application, workflow state, assessments and attempts, proctor review, manual interviews, AI interview sessions, and audit events. The existing AI interview PDF/report endpoints remain available for session-specific reports.

## API surface

| Route | Purpose |
|---|---|
| `GET /api/v1/hiring/apply/{token}` | Load a recruiter-configured public application form. |
| `POST /api/v1/hiring/apply/{token}` | Submit candidate data and consent; create/update ATS application. |
| `GET /api/v1/hiring/drives/{drive_id}/applications` | Recruiter application list with match score and workflow state. |
| `POST /api/v1/hiring/drives/{drive_id}/applications/{application_id}/assessment` | Assign an online assessment. |
| `POST /api/v1/hiring/assignments/{assignment_id}/attempt` | Candidate starts an assessment attempt. |
| `POST /api/v1/hiring/attempts/{attempt_id}/proctor-event` | Candidate submits consent-gated proctor evidence. |
| `POST /api/v1/hiring/attempts/{attempt_id}/submit` | Candidate submits an assessment. |
| `POST /api/v1/hiring/drives/{drive_id}/assessment-attempts/{attempt_id}/review` | Recruiter clears, suspects, or confirms cheating evidence. |
| `POST /api/v1/hiring/drives/{drive_id}/applications/{application_id}/manual-interview` | Add recruiter-entered interview data. |
| `POST /api/v1/hiring/drives/{drive_id}/workflow/{candidate_id}/override` | Move a candidate to any valid workflow state with rationale. |
| `POST /api/v1/hiring/drives/{drive_id}/workflow/{candidate_id}/decision` | Record hire, reject, withdraw, or hold. |
| `GET /api/v1/hiring/drives/{drive_id}/applications/{application_id}/report` | Retrieve the unified candidate dossier. |
| `GET /api/v1/hiring/drives/{drive_id}/audit` | Retrieve the recruiter/candidate/system audit timeline. |

## Traceability

Every application submission, assessment assignment/start/submission, proctor event, assessment review, manual interview, recruiter override, and final decision creates a `WorkflowAuditEvent`. The existing `CandidateWorkflow.transition_history` and `TraceEntry` observability records remain in place, providing both business-level and agent-level traceability.

The feature uses PostgreSQL models and Alembic migration `b7c9d1e2f3a4_add_hiring_workflow_entities.py`. Run the normal production migration command against the fresh PostgreSQL database before enabling the workflow.

## Frontend entry points

Recruiters can open `/hr/drives/:driveId/hiring-workflow` from each job-drive card. The workspace provides ATS applications, assessment assignment, manual interview entry, stage overrides, final decisions, unified report preview, and a traceability timeline. Candidates open `/apply/:token` from their invite link.
