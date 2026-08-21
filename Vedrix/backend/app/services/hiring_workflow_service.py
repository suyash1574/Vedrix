"""Core deterministic services for the recruiter-controlled hiring workflow."""

from __future__ import annotations

import re
import uuid
from copy import deepcopy
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_workflow import CandidateWorkflow
from app.models.hiring_workflow import CandidateApplication, WorkflowAuditEvent
from app.models.interview import JobDrive
from app.models.pipeline import HiringPipelineStageRun

_STOP_WORDS = {
    "and", "the", "for", "with", "that", "this", "from", "into", "your",
    "you", "are", "our", "will", "have", "has", "years", "year", "role",
    "work", "about", "using", "use", "must", "should", "their", "they",
}

CANONICAL_STAGE_ORDER = ("assessment", "ai_interview", "human_interview")
STAGE_STATE_MAP = {
    "assessment": "assessment_assigned",
    "ai_interview": "ai_interview_scheduled",
    "human_interview": "human_interview_scheduled",
}

DEFAULT_PIPELINE_POLICY: dict[str, Any] = {
    "assessment_enabled": True,
    "assessment_required": True,
    "proctoring_enabled": True,
    "ai_interview_enabled": True,
    "ai_interview_required": True,
    "human_interview_enabled": True,
    "human_interview_required": True,
    "stage_order": list(CANONICAL_STAGE_ORDER),
    "assessment_definition_id": None,
    "assessment_duration_minutes": 45,
    "assessment_passing_score": None,
    "assessment_allowed_attempts": 1,
    "assessment_due_hours": 72,
    "assessment_autosave_seconds": 10,
    "assessment_randomization": False,
    "proctor_consent_version": "proctoring-v1",
    "proctor_require_camera": False,
    "proctor_require_microphone": False,
    "proctor_require_fullscreen": False,
    "proctor_risk_review_threshold": 20,
    "proctor_continue_after_signal": True,
    "ai_interview_template": None,
    "ai_interview_question_count": 8,
    "ai_interview_time_limit_minutes": 30,
    "ai_interview_auto_progress_confidence": 0.85,
    "ai_interview_recruiter_approval_required": True,
    "human_interview_types": ["human_interview"],
    "human_interview_rubric": {},
    "human_interview_required_recommendation": False,
    "allowed_bypasses": [],
    "hold_reasons": [],
}


def _tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-zA-Z0-9+#.]{2,}", (value or "").lower())
        if token not in _STOP_WORDS
    }


def score_application_against_drive(drive: JobDrive, application: CandidateApplication) -> dict[str, Any]:
    """Return an explainable deterministic baseline match score for ATS screening."""
    jd_text = " ".join(
        str(value or "")
        for value in (drive.title, drive.description, drive.job_role, drive.experience_required, drive.skills_required)
    )
    candidate_form = application.form_data if isinstance(application.form_data, dict) else {}
    candidate_text = " ".join(
        [application.resume_text or ""]
        + [str(value or "") for value in candidate_form.values()]
    )
    jd_tokens = _tokens(jd_text)
    candidate_tokens = _tokens(candidate_text)
    matched = sorted(jd_tokens & candidate_tokens)
    missing = sorted(jd_tokens - candidate_tokens)
    score = round((len(matched) / max(len(jd_tokens), 1)) * 100, 2)
    return {
        "score": score,
        "matched_terms": matched[:100],
        "missing_terms": missing[:100],
        "jd_term_count": len(jd_tokens),
        "candidate_term_count": len(candidate_tokens),
        "method": "deterministic_token_overlap_v1",
    }


def normalize_pipeline_policy(raw_policy: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Merge and validate a drive policy while enforcing AI-before-human ordering."""
    policy = deepcopy(DEFAULT_PIPELINE_POLICY)
    if isinstance(raw_policy, dict):
        policy.update({key: value for key, value in raw_policy.items() if value is not None})

    order = list(policy.get("stage_order") or CANONICAL_STAGE_ORDER)
    unknown = set(order) - set(CANONICAL_STAGE_ORDER)
    if unknown or len(order) != len(set(order)):
        raise ValueError(f"stage_order contains unknown or duplicate stages: {sorted(unknown)}")
    if "ai_interview" in order and "human_interview" in order:
        if order.index("ai_interview") > order.index("human_interview"):
            raise ValueError("AI interview must occur before human interview")
    policy["stage_order"] = order

    for stage_key, enabled_key in (
        ("assessment", "assessment_enabled"),
        ("ai_interview", "ai_interview_enabled"),
        ("human_interview", "human_interview_enabled"),
    ):
        if policy.get(enabled_key) and stage_key not in order:
            order.append(stage_key)
    policy["stage_order"] = order

    if policy.get("assessment_required") and not policy.get("assessment_enabled"):
        raise ValueError("assessment_required cannot be true when assessment_enabled is false")
    if policy.get("ai_interview_required") and not policy.get("ai_interview_enabled"):
        raise ValueError("ai_interview_required cannot be true when ai_interview_enabled is false")
    if policy.get("human_interview_required") and not policy.get("human_interview_enabled"):
        raise ValueError("human_interview_required cannot be true when human_interview_enabled is false")
    if int(policy.get("assessment_allowed_attempts") or 0) < 1:
        raise ValueError("assessment_allowed_attempts must be at least 1")
    if int(policy.get("assessment_duration_minutes") or 0) < 1:
        raise ValueError("assessment_duration_minutes must be positive")
    return policy


def policy_version(drive: JobDrive) -> int:
    return int(getattr(drive, "jd_version", 1) or 1)


async def get_or_create_workflow(
    db: AsyncSession,
    *,
    candidate_id: int,
    job_drive_id: int,
    initial_state: str = "invited",
) -> CandidateWorkflow:
    result = await db.execute(
        select(CandidateWorkflow).where(
            CandidateWorkflow.candidate_id == candidate_id,
            CandidateWorkflow.job_drive_id == job_drive_id,
        )
    )
    workflow = result.scalar_one_or_none()
    if workflow:
        return workflow
    workflow = CandidateWorkflow(
        candidate_id=candidate_id,
        job_drive_id=job_drive_id,
        current_state=initial_state,
        transition_history=[],
    )
    db.add(workflow)
    await db.flush()
    return workflow


async def get_or_create_stage_run(
    db: AsyncSession,
    *,
    application: CandidateApplication,
    drive: JobDrive,
    stage_key: str,
    required: bool,
    sequence_number: int,
    due_at: Optional[datetime] = None,
    status: str = "pending",
    source: str = "system",
    attempt_number: int = 1,
    related_entity_type: Optional[str] = None,
    related_entity_id: Optional[int] = None,
) -> HiringPipelineStageRun:
    result = await db.execute(
        select(HiringPipelineStageRun).where(
            HiringPipelineStageRun.application_id == application.id,
            HiringPipelineStageRun.stage_key == stage_key,
            HiringPipelineStageRun.attempt_number == attempt_number,
        )
    )
    stage_run = result.scalar_one_or_none()
    if stage_run:
        return stage_run

    policy = normalize_pipeline_policy(drive.workflow_policy)
    stage_run = HiringPipelineStageRun(
        application_id=application.id,
        candidate_id=application.candidate_id,
        job_drive_id=drive.id,
        stage_key=stage_key,
        sequence_number=sequence_number,
        status=status,
        required=required,
        policy_snapshot=policy,
        policy_version=policy_version(drive),
        due_at=due_at,
        attempt_number=attempt_number,
        source=source,
        related_entity_type=related_entity_type,
        related_entity_id=related_entity_id,
    )
    db.add(stage_run)
    await db.flush()
    return stage_run


async def record_workflow_event(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    actor_id: Optional[int] = None,
    actor_type: str = "system",
    job_drive_id: Optional[int] = None,
    candidate_id: Optional[int] = None,
    application_id: Optional[int] = None,
    entity_id: Optional[int] = None,
    from_state: Optional[str] = None,
    to_state: Optional[str] = None,
    rationale: Optional[str] = None,
    payload: Optional[dict[str, Any]] = None,
    stage_key: Optional[str] = None,
    correlation_id: Optional[str] = None,
    policy_version_value: Optional[int] = None,
    source: str = "application",
) -> WorkflowAuditEvent:
    event = WorkflowAuditEvent(
        action=action,
        entity_type=entity_type,
        actor_id=actor_id,
        actor_type=actor_type,
        job_drive_id=job_drive_id,
        candidate_id=candidate_id,
        application_id=application_id,
        entity_id=entity_id,
        from_state=from_state,
        to_state=to_state,
        rationale=rationale,
        payload=payload,
        stage_key=stage_key,
        correlation_id=correlation_id or str(uuid.uuid4()),
        policy_version=policy_version_value,
        source=source,
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    return event


def state_for_stage(stage_key: str) -> str:
    try:
        return STAGE_STATE_MAP[stage_key]
    except KeyError as exc:
        raise ValueError(f"Unsupported pipeline stage: {stage_key}") from exc


def assert_human_stage_gate(current_state: str, *, override: bool = False) -> None:
    """Prevent human scheduling before AI completion unless explicitly overridden."""
    if override:
        return
    allowed = {"ai_interview_review", "human_interview_scheduled", "human_interview", "final_review"}
    if current_state not in allowed:
        raise ValueError(
            "Human interview cannot be scheduled before the AI interview is completed and reviewed"
        )
