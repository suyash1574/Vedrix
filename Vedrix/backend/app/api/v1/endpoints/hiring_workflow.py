"""End-to-end hiring workflow API for candidate intake through recruiter decision."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core import security
from app.core.config import settings
from app.db.session import get_session
from app.models.candidate_workflow import CandidateWorkflow
from app.models.hiring_workflow import (
    AssessmentAssignment,
    AssessmentAttempt,
    CandidateApplication,
    ManualInterviewEntry,
    WorkflowAuditEvent,
)
from app.models.pipeline import (
    AIInterviewStageReview,
    AssessmentDefinition,
    AssessmentQuestion,
    AssessmentResponse,
    HiringPipelineStageRun,
    HumanInterviewSchedule,
    ProctorEvidenceEvent,
)
from app.models.interview import DriveInviteToken, InterviewSession, JobDrive
from app.models.profile import HRProfile, StudentProfile
from app.models.user import User
from app.schemas.hr import (
    AssessmentAssignmentCreate,
    AssessmentDefinitionCreate,
    AssessmentResponseUpsert,
    AssessmentReviewRequest,
    AIInterviewStageReviewRequest,
    AIInterviewStageScheduleRequest,
    CandidateApplicationCreate,
    HumanInterviewScheduleRequest,
    HumanInterviewSubmitRequest,
    HiringPipelinePolicy,
    ManualInterviewEntryCreate,
    PipelineDecisionRequest,
    PipelineOverrideRequest,
    PipelinePolicyUpdate,
    ProctorEvidenceEventCreate,
    WorkflowDecisionRequest,
    WorkflowOverrideRequest,
)
from app.services.hiring_workflow_service import (
    assert_human_stage_gate,
    get_or_create_stage_run,
    get_or_create_workflow,
    normalize_pipeline_policy,
    policy_version,
    record_workflow_event,
    score_application_against_drive,
    state_for_stage,
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
    try:
        drive_policy = normalize_pipeline_policy(drive.workflow_policy) if settings.HIRING_PIPELINE_V2_ENABLED else {}
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid hiring pipeline policy: {exc}") from exc

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
            proctoring_consent_version=drive_policy.get("proctor_consent_version") if drive_policy else None,
            workflow_policy_snapshot=drive_policy or None,
            workflow_policy_version=policy_version(drive) if drive_policy else 1,
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
        application.proctoring_consent_version = application.proctoring_consent_version or (drive_policy.get("proctor_consent_version") if drive_policy else None)
        application.workflow_policy_snapshot = application.workflow_policy_snapshot or (drive_policy or None)
        application.workflow_policy_version = application.workflow_policy_version or (policy_version(drive) if drive_policy else 1)
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
        stage_key="screening",
        policy_version_value=application.workflow_policy_version,
        source="candidate_application",
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
        definition_id=body.definition_id,
        policy_version=application.workflow_policy_version or policy_version(await _get_drive_for_hr(db, drive_id, current_hr)),
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
    drive = await _get_drive_for_hr(db, drive_id, current_hr)
    policy = normalize_pipeline_policy(application.workflow_policy_snapshot or drive.workflow_policy)
    stage = await get_or_create_stage_run(
        db,
        application=application,
        drive=drive,
        stage_key="assessment",
        required=body.required,
        sequence_number=policy["stage_order"].index("assessment") + 1,
        status="scheduled",
        due_at=body.due_at,
        source="recruiter",
        related_entity_type="assessment_assignment",
        related_entity_id=assignment.id,
    )
    await record_workflow_event(
        db, action="assessment_assigned", entity_type="assessment_assignment", actor_id=current_hr.id,
        actor_type="recruiter", job_drive_id=drive_id, candidate_id=application.candidate_id,
        application_id=application.id, entity_id=assignment.id, to_state=workflow.current_state,
        rationale="Recruiter assigned online assessment", payload={"proctoring_enabled": body.proctoring_enabled},
        stage_key="assessment", policy_version_value=assignment.policy_version, source="assessment_stage",
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
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == assignment.application_id))).scalars().first()
    drive = (await db.execute(select(JobDrive).where(JobDrive.id == assignment.job_drive_id))).scalars().first()
    policy = normalize_pipeline_policy((application.workflow_policy_snapshot if application else None) or (drive.workflow_policy if drive else None))
    existing = (await db.execute(select(AssessmentAttempt).where(
        AssessmentAttempt.assignment_id == assignment.id,
        AssessmentAttempt.candidate_id == current_candidate.id,
        AssessmentAttempt.status.in_(["started", "submitted"]),
    ).order_by(AssessmentAttempt.attempt_number.desc()))).scalars().first()
    if existing and existing.status == "started":
        return existing
    attempt_count = (await db.execute(select(AssessmentAttempt).where(AssessmentAttempt.assignment_id == assignment.id))).scalars().all()
    if len(attempt_count) >= int(policy["assessment_allowed_attempts"]):
        raise HTTPException(status_code=409, detail="Assessment attempt limit has been reached")
    attempt = AssessmentAttempt(
        assignment_id=assignment.id,
        application_id=assignment.application_id,
        candidate_id=current_candidate.id,
        attempt_number=len(attempt_count) + 1,
        status="started",
        started_at=_now(),
        proctoring_consent_version=application.proctoring_consent_version if application else policy["proctor_consent_version"],
        correlation_id=str(uuid.uuid4()),
    )
    db.add(attempt)
    assignment.status = "in_progress"
    workflow = await get_or_create_workflow(db, candidate_id=current_candidate.id, job_drive_id=assignment.job_drive_id)
    if workflow.current_state == "assessment_assigned":
        workflow.current_state = "assessment_in_progress"
        workflow.updated_at = _now()
    stage = await _get_stage_run_for_application(db, assignment.application_id, "assessment")
    if stage:
        stage.status = "in_progress"
        stage.started_at = stage.started_at or _now()
        stage.attempt_number = attempt.attempt_number
        stage.related_entity_type = "assessment_attempt"
        stage.related_entity_id = attempt.id
    await record_workflow_event(
        db, action="assessment_started", entity_type="assessment_attempt", actor_id=current_candidate.id,
        actor_type="candidate", job_drive_id=assignment.job_drive_id, candidate_id=current_candidate.id,
        application_id=assignment.application_id, entity_id=attempt.id, to_state=workflow.current_state,
        stage_key="assessment", correlation_id=attempt.correlation_id,
        policy_version_value=assignment.policy_version, source="assessment_client",
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
    stage = await _get_stage_run_for_application(db, attempt.application_id, "assessment")
    if stage:
        stage.status = "needs_review"
        stage.completed_at = _now()
        stage.outcome = attempt.result or "submitted"
        stage.score = attempt.score
        stage.attempt_number = attempt.attempt_number
    await record_workflow_event(
        db, action="assessment_submitted", entity_type="assessment_attempt", actor_id=current_candidate.id,
        actor_type="candidate", job_drive_id=assignment.job_drive_id,
        candidate_id=current_candidate.id, application_id=attempt.application_id, entity_id=attempt.id,
        to_state=workflow.current_state, payload={"score": attempt.score},
        stage_key="assessment", correlation_id=attempt.correlation_id,
        policy_version_value=assignment.policy_version, source="assessment_client",
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
    drive = await _get_drive_for_hr(db, drive_id, current_hr)
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
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == attempt.application_id))).scalars().first()
    workflow = await get_or_create_workflow(db, candidate_id=attempt.candidate_id, job_drive_id=drive_id)
    policy = normalize_pipeline_policy((application.workflow_policy_snapshot if application else None) or drive.workflow_policy)
    is_v2 = bool(application and application.workflow_policy_snapshot)
    target_state = workflow.current_state
    trigger = "review"
    if body.cheating_status == "confirmed":
        target_state, trigger = "decided", "confirm_cheat"
    elif body.cheating_status == "suspected":
        target_state, trigger = "cheat_review", "flag_cheat"
    elif body.cheating_status == "cleared" or (body.cheating_status == "not_reviewed" and not is_v2):
        if is_v2 and policy["ai_interview_enabled"]:
            target_state, trigger = "ai_interview_scheduled", "clear_to_ai"
        elif is_v2 and policy["human_interview_enabled"]:
            target_state, trigger = "human_interview_scheduled", "clear_to_human"
        else:
            target_state, trigger = "interview_scheduled", "pass"
    if target_state != workflow.current_state:
        await _set_pipeline_state(
            db,
            workflow=workflow,
            new_state=target_state,
            trigger=trigger,
            actor_id=current_hr.id,
            application=application,
            drive=drive,
            stage_key="assessment",
            rationale=body.rationale or body.reviewer_notes,
            payload={"cheating_status": body.cheating_status},
        )
    stage = await _get_stage_run_for_application(db, attempt.application_id, "assessment")
    if stage and body.cheating_status in {"cleared", "confirmed"}:
        stage.outcome = body.cheating_status
        stage.status = "completed" if body.cheating_status == "cleared" else "rejected"
        stage.completed_at = _now()
    await record_workflow_event(
        db, action="assessment_reviewed", entity_type="assessment_attempt", actor_id=current_hr.id,
        actor_type="recruiter", job_drive_id=drive_id, candidate_id=attempt.candidate_id,
        application_id=attempt.application_id, entity_id=attempt.id, to_state=workflow.current_state,
        rationale=body.rationale or body.reviewer_notes, payload={"cheating_status": body.cheating_status},
        stage_key="assessment", correlation_id=attempt.correlation_id,
        policy_version_value=assignment.policy_version, source="assessment_review",
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
    if application.workflow_policy_snapshot and workflow.current_state not in {"human_interview_scheduled", "human_interview", "final_review"}:
        raise HTTPException(status_code=409, detail="V2 manual interview entries require the AI-reviewed human-interview stage or an explicit override")
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
    stage_runs = (await db.execute(select(HiringPipelineStageRun).where(
        HiringPipelineStageRun.application_id == application.id,
    ).order_by(HiringPipelineStageRun.sequence_number, HiringPipelineStageRun.attempt_number))).scalars().all()
    attempt_ids = [attempt.id for attempt in attempts]
    proctor_evidence = []
    if attempt_ids:
        proctor_evidence = (await db.execute(select(ProctorEvidenceEvent).where(
            ProctorEvidenceEvent.attempt_id.in_(attempt_ids),
        ).order_by(ProctorEvidenceEvent.occurred_at))).scalars().all()
    ai_reviews = (await db.execute(select(AIInterviewStageReview).where(
        AIInterviewStageReview.application_id == application.id,
    ).order_by(AIInterviewStageReview.created_at))).scalars().all()
    human_schedules = (await db.execute(select(HumanInterviewSchedule).where(
        HumanInterviewSchedule.application_id == application.id,
    ).order_by(HumanInterviewSchedule.created_at))).scalars().all()
    audit = (await db.execute(select(WorkflowAuditEvent).where(
        WorkflowAuditEvent.application_id == application.id,
    ).order_by(WorkflowAuditEvent.occurred_at))).scalars().all()
    return {
        "application": application,
        "workflow": workflow,
        "policy": application.workflow_policy_snapshot,
        "stage_runs": stage_runs,
        "assessments": [{"assignment": assignment, "attempts": [attempt for attempt in attempts if attempt.assignment_id == assignment.id]} for assignment in assignments],
        "proctor_evidence": proctor_evidence,
        "manual_interviews": manual_entries,
        "ai_interviews": sessions,
        "ai_stage_reviews": ai_reviews,
        "human_schedules": human_schedules,
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


# ── Ordered pipeline V2 endpoints ─────────────────────────────────────────────


def _public_question(question: AssessmentQuestion) -> dict[str, Any]:
    return {
        "id": question.id,
        "question_key": question.question_key,
        "question_type": question.question_type,
        "prompt": question.prompt,
        "options": question.options,
        "points": question.points,
        "skill_tags": question.skill_tags,
        "coding_config": question.coding_config,
        "display_order": question.display_order,
        "version": question.version,
    }


async def _set_pipeline_state(
    db: AsyncSession,
    *,
    workflow: CandidateWorkflow,
    new_state: str,
    trigger: str,
    actor_id: Optional[int],
    application: Optional[CandidateApplication] = None,
    drive: Optional[JobDrive] = None,
    stage_key: Optional[str] = None,
    rationale: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
) -> CandidateWorkflow:
    previous = workflow.current_state
    workflow.current_state = new_state
    workflow.updated_at = _now()
    workflow.transition_history = [*(workflow.transition_history or []), {
        "from_state": previous,
        "to_state": new_state,
        "trigger": trigger,
        "actor_id": actor_id,
        "rationale": rationale,
        "timestamp": _now().isoformat(),
    }]
    await record_workflow_event(
        db,
        action=f"workflow_transition:{trigger}",
        entity_type="candidate_workflow",
        actor_id=actor_id,
        actor_type="recruiter" if actor_id else "system",
        job_drive_id=workflow.job_drive_id,
        candidate_id=workflow.candidate_id,
        application_id=application.id if application else None,
        entity_id=workflow.id,
        from_state=previous,
        to_state=new_state,
        rationale=rationale,
        payload=payload or {},
        stage_key=stage_key,
        policy_version_value=policy_version(drive) if drive else None,
        source="ordered_pipeline",
    )
    return workflow


async def _get_stage_run_for_application(
    db: AsyncSession,
    application_id: int,
    stage_key: str,
) -> Optional[HiringPipelineStageRun]:
    return (await db.execute(
        select(HiringPipelineStageRun).where(
            HiringPipelineStageRun.application_id == application_id,
            HiringPipelineStageRun.stage_key == stage_key,
        ).order_by(HiringPipelineStageRun.attempt_number.desc())
    )).scalars().first()


@router.get("/drives/{drive_id}/pipeline-policy")
async def get_pipeline_policy(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    drive = await _get_drive_for_hr(db, drive_id, current_hr)
    try:
        policy = normalize_pipeline_policy(drive.workflow_policy)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"drive_id": drive_id, "version": policy_version(drive), "policy": policy}


@router.put("/drives/{drive_id}/pipeline-policy")
async def update_pipeline_policy(
    drive_id: int,
    body: PipelinePolicyUpdate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    drive = await _get_drive_for_hr(db, drive_id, current_hr)
    try:
        policy = normalize_pipeline_policy(body.policy.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    drive.workflow_policy = policy
    drive.jd_version = int(drive.jd_version or 1) + 1
    drive.updated_at = _now()
    await record_workflow_event(
        db,
        action="pipeline_policy_updated",
        entity_type="job_drive",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive_id,
        entity_id=drive_id,
        rationale=body.rationale,
        payload={"policy": policy, "version": drive.jd_version},
        source="pipeline_policy",
    )
    await db.commit()
    return {"drive_id": drive_id, "version": drive.jd_version, "policy": policy}


@router.post("/drives/{drive_id}/assessments")
async def create_assessment_definition(
    drive_id: int,
    body: AssessmentDefinitionCreate,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    version = (await db.execute(
        select(func.coalesce(func.max(AssessmentDefinition.version), 0)).where(
            AssessmentDefinition.job_drive_id == drive_id
        )
    )).scalar_one() + 1
    definition = AssessmentDefinition(
        job_drive_id=drive_id,
        title=body.title,
        instructions=body.instructions,
        version=version,
        duration_minutes=body.duration_minutes,
        passing_score=body.passing_score,
        question_order_policy=body.question_order_policy,
        is_published=body.publish,
        created_by=current_hr.id,
    )
    db.add(definition)
    await db.flush()
    questions = []
    for index, item in enumerate(body.questions):
        question = AssessmentQuestion(
            assessment_definition_id=definition.id,
            question_key=str(item.get("question_key") or f"q{index + 1}"),
            question_type=str(item.get("question_type") or "text"),
            prompt=str(item.get("prompt") or ""),
            options=item.get("options"),
            expected_answer=item.get("expected_answer"),
            points=float(item.get("points") or 1),
            skill_tags=item.get("skill_tags"),
            coding_config=item.get("coding_config"),
            display_order=int(item.get("display_order", index)),
        )
        if not question.prompt:
            raise HTTPException(status_code=422, detail="Every assessment question needs a prompt")
        db.add(question)
        questions.append(question)
    await record_workflow_event(
        db,
        action="assessment_definition_created",
        entity_type="assessment_definition",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive_id,
        entity_id=definition.id,
        payload={"version": version, "question_count": len(questions), "published": body.publish},
        source="assessment_builder",
    )
    await db.commit()
    return {
        "id": definition.id,
        "job_drive_id": definition.job_drive_id,
        "title": definition.title,
        "version": definition.version,
        "duration_minutes": definition.duration_minutes,
        "passing_score": definition.passing_score,
        "question_order_policy": definition.question_order_policy,
        "is_published": definition.is_published,
        "questions": [_public_question(question) for question in questions],
    }


@router.get("/drives/{drive_id}/assessments")
async def list_assessment_definitions(
    drive_id: int,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    await _get_drive_for_hr(db, drive_id, current_hr)
    definitions = (await db.execute(
        select(AssessmentDefinition).where(AssessmentDefinition.job_drive_id == drive_id).order_by(AssessmentDefinition.version.desc())
    )).scalars().all()
    return definitions


@router.get("/applications/{application_id}/pipeline")
async def get_candidate_pipeline(
    application_id: int,
    db: AsyncSession = Depends(get_session),
    current_candidate: User = Depends(deps.get_current_user),
) -> Any:
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == application_id))).scalars().first()
    if not application or application.candidate_id != current_candidate.id:
        raise HTTPException(status_code=404, detail="Application not found")
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=application.job_drive_id)
    stages = (await db.execute(
        select(HiringPipelineStageRun).where(HiringPipelineStageRun.application_id == application.id).order_by(HiringPipelineStageRun.sequence_number, HiringPipelineStageRun.attempt_number)
    )).scalars().all()
    return {
        "application_id": application.id,
        "workflow_state": workflow.current_state,
        "policy_version": application.workflow_policy_version,
        "stages": stages,
        "privacy_notice": "Proctoring signals are reviewable evidence and are not automatic rejection decisions.",
    }


@router.post("/assignments/{assignment_id}/responses")
async def autosave_assessment_response(
    assignment_id: int,
    body: AssessmentResponseUpsert,
    db: AsyncSession = Depends(get_session),
    current_candidate: User = Depends(deps.get_current_user),
) -> Any:
    assignment = (await db.execute(select(AssessmentAssignment).where(AssessmentAssignment.id == assignment_id))).scalars().first()
    if not assignment or assignment.candidate_id != current_candidate.id:
        raise HTTPException(status_code=404, detail="Assessment assignment not found")
    attempt = (await db.execute(select(AssessmentAttempt).where(
        AssessmentAttempt.assignment_id == assignment.id,
        AssessmentAttempt.candidate_id == current_candidate.id,
        AssessmentAttempt.status == "started",
    ).order_by(AssessmentAttempt.attempt_number.desc()))).scalars().first()
    if not attempt:
        raise HTTPException(status_code=409, detail="Start an assessment attempt before saving responses")
    question = (await db.execute(select(AssessmentQuestion).where(AssessmentQuestion.id == body.question_id))).scalars().first()
    if not question:
        raise HTTPException(status_code=404, detail="Assessment question not found")
    if assignment.definition_id and question.assessment_definition_id != assignment.definition_id:
        raise HTTPException(status_code=400, detail="Question is not part of the assigned assessment")
    response = (await db.execute(select(AssessmentResponse).where(
        AssessmentResponse.attempt_id == attempt.id,
        AssessmentResponse.question_id == body.question_id,
        AssessmentResponse.question_version == body.question_version,
    ))).scalars().first()
    if response and response.finalized:
        return {"response_id": response.id, "finalized": True, "autosaved_at": response.autosaved_at}
    if not response:
        response = AssessmentResponse(
            attempt_id=attempt.id,
            question_id=body.question_id,
            question_version=body.question_version,
            idempotency_key=body.idempotency_key,
        )
        db.add(response)
    response.response_data = body.response_data
    response.idempotency_key = body.idempotency_key
    response.finalized = body.finalize
    response.autosaved_at = _now()
    response.updated_at = _now()
    await record_workflow_event(
        db,
        action="assessment_response_autosaved",
        entity_type="assessment_response",
        actor_id=current_candidate.id,
        actor_type="candidate",
        job_drive_id=assignment.job_drive_id,
        candidate_id=current_candidate.id,
        application_id=assignment.application_id,
        entity_id=response.id,
        stage_key="assessment",
        correlation_id=attempt.correlation_id,
        payload={"question_id": body.question_id, "finalized": body.finalize},
        source="assessment_client",
    )
    await db.commit()
    await db.refresh(response)
    return {"response_id": response.id, "finalized": response.finalized, "autosaved_at": response.autosaved_at}


@router.post("/attempts/{attempt_id}/events")
async def record_assessment_evidence_event(
    attempt_id: int,
    body: ProctorEvidenceEventCreate,
    db: AsyncSession = Depends(get_session),
    current_candidate: User = Depends(deps.get_current_user),
) -> Any:
    attempt = (await db.execute(select(AssessmentAttempt).where(
        AssessmentAttempt.id == attempt_id,
        AssessmentAttempt.candidate_id == current_candidate.id,
    ))).scalars().first()
    if not attempt:
        raise HTTPException(status_code=404, detail="Assessment attempt not found")
    assignment = (await db.execute(select(AssessmentAssignment).where(AssessmentAssignment.id == attempt.assignment_id))).scalars().first()
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == attempt.application_id))).scalars().first()
    if not assignment or not assignment.proctoring_enabled:
        raise HTTPException(status_code=400, detail="Proctoring is not enabled for this assessment")
    if not application or not application.consent_granted or not application.proctoring_consent_version:
        raise HTTPException(status_code=403, detail="Versioned candidate proctoring consent is required")
    allowed_events = {"tab_switch", "fullscreen_exit", "paste_detected", "multiple_faces", "no_face", "gaze_deviation", "anomalous_typing", "camera_denied", "microphone_denied"}
    if body.event_type not in allowed_events:
        raise HTTPException(status_code=422, detail="Unsupported proctor event type")
    if len(str(body.payload)) + len(str(body.client_metadata)) > 12000:
        raise HTTPException(status_code=413, detail="Proctor event payload is too large")
    recent_events = (await db.execute(select(func.count(ProctorEvidenceEvent.id)).where(
        ProctorEvidenceEvent.attempt_id == attempt.id,
        ProctorEvidenceEvent.created_at >= _now() - timedelta(seconds=60),
    ))).scalar_one()
    if recent_events >= 60:
        raise HTTPException(status_code=429, detail="Too many proctor events for this attempt")
    occurred_at = body.occurred_at or _now()
    if abs((_now() - occurred_at).total_seconds()) > 300:
        raise HTTPException(status_code=422, detail="Proctor event timestamp is outside the allowed clock skew")
    event = ProctorEvidenceEvent(
        attempt_id=attempt.id,
        candidate_id=current_candidate.id,
        event_type=body.event_type,
        occurred_at=occurred_at,
        client_metadata=body.client_metadata,
        evidence_uri=body.evidence_uri,
        confidence=body.confidence,
        consent_version=application.proctoring_consent_version,
        correlation_id=attempt.correlation_id or str(uuid.uuid4()),
        payload=body.payload,
    )
    db.add(event)
    summary = dict(attempt.proctor_summary or {})
    counts = dict(summary.get("counts") or {})
    counts[body.event_type] = int(counts.get(body.event_type, 0)) + 1
    risk_events = {"tab_switch", "fullscreen_exit", "paste_detected", "multiple_faces", "no_face", "gaze_deviation", "anomalous_typing"}
    risk_count = sum(int(value) for key, value in counts.items() if key in risk_events)
    summary["counts"] = counts
    summary["risk_score"] = min(100, risk_count * 10)
    summary["risk_level"] = "high" if risk_count >= 5 else "medium" if risk_count >= 2 else "low"
    attempt.proctor_summary = summary
    await record_workflow_event(
        db,
        action="assessment_proctor_event",
        entity_type="proctor_evidence_event",
        actor_id=current_candidate.id,
        actor_type="candidate",
        job_drive_id=assignment.job_drive_id,
        candidate_id=current_candidate.id,
        application_id=attempt.application_id,
        entity_id=event.id,
        stage_key="assessment",
        correlation_id=event.correlation_id,
        payload={"event_type": body.event_type, "risk_level": summary["risk_level"]},
        source="proctor_client",
    )
    await db.commit()
    await db.refresh(event)
    return {"event_id": event.id, "risk_level": summary["risk_level"], "risk_score": summary["risk_score"], "correlation_id": event.correlation_id}


@router.post("/applications/{application_id}/ai-interview")
async def schedule_ai_interview_stage(
    application_id: int,
    body: AIInterviewStageScheduleRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == application_id))).scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    drive = await _get_drive_for_hr(db, application.job_drive_id, current_hr)
    policy = normalize_pipeline_policy(application.workflow_policy_snapshot or drive.workflow_policy)
    if not policy["ai_interview_enabled"]:
        raise HTTPException(status_code=409, detail="AI interview is disabled for this hiring drive")
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive.id)
    is_v2 = bool(application.workflow_policy_snapshot)
    if is_v2 and workflow.current_state == "assessment_review":
        latest_attempt = (await db.execute(select(AssessmentAttempt).where(
            AssessmentAttempt.application_id == application.id,
        ).order_by(AssessmentAttempt.attempt_number.desc()))).scalars().first()
        if not latest_attempt or latest_attempt.cheating_status != "cleared":
            raise HTTPException(status_code=409, detail="Assessment and proctor review must be cleared before AI scheduling")
    allowed_ai_states = {"assessment_review", "interview_scheduled", "ai_interview_scheduled"}
    if not is_v2:
        allowed_ai_states.add("cheat_review")
    if workflow.current_state not in allowed_ai_states:
        raise HTTPException(status_code=409, detail=f"Candidate is not cleared for AI interview from state '{workflow.current_state}'")
    session = (await db.execute(select(InterviewSession).where(
        InterviewSession.candidate_id == application.candidate_id,
        InterviewSession.job_drive_id == drive.id,
        InterviewSession.session_type == "ai_interview",
        InterviewSession.status.in_(["scheduled", "in_progress", "completed"]),
    ).order_by(InterviewSession.created_at.desc()))).scalars().first()
    if not session:
        session = InterviewSession(
            candidate_id=application.candidate_id,
            job_drive_id=drive.id,
            session_type="ai_interview",
            status="scheduled",
            start_time=body.start_time,
            duration=body.duration_minutes or policy["ai_interview_time_limit_minutes"],
            workflow_state="ai_interview_scheduled",
        )
        db.add(session)
        await db.flush()
    stage = await get_or_create_stage_run(
        db,
        application=application,
        drive=drive,
        stage_key="ai_interview",
        required=policy["ai_interview_required"],
        sequence_number=policy["stage_order"].index("ai_interview") + 1,
        status="scheduled",
        source="recruiter",
        related_entity_type="interview_session",
        related_entity_id=session.id,
    )
    stage.related_entity_id = session.id
    stage.related_entity_type = "interview_session"
    stage.started_at = stage.started_at or _now()
    session.workflow_state = "ai_interview_scheduled"
    await _set_pipeline_state(
        db,
        workflow=workflow,
        new_state="ai_interview_scheduled",
        trigger="schedule_ai_interview",
        actor_id=current_hr.id,
        application=application,
        drive=drive,
        stage_key="ai_interview",
        rationale=body.rationale,
        payload={"session_id": session.id},
    )
    await record_workflow_event(
        db,
        action="ai_interview_scheduled",
        entity_type="interview_session",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        entity_id=session.id,
        stage_key="ai_interview",
        payload={"duration_minutes": session.duration},
        source="ai_interview_stage",
    )
    await db.commit()
    await db.refresh(session)
    return {"stage_run": stage, "session": session, "workflow_state": workflow.current_state}


@router.post("/applications/{application_id}/ai-interview/review")
async def review_ai_interview_stage(
    application_id: int,
    body: AIInterviewStageReviewRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == application_id))).scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    drive = await _get_drive_for_hr(db, application.job_drive_id, current_hr)
    session = (await db.execute(select(InterviewSession).where(
        InterviewSession.id == body.session_id,
        InterviewSession.candidate_id == application.candidate_id,
        InterviewSession.job_drive_id == drive.id,
    ))).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="AI interview session not found")
    if body.status in {"approved", "follow_up"} and session.status not in {"completed", "evaluated"}:
        raise HTTPException(status_code=409, detail="AI interview must be completed before recruiter review")
    stage = await _get_stage_run_for_application(db, application.id, "ai_interview")
    if not stage:
        raise HTTPException(status_code=409, detail="AI interview stage has not been scheduled")
    review = (await db.execute(select(AIInterviewStageReview).where(AIInterviewStageReview.interview_session_id == session.id))).scalars().first()
    if not review:
        review = AIInterviewStageReview(
            stage_run_id=stage.id,
            application_id=application.id,
            interview_session_id=session.id,
        )
        db.add(review)
    review.status = body.status
    review.confidence = body.confidence
    review.follow_up_request = body.follow_up_request
    review.approved_by = current_hr.id if body.status == "approved" else None
    review.approved_at = _now() if body.status == "approved" else None
    review.rationale = body.rationale
    stage.confidence = body.confidence
    stage.outcome = body.status
    stage.completed_at = _now() if body.status in {"approved", "rejected"} else None
    stage.status = "completed" if body.status in {"approved", "rejected"} else "needs_review"
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive.id)
    target_state = {
        "approved": "human_interview_scheduled",
        "follow_up": "ai_interview_scheduled",
        "rejected": "decided",
        "hold": "ai_interview_review",
    }[body.status]
    trigger = {"approved": "approve_human", "follow_up": "follow_up", "rejected": "reject", "hold": "hold"}[body.status]
    await _set_pipeline_state(
        db,
        workflow=workflow,
        new_state=target_state,
        trigger=trigger,
        actor_id=current_hr.id,
        application=application,
        drive=drive,
        stage_key="ai_interview",
        rationale=body.rationale,
        payload={"session_id": session.id, "confidence": body.confidence},
    )
    await record_workflow_event(
        db,
        action="ai_interview_reviewed",
        entity_type="ai_interview_stage_review",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        entity_id=review.id,
        stage_key="ai_interview",
        rationale=body.rationale,
        payload={"status": body.status, "confidence": body.confidence},
        source="ai_interview_review",
    )
    await db.commit()
    await db.refresh(review)
    return {"review": review, "workflow_state": workflow.current_state}


@router.post("/applications/{application_id}/human-interview")
async def schedule_human_interview_stage(
    application_id: int,
    body: HumanInterviewScheduleRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == application_id))).scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    drive = await _get_drive_for_hr(db, application.job_drive_id, current_hr)
    policy = normalize_pipeline_policy(application.workflow_policy_snapshot or drive.workflow_policy)
    if not policy["human_interview_enabled"]:
        raise HTTPException(status_code=409, detail="Human interview is disabled for this hiring drive")
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive.id)
    try:
        assert_human_stage_gate(workflow.current_state)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if application.workflow_policy_snapshot and workflow.current_state == "ai_interview_review":
        approved_review = (await db.execute(select(AIInterviewStageReview).where(
            AIInterviewStageReview.application_id == application.id,
            AIInterviewStageReview.status == "approved",
        ))).scalars().first()
        if not approved_review:
            raise HTTPException(status_code=409, detail="Recruiter AI approval is required before human scheduling")
    stage = await get_or_create_stage_run(
        db,
        application=application,
        drive=drive,
        stage_key="human_interview",
        required=policy["human_interview_required"],
        sequence_number=policy["stage_order"].index("human_interview") + 1,
        status="scheduled",
        source="recruiter",
    )
    schedule = HumanInterviewSchedule(
        stage_run_id=stage.id,
        application_id=application.id,
        candidate_id=application.candidate_id,
        job_drive_id=drive.id,
        interviewer_id=body.interviewer_id,
        interview_type=body.interview_type,
        scheduled_at=body.scheduled_at,
        timezone=body.timezone,
        meeting_location=body.meeting_location,
        meeting_link=body.meeting_link,
        rubric=body.rubric or policy["human_interview_rubric"],
    )
    db.add(schedule)
    await db.flush()
    stage.assigned_to = body.interviewer_id
    stage.related_entity_type = "human_interview_schedule"
    stage.related_entity_id = schedule.id
    await _set_pipeline_state(
        db,
        workflow=workflow,
        new_state="human_interview_scheduled",
        trigger="schedule_human_interview",
        actor_id=current_hr.id,
        application=application,
        drive=drive,
        stage_key="human_interview",
        rationale=body.rationale,
        payload={"schedule_id": schedule.id, "interviewer_id": body.interviewer_id},
    )
    await record_workflow_event(
        db,
        action="human_interview_scheduled",
        entity_type="human_interview_schedule",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        entity_id=schedule.id,
        stage_key="human_interview",
        rationale=body.rationale,
        payload={"interviewer_id": body.interviewer_id, "scheduled_at": body.scheduled_at.isoformat() if body.scheduled_at else None},
        source="human_interview_stage",
    )
    await db.commit()
    await db.refresh(schedule)
    return {"schedule": schedule, "workflow_state": workflow.current_state}


@router.post("/applications/{application_id}/human-interview/submit")
async def submit_human_interview_stage(
    application_id: int,
    body: HumanInterviewSubmitRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == application_id))).scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    drive = await _get_drive_for_hr(db, application.job_drive_id, current_hr)
    schedule = (await db.execute(select(HumanInterviewSchedule).where(
        HumanInterviewSchedule.id == body.schedule_id,
        HumanInterviewSchedule.application_id == application.id,
    ))).scalars().first()
    if not schedule:
        raise HTTPException(status_code=404, detail="Human interview schedule not found")
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive.id)
    if workflow.current_state not in {"human_interview_scheduled", "human_interview"}:
        raise HTTPException(status_code=409, detail="Human interview is not the current pipeline stage")
    entry = ManualInterviewEntry(
        application_id=application.id,
        candidate_id=application.candidate_id,
        job_drive_id=drive.id,
        interviewer_id=schedule.interviewer_id,
        interview_type=schedule.interview_type,
        scheduled_at=schedule.scheduled_at,
        occurred_at=body.occurred_at or _now(),
        duration_minutes=body.duration_minutes,
        rubric=schedule.rubric,
        notes={**(body.notes or {}), "evidence_links": body.evidence_links},
        score=body.score,
        recommendation=body.recommendation,
    )
    db.add(entry)
    await db.flush()
    schedule.manual_entry_id = entry.id
    schedule.status = "completed"
    stage = await _get_stage_run_for_application(db, application.id, "human_interview")
    if stage:
        stage.status = "completed"
        stage.outcome = body.recommendation or "submitted"
        stage.score = body.score
        stage.completed_at = _now()
        stage.related_entity_type = "manual_interview_entry"
        stage.related_entity_id = entry.id
    await _set_pipeline_state(
        db,
        workflow=workflow,
        new_state="final_review",
        trigger="submit_human_interview",
        actor_id=current_hr.id,
        application=application,
        drive=drive,
        stage_key="human_interview",
        rationale=body.recommendation,
        payload={"schedule_id": schedule.id, "entry_id": entry.id, "score": body.score},
    )
    await record_workflow_event(
        db,
        action="human_interview_submitted",
        entity_type="manual_interview_entry",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        entity_id=entry.id,
        stage_key="human_interview",
        rationale=body.recommendation,
        payload={"score": body.score, "recommendation": body.recommendation},
        source="human_interview_stage",
    )
    await db.commit()
    await db.refresh(entry)
    return {"entry": entry, "workflow_state": workflow.current_state}


@router.post("/applications/{application_id}/override-stage")
async def override_pipeline_stage(
    application_id: int,
    body: PipelineOverrideRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == application_id))).scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    drive = await _get_drive_for_hr(db, application.job_drive_id, current_hr)
    target_map = {
        "assessment": "assessment_assigned",
        "ai_interview": "ai_interview_scheduled",
        "human_interview": "human_interview_scheduled",
        "final_review": "final_review",
        "decided": "decided",
    }
    if body.target_stage not in target_map:
        raise HTTPException(status_code=422, detail="Unsupported pipeline target stage")
    if not body.rationale.strip():
        raise HTTPException(status_code=422, detail="A rationale is required for stage overrides")
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive.id)
    target_state = target_map[body.target_stage]
    await _set_pipeline_state(
        db,
        workflow=workflow,
        new_state=target_state,
        trigger="pipeline_override",
        actor_id=current_hr.id,
        application=application,
        drive=drive,
        stage_key=body.target_stage if body.target_stage in {"assessment", "ai_interview", "human_interview"} else None,
        rationale=body.rationale,
        payload={"bypassed_stages": body.bypassed_stages},
    )
    await record_workflow_event(
        db,
        action="pipeline_stage_override",
        entity_type="candidate_workflow",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        entity_id=workflow.id,
        to_state=target_state,
        rationale=body.rationale,
        payload={"target_stage": body.target_stage, "bypassed_stages": body.bypassed_stages},
        source="recruiter_override",
    )
    await db.commit()
    return {"application_id": application_id, "workflow_state": workflow.current_state, "rationale": body.rationale}


@router.post("/applications/{application_id}/pipeline-decision")
async def record_pipeline_decision(
    application_id: int,
    body: PipelineDecisionRequest,
    db: AsyncSession = Depends(get_session),
    current_hr: User = Depends(deps.get_current_hr),
) -> Any:
    application = (await db.execute(select(CandidateApplication).where(CandidateApplication.id == application_id))).scalars().first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    drive = await _get_drive_for_hr(db, application.job_drive_id, current_hr)
    workflow = await get_or_create_workflow(db, candidate_id=application.candidate_id, job_drive_id=drive.id)
    if body.decision != "on_hold" and workflow.current_state not in {"final_review", "decided"}:
        raise HTTPException(status_code=409, detail="Final decision requires the final review stage or an explicit override")
    workflow.decision = None if body.decision == "on_hold" else body.decision
    if body.decision in {"hired", "rejected", "withdrawn"}:
        workflow.current_state = "decided"
        workflow.decided_by = current_hr.id
        workflow.decided_at = _now()
    else:
        workflow.current_state = "final_review"
    workflow.updated_at = _now()
    await record_workflow_event(
        db,
        action="pipeline_final_decision",
        entity_type="candidate_workflow",
        actor_id=current_hr.id,
        actor_type="recruiter",
        job_drive_id=drive.id,
        candidate_id=application.candidate_id,
        application_id=application.id,
        entity_id=workflow.id,
        to_state=workflow.current_state,
        rationale=body.rationale,
        payload={"decision": body.decision},
        source="recruiter_decision",
    )
    await db.commit()
    return {"application_id": application_id, "decision": body.decision, "workflow_state": workflow.current_state}


@router.get("/assignments/{assignment_id}")
async def get_candidate_assessment(
    assignment_id: int,
    db: AsyncSession = Depends(get_session),
    current_candidate: User = Depends(deps.get_current_user),
) -> Any:
    assignment = (await db.execute(select(AssessmentAssignment).where(
        AssessmentAssignment.id == assignment_id,
        AssessmentAssignment.candidate_id == current_candidate.id,
    ))).scalars().first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assessment assignment not found")
    questions = []
    if assignment.definition_id:
        rows = (await db.execute(select(AssessmentQuestion).where(
            AssessmentQuestion.assessment_definition_id == assignment.definition_id,
            AssessmentQuestion.is_active == True,
        ).order_by(AssessmentQuestion.display_order))).scalars().all()
        questions = [_public_question(question) for question in rows]
    return {
        "assignment": {
            "id": assignment.id,
            "title": assignment.title,
            "instructions": assignment.instructions,
            "duration_minutes": assignment.duration_minutes,
            "passing_score": assignment.passing_score,
            "proctoring_enabled": assignment.proctoring_enabled,
            "due_at": assignment.due_at,
            "status": assignment.status,
        },
        "questions": questions,
        "proctoring_notice": "Proctoring events are reviewable evidence. They are not automatic rejection decisions.",
    }
