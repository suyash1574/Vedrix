"""End-to-end hiring workflow API for candidate intake through recruiter decision."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.db.session import get_session
from app.models.candidate_workflow import CandidateWorkflow
from app.models.hiring_workflow import (
    AssessmentAssignment,
    AssessmentAttempt,
    CandidateApplication,
    ManualInterviewEntry,
    WorkflowAuditEvent,
)
from app.models.interview import DriveInviteToken, InterviewSession, JobDrive
from app.models.profile import HRProfile, StudentProfile
from app.models.user import User
from app.schemas.hr import (
    AssessmentAssignmentCreate,
    AssessmentReviewRequest,
    CandidateApplicationCreate,
    ManualInterviewEntryCreate,
    WorkflowDecisionRequest,
    WorkflowOverrideRequest,
)
from app.services.hiring_workflow_service import (
    get_or_create_workflow,
    record_workflow_event,
    score_application_against_drive,
)
from app.services.orchestrator_service import InvalidTransitionError, OrchestratorService, WORKFLOW_TRANSITIONS

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_drive_for_hr(db: AsyncSession, drive_id: int, current_hr: User) -> JobDrive:
    profile = (await db.execute(select(HRProfile).where(HRProfile.user_id == current_hr.id))).scalars().first()
    if not profile:
        raise HTTPException(status_code=400, detail="HR profile not found")
    drive = (await db.execute(select(JobDrive).where(JobDrive.id == drive_id, JobDrive.hr_id == profile.id))).scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Job drive not found")
    return drive


async def _get_application_for_drive(db: AsyncSession, drive_id: int, application_id: int) -> CandidateApplication:
    application = (await db.execute(
        select(CandidateApplication).where(
            CandidateApplication.id == application_id,
            CandidateApplication.job_drive_id == drive_id,
        )
    )).scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("/apply/{token}")
async def get_application_form(token: str, db: AsyncSession = Depends(get_session)) -> Any:
    invite = (await db.execute(select(DriveInviteToken).where(DriveInviteToken.token == token))).scalars().first()
    if not invite or invite.is_used or (invite.expires_at and invite.expires_at < _now()):
        raise HTTPException(status_code=404, detail="Application link is invalid or expired")
    drive = (await db.execute(select(JobDrive).where(JobDrive.id == invite.drive_id, JobDrive.is_active == True))).scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Job drive is not active")
    default_fields = [
        {"name": "first_name", "label": "First name", "required": True},
        {"name": "last_name", "label": "Last name", "required": True},
        {"name": "phone", "label": "Phone", "required": False},
        {"name": "resume_text", "label": "Resume or experience", "required": True},
        {"name": "portfolio_url", "label": "Portfolio URL", "required": False},
        {"name": "availability", "label": "Availability", "required": False},
    ]
    return {
        "token": token,
        "drive": {
            "id": drive.id,
            "title": drive.title,
            "description": drive.description,
            "job_role": drive.job_role,
            "experience_required": drive.experience_required,
            "skills_required": drive.skills_required,
            "application_form_config": drive.application_form_config or {},
            "assessment_policy": drive.assessment_policy or {},
            "workflow_policy": drive.workflow_policy or {},
        },
        "candidate_email": invite.candidate_email,
        "form_fields": drive.application_form_config.get("fields", default_fields) if isinstance(drive.application_form_config, dict) else default_fields,
        "consent_required": True,
    }


@router.post("/apply/{token}")
async def submit_application(token: str, body: CandidateApplicationCreate, db: AsyncSession = Depends(get_session)) -> Any:
    invite = (await db.execute(select(DriveInviteToken).where(DriveInviteToken.token == token))).scalars().first()
    if not invite or invite.is_used or (invite.expires_at and invite.expires_at < _now()):
        raise HTTPException(status_code=404, detail="Application link is invalid or expired")
    if not body.candidate_email:
        raise HTTPException(status_code=422, detail="candidate_email is required for an application link")
    if invite.candidate_email and invite.candidate_email.lower() != str(body.candidate_email).lower():
        raise HTTPException(status_code=403, detail="This application link is assigned to another email")
    if not body.consent_granted:
        raise HTTPException(status_code=400, detail="Candidate consent is required")

    drive = (await db.execute(select(JobDrive).where(JobDrive.id == invite.drive_id, JobDrive.is_active == True))).scalars().first()
    if not drive:
        raise HTTPException(status_code=404, detail="Job drive is not active")

    candidate = (await db.execute(select(User).where(User.email == str(body.candidate_email)))).scalars().first()
    if not candidate:
        username = f"candidate_{uuid.uuid4().hex[:12]}"
        candidate = User(
            email=str(body.candidate_email),
            username=username,
            password_hash=security.get_password_hash(uuid.uuid4().hex),
            user_type="student",
            first_name=body.candidate_first_name or str(body.candidate_email).split("@")[0],
            last_name=body.candidate_last_name or "",
            is_active=True,
        )
        db.add(candidate)
        await db.flush()
        db.add(StudentProfile(user_id=candidate.id))
    else:
        if body.candidate_first_name:
            candidate.first_name = body.candidate_first_name
        if body.candidate_last_name:
            candidate.last_name = body.candidate_last_name

    application = (await db.execute(select(CandidateApplication).where(
        CandidateApplication.candidate_id == candidate.id,
        CandidateApplication.job_drive_id == drive.id,
    ))).scalars().first()
    if not application:
        application = CandidateApplication(
            candidate_id=candidate.id,
            job_drive_id=drive.id,
            source=body.source,
            form_data=body.form_data,
            resume_text=body.resume_text,
            resume_url=body.resume_url,
            consent_granted=True,
            consent_at=_now(),
            status="submitted",
        )
        db.add(application)
        await db.flush()
    else:
        application.form_data = body.form_data
        application.resume_text = body.resume_text
        application.resume_url = body.resume_url
        application.source = body.source
        application.consent_granted = True
        application.consent_at = application.consent_at or _now()
        application.updated_at = _now()

    match = score_application_against_drive(drive, application)
    application.match_score = match["score"]
    application.match_breakdown = match
    workflow = await get_or_create_workflow(db, candidate_id=candidate.id, job_drive_id=drive.id, initial_state="screening")
    if workflow.current_state == "invited":
        previous = workflow.current_state
        workflow.current_state = "screening"
        workflow.updated_at = _now()
        workflow.transition_history = [*(workflow.transition_history or []), {
            "from_state": previous,
            "to_state": "screening",
            "trigger": "apply",
            "actor_id": candidate.id,
            "timestamp": _now().isoformat(),
        }]
    await record_workflow_event(
        db,
        action="application_submitted",
        entity_type="candidate_application",
        actor_id=candidate.id,
        actor_type="candidate",
        job_drive_id=drive.id,
        candidate_id=candidate.id,
        application_id=application.id,
        entity_id=application.id,
        to_state=workflow.current_state,
        payload={"source": body.source, "match_score": match["score"]},
    )
    invite.is_used = True
    await db.commit()
    await db.refresh(application)
    return {
        "application_id": application.id,
        "candidate_id": candidate.id,
        "status": application.status,
        "match_score": application.match_score,
        "next_step": "Your application has been received. The recruiter will review it.",
    }


@router.get("/drives/{drive_id}/applications")
async def list_applications(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    rows = (await db.execute(
        select(CandidateApplication, User, CandidateWorkflow)
        .join(User, User.id == CandidateApplication.candidate_id)
        .outerjoin(CandidateWorkflow, (CandidateWorkflow.candidate_id == CandidateApplication.candidate_id) & (CandidateWorkflow.job_drive_id == drive_id))
        .where(CandidateApplication.job_drive_id == drive_id)
        .order_by(CandidateApplication.updated_at.desc())
    )).all()
    return [{
        "id": application.id,
        "candidate_id": application.candidate_id,
        "candidate_name": f"{candidate.first_name} {candidate.last_name}".strip(),
        "candidate_email": candidate.email,
        "status": application.status,
        "workflow_state": workflow.current_state if workflow else None,
        "match_score": application.match_score,
        "match_breakdown": application.match_breakdown,
        "form_data": application.form_data,
        "resume_url": application.resume_url,
        "consent_granted": application.consent_granted,
        "submitted_at": application.submitted_at,
        "updated_at": application.updated_at,
    } for application, candidate, workflow in rows]


@router.post("/drives/{drive_id}/applications/{application_id}/assessment")
async def assign_assessment(
    drive_id: int,
    application_id: int,
    body: AssessmentAssignmentCreate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    application = await _get_application_for_drive(db, drive_id, application_id)
    if body.application_id != application_id:
        raise HTTPException(status_code=400, detail="application_id does not match route")
    assignment = AssessmentAssignment(
        application_id=application.id,
        job_drive_id=drive_id,
        candidate_id=application.candidate_id,
        title=body.title,
        assessment_type=body.assessment_type,
        instructions=body.instructions,
        config=body.config,
        duration_minutes=body.duration_minutes,
        passing_score=body.passing_score,
        required=body.required,
        proctoring_enabled=body.proctoring_enabled,
        assigned_by=current_hr.id,
        available_from=body.available_from,
        due_at=body.due_at,
    )
    db.add(assignment)
    await db.flush()
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive_id)
    if workflow.current_state == "screening":
        previous = workflow.current_state
        workflow.current_state = "assessment_assigned"
        workflow.updated_at = _now()
        workflow.transition_history = [*(workflow.transition_history or []), {
            "from_state": previous, "to_state": "assessment_assigned", "trigger": "assign_assessment",
            "actor_id": current_hr.id, "timestamp": _now().isoformat(),
        }]
    await record_workflow_event(
        db, action="assessment_assigned", entity_type="assessment_assignment", actor_id=current_hr.id,
        actor_type="recruiter", job_drive_id=drive_id, candidate_id=application.candidate_id,
        application_id=application.id, entity_id=assignment.id, to_state=workflow.current_state,
        rationale="Recruiter assigned online assessment", payload={"proctoring_enabled": body.proctoring_enabled},
    )
    await db.commit()
    await db.refresh(assignment)
    return assignment


@router.post("/assignments/{assignment_id}/attempt")
async def start_assessment_attempt(
    assignment_id: int,
    db: AsyncSession = Depends(get_session),
    current_candidate: User = Depends(deps.get_current_user),
) -> Any:
    assignment = (await db.execute(select(AssessmentAssignment).where(AssessmentAssignment.id == assignment_id))).scalars().first()
    if not assignment or assignment.candidate_id != current_candidate.id:
        raise HTTPException(status_code=404, detail="Assessment assignment not found")
    if assignment.status in {"cancelled", "completed"}:
        raise HTTPException(status_code=400, detail="Assessment is not available")
    existing = (await db.execute(select(AssessmentAttempt).where(
        AssessmentAttempt.assignment_id == assignment.id,
        AssessmentAttempt.candidate_id == current_candidate.id,
        AssessmentAttempt.status.in_(["started", "submitted"]),
    ).order_by(AssessmentAttempt.attempt_number.desc()))).scalars().first()
    if existing and existing.status == "started":
        return existing
    attempt_count = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.assignment_id == assignment.id))).scalars().all()
    attempt = AssessmentAttempt(
        assignment_id=assignment.id,
        application_id=assignment.application_id,
        candidate_id=current_candidate.id,
        attempt_number=len(attempt_count) + 1,
        status="started",
        started_at=_now(),
    )
    db.add(attempt)
    assignment.status = "in_progress"
    workflow = await get_or_create_workflow(db, candidate_id=current_candidate.id, job_drive_id=assignment.job_drive_id)
    if workflow.current_state == "assessment_assigned":
        workflow.current_state = "assessment_in_progress"
        workflow.updated_at = _now()
    await record_workflow_event(
        db, action="assessment_started", entity_type="assessment_attempt", actor_id=current_candidate.id,
        actor_type="candidate", job_drive_id=assignment.job_drive_id, candidate_id=current_candidate.id,
        application_id=assignment.application_id, entity_id=attempt.id, to_state=workflow.current_state,
    )
    await db.commit()
    await db.refresh(attempt)
    return attempt


@router.post("/attempts/{attempt_id}/submit")
async def submit_assessment_attempt(
    attempt_id: int,
    body: dict,
    db: AsyncSession = Depends(get_session),
    current_candidate: User = Depends(deps.get_current_user),
) -> Any:
    attempt = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id, AssessmentAttempt.candidate_id == current_candidate.id))).scalars().first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    if attempt.status != "started":
        raise HTTPException(status_code=400, detail="Assessment attempt is not active")
    answers = body.get("answers")
    if not isinstance(answers, dict):
        raise HTTPException(status_code=422, detail="answers must be an object")
    attempt.answers = answers
    attempt.score = float(body["score"]) if body.get("score") is not None else None
    attempt.result = body.get("result")
    attempt.status = "submitted"
    attempt.submitted_at = _now()
    attempt.updated_at = _now()
    assignment = (await db.execute(select(AssessmentAssignment).where(AssessmentAssignment.id == attempt.assignment_id))).scalars().first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assessment assignment not found")
    assignment.status = "submitted"
    workflow = await get_or_create_workflow(db, candidate_id=current_candidate.id, job_drive_id=assignment.job_drive_id)
    if workflow.current_state == "assessment_in_progress":
        workflow.current_state = "assessment_review"
        workflow.updated_at = _now()
    await record_workflow_event(
        db, action="assessment_submitted", entity_type="assessment_attempt", actor_id=current_candidate.id,
        actor_type="candidate", job_drive_id=assignment.job_drive_id,
        candidate_id=current_candidate.id, application_id=attempt.application_id, entity_id=attempt.id,
        to_state=workflow.current_state, payload={"score": attempt.score},
    )
    await db.commit()
    return {"attempt_id": attempt.id, "status": attempt.status, "score": attempt.score}


@router.post("/attempts/{attempt_id}/proctor-event")
async def record_assessment_proctor_event(
    attempt_id: int,
    body: dict,
    db: AsyncSession = Depends(get_session),
    current_candidate: User = Depends(deps.get_current_user),
) -> Any:
    attempt = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id, AssessmentAttempt.candidate_id == current_candidate.id))).scalars().first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    assignment = (await db.execute(select(AssessmentAssignment).where(AssessmentAssignment.id == attempt.assignment_id))).scalars().first()
    if not assignment or not assignment.proctoring_enabled:
        raise HTTPException(status_code=400, detail="Proctoring is not enabled for this assessment")
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == attempt.application_id))).scalars().first()
    if not application or not application.consent_granted:
        raise HTTPException(status_code=403, detail="Candidate proctoring consent is required")
    summary = dict(attempt.proctor_summary or {})
    event_type = str(body.get("event_type") or "unknown")
    events = list(summary.get("events") or [])
    events.append({"event_type": event_type, "payload": body.get("payload") or {}, "at": _now().isoformat()})
    summary["events"] = events[-200:]
    summary["counts"] = {**(summary.get("counts") or {}), event_type: int((summary.get("counts") or {}).get(event_type, 0)) + 1}
    risk_events = {"tab_switch", "paste_detected", "multiple_faces", "no_face", "gaze_deviation", "anomalous_typing"}
    risk_count = sum(int(value) for key, value in summary["counts"].items() if key in risk_events)
    summary["risk_score"] = min(100, risk_count * 10)
    summary["risk_level"] = "high" if risk_count >= 5 else "medium" if risk_count >= 2 else "low"
    attempt.proctor_summary = summary
    attempt.updated_at = _now()
    await record_workflow_event(
        db, action="assessment_proctor_event", entity_type="assessment_attempt", actor_id=current_candidate.id,
        actor_type="candidate", candidate_id=current_candidate.id, application_id=attempt.application_id,
        entity_id=attempt.id, payload={"event_type": event_type},
    )
    await db.commit()
    return {"attempt_id": attempt.id, "risk_level": summary["risk_level"], "risk_score": summary["risk_score"]}


@router.post("/drives/{drive_id}/assessment-attempts/{attempt_id}/review")
async def review_assessment_attempt(
    drive_id: int,
    attempt_id: int,
    body: AssessmentReviewRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    attempt = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.id == attempt_id))).scalars().first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    allowed = {"not_reviewed", "cleared", "suspected", "confirmed"}
    if body.cheating_status not in allowed:
        raise HTTPException(status_code=422, detail=f"cheating_status must be one of {sorted(allowed)}")
    attempt.cheating_status = body.cheating_status
    attempt.reviewer_id = current_hr.id
    attempt.reviewer_notes = body.reviewer_notes
    attempt.reviewed_at = _now()
    attempt.updated_at = _now()
    assignment = (await db.execute(select(AssessmentAssignment).where(AssessmentAssignment.id == attempt.assignment_id))).scalars().first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assessment assignment not found")
    workflow = await get_or_create_workflow(db, candidate_id=attempt.candidate_id, job_drive_id=drive_id)
    trigger = "confirm_cheat" if body.cheating_status == "confirmed" else "flag_cheat" if body.cheating_status == "suspected" else "pass"
    if workflow.current_state == "assessment_review" and trigger in WORKFLOW_TRANSITIONS[workflow.current_state]:
        previous = workflow.current_state
        workflow.current_state = WORKFLOW_TRANSITIONS[workflow.current_state][trigger]
        workflow.updated_at = _now()
        workflow.transition_history = [*(workflow.transition_history or []), {
            "from_state": previous, "to_state": workflow.current_state, "trigger": trigger,
            "actor_id": current_hr.id, "timestamp": _now().isoformat(),
        }]
    await record_workflow_event(
        db, action="assessment_reviewed", entity_type="assessment_attempt", actor_id=current_hr.id,
        actor_type="recruiter", job_drive_id=drive_id, candidate_id=attempt.candidate_id,
        application_id=attempt.application_id, entity_id=attempt.id, to_state=workflow.current_state,
        rationale=body.rationale or body.reviewer_notes, payload={"cheating_status": body.cheating_status},
    )
    await db.commit()
    return {"attempt_id": attempt.id, "cheating_status": attempt.cheating_status, "workflow_state": workflow.current_state}


@router.post("/drives/{drive_id}/applications/{application_id}/manual-interview")
async def create_manual_interview_entry(
    drive_id: int,
    application_id: int,
    body: ManualInterviewEntryCreate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    application = await _get_application_for_drive(db, drive_id, application_id)
    entry = ManualInterviewEntry(
        application_id=application.id,
        candidate_id=application.candidate_id,
        job_drive_id=drive_id,
        interviewer_id=current_hr.id,
        interview_type=body.interview_type,
        scheduled_at=body.scheduled_at,
        occurred_at=body.occurred_at or _now(),
        duration_minutes=body.duration_minutes,
        rubric=body.rubric,
        notes=body.notes,
        score=body.score,
        recommendation=body.recommendation,
    )
    db.add(entry)
    await db.flush()
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive_id)
    if workflow.current_state in {"screening", "assessment_review", "cheat_review", "scheduled", "interview_scheduled", "evaluated"}:
        previous = workflow.current_state
        workflow.current_state = "manual_interview"
        workflow.updated_at = _now()
        workflow.transition_history = [*(workflow.transition_history or []), {
            "from_state": previous, "to_state": "manual_interview", "trigger": "manual_interview",
            "actor_id": current_hr.id, "timestamp": _now().isoformat(),
        }]
    await record_workflow_event(
        db, action="manual_interview_recorded", entity_type="manual_interview_entry", actor_id=current_hr.id,
        actor_type="recruiter", job_drive_id=drive_id, candidate_id=application.candidate_id,
        application_id=application.id, entity_id=entry.id, to_state=workflow.current_state,
        rationale=body.recommendation, payload={"score": body.score, "interview_type": body.interview_type},
    )
    await db.commit()
    await db.refresh(entry)
    return entry


@router.post("/drives/{drive_id}/workflow/{candidate_id}/override")
async def override_workflow_state(
    drive_id: int,
    candidate_id: int,
    body: WorkflowOverrideRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    if body.target_state not in WORKFLOW_TRANSITIONS:
        raise HTTPException(status_code=422, detail="Unknown workflow state")
    workflow = await get_or_create_workflow(db, candidate_id=candidate_id, job_drive_id=drive_id)
    previous = workflow.current_state
    workflow.current_state = body.target_state
    workflow.updated_at = _now()
    workflow.transition_history = [*(workflow.transition_history or []), {
        "from_state": previous, "to_state": body.target_state, "trigger": "recruiter_override",
        "actor_id": current_hr.id, "rationale": body.rationale, "timestamp": _now().isoformat(),
    }]
    await record_workflow_event(
        db, action="workflow_override", entity_type="candidate_workflow", actor_id=current_hr.id,
        actor_type="recruiter", job_drive_id=drive_id, candidate_id=candidate_id,
        entity_id=workflow.id, from_state=previous, to_state=body.target_state,
        rationale=body.rationale,
    )
    await db.commit()
    return {"candidate_id": candidate_id, "job_drive_id": drive_id, "current_state": workflow.current_state, "rationale": body.rationale}


@router.post("/drives/{drive_id}/workflow/{candidate_id}/decision")
async def record_workflow_decision(
    drive_id: int,
    candidate_id: int,
    body: WorkflowDecisionRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    if body.decision not in {"hired", "rejected", "withdrawn", "on_hold"}:
        raise HTTPException(status_code=422, detail="Unsupported decision")
    workflow = await get_or_create_workflow(db, candidate_id=candidate_id, job_drive_id=drive_id)
    workflow.decision = body.decision if body.decision != "on_hold" else None
    if body.decision in {"hired", "rejected", "withdrawn"}:
        workflow.current_state = "decided"
        workflow.decided_by = current_hr.id
        workflow.decided_at = _now()
    workflow.updated_at = _now()
    await record_workflow_event(
        db, action="recruiter_decision", entity_type="candidate_workflow", actor_id=current_hr.id,
        actor_type="recruiter", job_drive_id=drive_id, candidate_id=candidate_id,
        entity_id=workflow.id, to_state=workflow.current_state, rationale=body.rationale,
        payload={"decision": body.decision},
    )
    await db.commit()
    return {"candidate_id": candidate_id, "decision": body.decision, "current_state": workflow.current_state}


@router.get("/drives/{drive_id}/applications/{application_id}/report")
async def get_application_report(
    drive_id: int,
    application_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    application = await _get_application_for_drive(db, drive_id, application_id)
    workflow = (await db.execute(select(CandidateWorkflow).where(
        CandidateWorkflow.candidate_id == application.candidate_id,
        CandidateWorkflow.job_drive_id == drive_id,
    ))).scalars().first()
    assignments = (await db.execute(select(AssessmentAssignment).where(AssessmentAssignment.application_id == application.id))).scalars().all()
    attempts = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.application_id == application.id).order_by(AssessmentAttempt.created_at))).scalars().all()
    manual_entries = (await db.execute(select(ManualInterviewEntry).where(ManualInterviewEntry.application_id == application.id).order_by(ManualInterviewEntry.occurred_at))).scalars().all()
    sessions = (await db.execute(select(InterviewSession).where(
        InterviewSession.candidate_id == application.candidate_id,
        InterviewSession.job_drive_id == drive_id,
    ).order_by(InterviewSession.created_at))).scalars().all()
    audit = (await db.execute(select(WorkflowAuditEvent).where(
        WorkflowAuditEvent.application_id == application.id,
    ).order_by(WorkflowAuditEvent.occurred_at))).scalars().all()
    return {
        "application": application,
        "workflow": workflow,
        "assessments": [{"assignment": assignment, "attempts": [attempt for attempt in attempts if attempt.assignment_id == assignment.id]} for assignment in assignments],
        "manual_interviews": manual_entries,
        "ai_interviews": sessions,
        "audit": audit,
        "review_guidance": "Proctoring signals are evidence for recruiter review and must not be treated as an automatic rejection without a recorded human decision.",
    }


@router.get("/drives/{drive_id}/audit")
async def get_workflow_audit(
    drive_id: int,
    candidate_id: Optional[int] = None,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    query = select(WorkflowAuditEvent).where(WorkflowAuditEvent.job_drive_id == drive_id).order_by(WorkflowAuditEvent.occurred_at.desc())
    if candidate_id is not None:
        query = query.where(WorkflowAuditEvent.candidate_id == candidate_id)
    events = (await db.execute(query.limit(500))).scalars().all()
    return events
