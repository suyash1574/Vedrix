"""First-class hiring workflow records for ATS, assessments, manual interviews, and auditability."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, ForeignKey, Index, JSON, Text
from sqlmodel import Field, SQLModel

from app.core.encryption import EncryptedJSON


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CandidateApplication(SQLModel, table=True):
    """Candidate-submitted or recruiter-imported application for one job drive."""

    __tablename__ = "candidate_application"
    __table_args__ = (
        Index("ix_application_candidate_drive", "candidate_id", "job_drive_id", unique=True),
        Index("ix_application_drive_status", "job_drive_id", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)
    source: str = Field(default="application_form", nullable=False)
    status: str = Field(default="submitted", nullable=False, index=True)
    form_data: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    resume_text: Optional[str] = Field(default=None, sa_column=Column(Text))
    resume_url: Optional[str] = None
    consent_granted: bool = Field(default=False, nullable=False)
    consent_at: Optional[datetime] = None
    match_score: Optional[float] = None
    match_breakdown: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    screening_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    workflow_policy_snapshot: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    workflow_policy_version: int = Field(default=1, nullable=False)
    proctoring_consent_version: Optional[str] = None
    submitted_at: datetime = Field(default_factory=utc_now, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class AssessmentAssignment(SQLModel, table=True):
    """Recruiter-controlled online test assignment for one candidate application."""

    __tablename__ = "assessment_assignment"
    __table_args__ = (
        Index("ix_assessment_assignment_application", "application_id"),
        Index("ix_assessment_assignment_status", "status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="candidate_application.id", nullable=False)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    title: str = Field(nullable=False)
    assessment_type: str = Field(default="online_test", nullable=False)
    instructions: Optional[str] = Field(default=None, sa_column=Column(Text))
    config: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    definition_id: Optional[int] = Field(default=None, foreign_key="assessment_definition.id")
    policy_version: int = Field(default=1, nullable=False)
    duration_minutes: int = Field(default=45, nullable=False)
    passing_score: Optional[float] = None
    required: bool = Field(default=True, nullable=False)
    proctoring_enabled: bool = Field(default=True, nullable=False)
    status: str = Field(default="assigned", nullable=False)
    assigned_by: Optional[int] = Field(default=None, foreign_key="user.id")
    assigned_at: datetime = Field(default_factory=utc_now, nullable=False)
    available_from: Optional[datetime] = None
    due_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class AssessmentAttempt(SQLModel, table=True):
    """One online assessment attempt, including reviewable proctor evidence."""

    __tablename__ = "assessment_attempt"
    __table_args__ = (
        Index("ix_assessment_attempt_application", "application_id"),
        Index("ix_assessment_attempt_status", "status"),
        Index("ix_assessment_attempt_cheating", "cheating_status"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    assignment_id: int = Field(foreign_key="assessment_assignment.id", nullable=False)
    application_id: int = Field(foreign_key="candidate_application.id", nullable=False)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    attempt_number: int = Field(default=1, nullable=False)
    status: str = Field(default="not_started", nullable=False)
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    score: Optional[float] = None
    result: Optional[str] = None
    answers: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    proctor_summary: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    proctoring_consent_version: Optional[str] = None
    correlation_id: Optional[str] = Field(default=None, index=True)
    cheating_status: str = Field(default="not_reviewed", nullable=False)
    reviewer_id: Optional[int] = Field(default=None, foreign_key="user.id")
    reviewer_notes: Optional[str] = Field(default=None, sa_column=Column(Text))
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class ManualInterviewEntry(SQLModel, table=True):
    """Recruiter-entered interview record that participates in the final report."""

    __tablename__ = "manual_interview_entry"
    __table_args__ = (
        Index("ix_manual_interview_application", "application_id"),
        Index("ix_manual_interview_candidate_drive", "candidate_id", "job_drive_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="candidate_application.id", nullable=False)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)
    interviewer_id: int = Field(foreign_key="user.id", nullable=False)
    interview_type: str = Field(default="manual_interview", nullable=False)
    scheduled_at: Optional[datetime] = None
    occurred_at: datetime = Field(default_factory=utc_now, nullable=False)
    duration_minutes: Optional[int] = None
    rubric: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    notes: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    score: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class WorkflowAuditEvent(SQLModel, table=True):
    """Append-only business audit event for recruiter and candidate workflow actions."""

    __tablename__ = "workflow_audit_event"
    __table_args__ = (
        Index("ix_workflow_audit_candidate_drive", "candidate_id", "job_drive_id"),
        Index("ix_workflow_audit_occurred_at", "occurred_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    job_drive_id: Optional[int] = Field(default=None, foreign_key="job_drive.id", index=True)
    candidate_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    application_id: Optional[int] = Field(default=None, foreign_key="candidate_application.id", index=True)
    actor_id: Optional[int] = Field(default=None, foreign_key="user.id", index=True)
    actor_type: str = Field(default="system", nullable=False)
    entity_type: str = Field(nullable=False)
    entity_id: Optional[int] = None
    action: str = Field(nullable=False, index=True)
    from_state: Optional[str] = None
    to_state: Optional[str] = None
    rationale: Optional[str] = Field(default=None, sa_column=Column(Text))
    payload: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    stage_key: Optional[str] = Field(default=None, index=True)
    correlation_id: Optional[str] = Field(default=None, index=True)
    policy_version: Optional[int] = None
    source: str = Field(default="application", nullable=False)
    event_hash: Optional[str] = None
    previous_event_hash: Optional[str] = None
    occurred_at: datetime = Field(default_factory=utc_now, nullable=False, index=True)
