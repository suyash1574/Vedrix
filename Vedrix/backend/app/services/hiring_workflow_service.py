"""Core deterministic services for the recruiter-controlled hiring workflow."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.candidate_workflow import CandidateWorkflow
from app.models.hiring_workflow import CandidateApplication, WorkflowAuditEvent
from app.models.interview import JobDrive

_STOP_WORDS = {
    "and", "the", "for", "with", "that", "this", "from", "into", "your",
    "you", "are", "our", "will", "have", "has", "years", "year", "role",
    "work", "about", "using", "use", "must", "should", "their", "they",
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
        occurred_at=datetime.now(timezone.utc),
    )
    db.add(event)
    await db.flush()
    return event
