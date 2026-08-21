# Autergo End-to-End Hiring Workflow

## Purpose

Autergo supports a recruiter-controlled hiring process from JD-specific candidate intake through ATS screening, a timed online assessment with consent-based proctoring, an AI interview, a human interview, recruiter review, and a final decision. Every stage is represented in PostgreSQL and contributes to a unified candidate dossier and append-only audit timeline.

> **Fairness rule:** Proctoring signals and AI scores are decision-support evidence. A tab switch, paste event, camera anomaly, behavioral signal, or model score must never automatically reject a candidate. A recruiter must record the human review outcome and rationale.

## Canonical candidate sequence

| Stage | Meaning | Recruiter controls |
|---|---|---|
| `screening` | Candidate submitted the recruiter-configured form and received an explainable JD match score. | Review form data, resume context, match terms, missing terms, notes, and screening outcome. |
| `assessment_assigned` | A versioned online test is available. | Select test definition, duration, pass score, attempts, deadline, proctoring permissions, and consent version. |
| `assessment_in_progress` | Candidate is completing the test with server-backed timing and autosave. | Monitor attempt status and review structured proctoring evidence. |
| `assessment_review` | Assessment responses, score, and proctor summary await review. | Pass, fail, retake, clear evidence, flag suspected evidence, confirm cheating with rationale, hold, or override. |
| `cheat_review` | A proctoring signal requires explicit human review. | Clear the signal, confirm cheating, request a retake, or use an audited override. |
| `ai_interview_scheduled` | Candidate is cleared for the AI interview. | Schedule, reschedule, cancel, bypass with rationale, and select the interview policy. |
| `ai_interview_in_progress` | The live AI interview is running. | Monitor, take over, close, and review timing, transcript, coordination, and evaluation evidence. |
| `ai_interview_review` | AI transcript/report awaits recruiter approval or follow-up. | Approve human progression, request follow-up, hold, reject, or override. |
| `human_interview_scheduled` | A human interviewer and appointment are assigned. | Select interviewer, type, schedule, meeting location/link, rubric, and reminders. |
| `human_interview` | The interview is live or being captured manually. | Record rubric scores, notes, recommendation, duration, evidence links, and schedule changes. |
| `final_review` | Required evidence is assembled for the final recruiter decision. | Hire, reject, withdraw, hold, or override with rationale. |
| `decided` | Final decision has been recorded. | Ordinary transitions are closed; reopening requires explicit administrative override. |

New applications follow the explicit sequence. Existing legacy states (`invited`, `scheduled`, `in_progress`, `evaluated`, `shortlisted`, `manual_interview`, and `interview_scheduled`) remain readable for compatibility. Recruiter bypasses and legacy routes are retained, but every bypass is recorded as an override event.

## Recruiter policy

Each job drive stores a validated workflow policy. The default policy enables the assessment, consent-based proctoring, AI interview, and human interview in that order. Recruiters may disable optional stages, configure required gates, set attempt and deadline rules, choose whether AI review approval is mandatory, define human rubrics, and specify permitted bypasses. The policy is normalized and snapshotted onto each application so later drive edits do not silently change an in-progress candidate’s contract.

The primary policy groups are `assessment_enabled`, `assessment_required`, `proctoring_enabled`, `ai_interview_enabled`, `ai_interview_required`, `human_interview_enabled`, `human_interview_required`, `stage_order`, assessment timing and attempt settings, proctoring consent and risk settings, AI interview confidence/approval settings, human interview types/rubrics, allowed bypasses, and hold reasons. The API rejects a stage order that places the AI interview after the human interview.

## Online test and proctoring

Recruiters create a versioned assessment definition with public-safe questions and server-side answer metadata. Candidates receive only question prompts, options, scoring points, and coding configuration; expected answers remain server-side. The candidate must acknowledge the assessment and privacy/proctoring notice before starting.

The assessment room uses a server-created attempt, server-backed duration, per-question autosave, reconnect-safe responses, and idempotent submission. Structured evidence events may include tab switch, fullscreen exit, paste, multiple faces, no face, gaze deviation, anomalous typing, and permission-denied events. The server validates candidate ownership, event type, consent version, timestamp skew, payload size, and rate limits. It maintains a risk summary for recruiter review, but does not automatically reject or terminate a candidate unless a drive policy explicitly requires a pause.

When submitted, an attempt becomes immutable for ordinary candidate writes and enters `assessment_review`. Recruiters can inspect score, answers, event counts, risk level, evidence references, and review history. A cleared/passed assessment advances to the AI stage for V2 applications; suspected evidence enters `cheat_review` first.

## AI interview

After the assessment gate is cleared, Autergo creates an AI interview stage run and links it to an `InterviewSession`. The existing NOOA/ReAct routing, response validation, clarification handling, WebSocket coordination, timing budgets, precision flags, and degraded-mode indicators remain active. Completion stores the transcript, evaluation history, report, confidence, timing metadata, and correlation ID.

The AI result enters `ai_interview_review`. If the drive requires recruiter approval, the recruiter must explicitly approve it before a human interview can be scheduled. Low-confidence or provider-degraded results remain visible as review flags and cannot silently progress as high-confidence evidence.

## Human interview

Only an AI-reviewed application can enter `human_interview_scheduled` through the normal path. The scheduling endpoint records interviewer identity, interview type, time, timezone, meeting location/link, rubric, and the stage-run correlation. Notifications and reminders use the existing application notification service; third-party calendar integration is intentionally deferred.

The human interview may be conducted in Autergo or recorded manually for a phone, panel, onsite, or external meeting. Submission creates a linked `ManualInterviewEntry`, completes the human stage, and moves the candidate to `final_review`. The recruiter then records hire, reject, withdraw, or hold with a rationale.

## Data and traceability

The PostgreSQL migration `c8d4e5f6a7b8_add_ordered_hiring_pipeline.py` adds `HiringPipelineStageRun`, `AssessmentDefinition`, `AssessmentQuestion`, `AssessmentResponse`, `ProctorEvidenceEvent`, `AIInterviewStageReview`, and `HumanInterviewSchedule`. Existing application, assessment, attempt, manual interview, interview session, and workflow records remain available.

Each application captures a workflow-policy snapshot and version. Each stage run records stage key, sequence, status, required flag, due date, attempt number, outcome, score/confidence, assigned actor, related entity, and timing. Audit events include stage key, correlation ID, policy version, source, actor, state changes, rationale, and payload. The unified report returns ATS evidence, policy, stage runs, assessment attempts, proctor evidence, AI sessions and reviews, human schedules and entries, and the audit timeline.

## API surface

| Route | Purpose |
|---|---|
| `GET /api/v1/hiring/apply/{token}` | Load a recruiter-configured public application form. |
| `POST /api/v1/hiring/apply/{token}` | Submit candidate data, consent, ATS match, and policy snapshot. |
| `GET /api/v1/hiring/drives/{drive_id}/pipeline-policy` | Read normalized drive policy. |
| `PUT /api/v1/hiring/drives/{drive_id}/pipeline-policy` | Update policy with versioning and audit rationale. |
| `POST /api/v1/hiring/drives/{drive_id}/assessments` | Create and version an assessment definition/questions. |
| `GET /api/v1/hiring/drives/{drive_id}/assessments` | List drive assessment definitions. |
| `POST /api/v1/hiring/drives/{drive_id}/applications/{application_id}/assessment` | Assign an online assessment. |
| `GET /api/v1/hiring/assignments/{assignment_id}` | Return candidate-safe assignment instructions/questions. |
| `POST /api/v1/hiring/assignments/{assignment_id}/attempt` | Create/resume a candidate attempt. |
| `POST /api/v1/hiring/assignments/{assignment_id}/responses` | Autosave or finalize an encrypted question response. |
| `POST /api/v1/hiring/attempts/{attempt_id}/events` | Record validated structured proctor evidence. |
| `POST /api/v1/hiring/attempts/{attempt_id}/submit` | Atomically submit an assessment attempt. |
| `POST /api/v1/hiring/drives/{drive_id}/assessment-attempts/{attempt_id}/review` | Record recruiter assessment/proctor disposition. |
| `POST /api/v1/hiring/applications/{application_id}/ai-interview` | Schedule or resume the AI stage. |
| `POST /api/v1/hiring/applications/{application_id}/ai-interview/review` | Approve, hold, request follow-up, or reject the AI stage. |
| `POST /api/v1/hiring/applications/{application_id}/human-interview` | Schedule the human stage after AI review. |
| `POST /api/v1/hiring/applications/{application_id}/human-interview/submit` | Save manual human-interview evidence and complete the stage. |
| `POST /api/v1/hiring/applications/{application_id}/override-stage` | Bypass or reorder a stage with mandatory rationale. |
| `POST /api/v1/hiring/applications/{application_id}/pipeline-decision` | Record the final recruiter decision. |
| `GET /api/v1/hiring/applications/{application_id}/pipeline` | Return the candidate’s own stage status and next-step notice. |
| `GET /api/v1/hiring/drives/{drive_id}/applications/{application_id}/report` | Retrieve the unified candidate dossier. |
| `GET /api/v1/hiring/drives/{drive_id}/audit` | Retrieve recruiter/candidate/system audit events. |

## Frontend entry points

Recruiters open `/hr/drives/:driveId/hiring-workflow` to manage ATS applications, assessment assignment, proctor review, AI scheduling/review, human scheduling/submission, overrides, final decisions, unified reports, and traceability. Candidates open `/apply/:token` for intake and `/assessment/:assignmentId` for the consent-based online test. The candidate test room displays the timer, autosave status, question navigation, proctoring notice, and submission controls.

## Background processing and operations

The existing persistent backend and orchestrator scheduler handle deadline expiry, reminders, incomplete attempts, AI/human interview reminders, and stale-review escalation. WebSockets can be used for live attempt status, recruiter monitoring, proctor acknowledgement, and AI interview events. Scoring, report generation, and optional evidence processing should remain off the candidate’s latency-critical request path. Proctoring events are emitted by the candidate client and validated by the API; they are not collected by high-frequency polling tasks.

## Security and privacy

Consent is versioned before camera, microphone, screen, or behavioral signals are accepted. Answers and sensitive human notes use encrypted columns, evidence references should use signed/expiring URLs, and retention/deletion status is recorded. Raw recordings are not assumed or stored by default. Recruiter/admin role checks, payload caps, timestamp validation, idempotency keys, and audit rationale are required for sensitive writes.

## Rollout and validation

Set `HIRING_PIPELINE_V2_ENABLED=true` for the ordered flow. The migration must run against the fresh PostgreSQL schema before enabling recruiter policy editing. New applications use the explicit states; legacy applications continue through compatibility states until closed or explicitly overridden. Validation covers backend state and policy tests, frontend tests/build, migration compilation, API import checks, and a scripted end-to-end path: application → assessment → proctor review → AI interview → AI approval → human interview → final decision.
