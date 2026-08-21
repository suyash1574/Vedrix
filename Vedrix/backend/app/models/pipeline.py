"""First-class ordered hiring pipeline entities for Autergo."""

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Column, ForeignKey, Index, JSON, Text
from sqlmodel import Field, SQLModel

from app.core.encryption import EncryptedJSON


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class HiringPipelineStageRun(SQLModel, table=True):
    """One versioned, auditable run of a candidate pipeline stage."""

    __tablename__ = "hiring_pipeline_stage_run"
    __table_args__ = (
        Index("ix_stage_run_application_stage", "application_id", "stage_key"),
        Index("ix_stage_run_candidate_drive", "candidate_id", "job_drive_id"),
        Index("ix_stage_run_status_due", "status", "due_at"),
        Index(
            "uq_stage_run_application_stage_attempt",
            "application_id",
            "stage_key",
            "attempt_number",
            unique=True,
        ),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    application_id: int = Field(foreign_key="candidate_application.id", nullable=False)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)
    stage_key: str = Field(nullable=False, index=True)
    sequence_number: int = Field(default=1, nullable=False)
    status: str = Field(default="pending", nullable=False, index=True)
    required: bool = Field(default=True, nullable=False)
    policy_snapshot: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    policy_version: int = Field(default=1, nullable=False)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    due_at: Optional[datetime] = None
    attempt_number: int = Field(default=1, nullable=False)
    outcome: Optional[str] = None
    score: Optional[float] = None
    confidence: Optional[float] = None
    assigned_to: Optional[int] = Field(default=None, foreign_key="user.id")
    source: str = Field(default="system", nullable=False)
    related_entity_type: Optional[str] = None
    related_entity_id: Optional[int] = None
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class AssessmentDefinition(SQLModel, table=True):
    """Versioned recruiter-authored online test definition."""

    __tablename__ = "assessment_definition"
    __table_args__ = (
        Index("ix_assessment_definition_drive_active", "job_drive_id", "is_active"),
        Index("uq_assessment_definition_drive_version", "job_drive_id", "version", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)
    title: str = Field(nullable=False)
    instructions: Optional[str] = Field(default=None, sa_column=Column(Text))
    version: int = Field(default=1, nullable=False)
    duration_minutes: int = Field(default=45, nullable=False)
    passing_score: Optional[float] = None
    question_order_policy: str = Field(default="fixed", nullable=False)
    randomization_seed: Optional[str] = None
    is_published: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_by: Optional[int] = Field(default=None, foreign_key="user.id")
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class AssessmentQuestion(SQLModel, table=True):
    """A public-safe question definition; answer metadata stays server-side."""

    __tablename__ = "assessment_question"
    __table_args__ = (
        Index("ix_assessment_question_definition_order", "assessment_definition_id", "display_order"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    assessment_definition_id: int = Field(foreign_key="assessment_definition.id", nullable=False, index=True)
    question_key: str = Field(nullable=False)
    question_type: str = Field(default="text", nullable=False)
    prompt: str = Field(sa_column=Column(Text, nullable=False))
    options: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    expected_answer: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    points: float = Field(default=1.0, nullable=False)
    skill_tags: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    coding_config: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    display_order: int = Field(default=0, nullable=False)
    version: int = Field(default=1, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class AssessmentResponse(SQLModel, table=True):
    """Encrypted, idempotent candidate response for one assessment question."""

    __tablename__ = "assessment_response"
    __table_args__ = (
        Index(
            "uq_assessment_response_attempt_question",
            "attempt_id",
            "question_id",
            "question_version",
            unique=True,
        ),
        Index("ix_assessment_response_attempt", "attempt_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    attempt_id: int = Field(foreign_key="assessment_attempt.id", nullable=False)
    question_id: int = Field(foreign_key="assessment_question.id", nullable=False)
    question_version: int = Field(default=1, nullable=False)
    response_data: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    autosaved_at: datetime = Field(default_factory=utc_now, nullable=False)
    finalized: bool = Field(default=False, nullable=False)
    score: Optional[float] = None
    grader_source: Optional[str] = None
    idempotency_key: Optional[str] = None
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class ProctorEvidenceEvent(SQLModel, table=True):
    """Append-only, consent-gated structured proctoring evidence."""

    __tablename__ = "proctor_evidence_event"
    __table_args__ = (
        Index("ix_proctor_event_attempt_at", "attempt_id", "occurred_at"),
        Index("ix_proctor_event_type", "event_type"),
        Index("ix_proctor_event_correlation", "correlation_id"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    attempt_id: int = Field(foreign_key="assessment_attempt.id", nullable=False, index=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    event_type: str = Field(nullable=False)
    occurred_at: datetime = Field(default_factory=utc_now, nullable=False)
    client_metadata: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    evidence_uri: Optional[str] = None
    confidence: Optional[float] = None
    consent_version: Optional[str] = None
    correlation_id: str = Field(nullable=False, index=True)
    retention_status: str = Field(default="active", nullable=False)
    payload: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)


class AIInterviewStageReview(SQLModel, table=True):
    """Recruiter review gate for an AI interview stage."""

    __tablename__ = "ai_interview_stage_review"
    __table_args__ = (
        Index("ix_ai_stage_review_application", "application_id"),
        Index("uq_ai_stage_review_session", "interview_session_id", unique=True),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    stage_run_id: int = Field(foreign_key="hiring_pipeline_stage_run.id", nullable=False, index=True)
    application_id: int = Field(foreign_key="candidate_application.id", nullable=False)
    interview_session_id: int = Field(foreign_key="interview_session.id", nullable=False)
    status: str = Field(default="pending", nullable=False)
    confidence: Optional[float] = None
    follow_up_request: Optional[str] = Field(default=None, sa_column=Column(Text))
    approved_by: Optional[int] = Field(default=None, foreign_key="user.id")
    approved_at: Optional[datetime] = None
    rationale: Optional[str] = Field(default=None, sa_column=Column(Text))
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)


class HumanInterviewSchedule(SQLModel, table=True):
    """Recruiter-controlled human interview schedule linked to a stage run."""

    __tablename__ = "human_interview_schedule"
    __table_args__ = (
        Index("ix_human_schedule_application_status", "application_id", "status"),
        Index("ix_human_schedule_interviewer_time", "interviewer_id", "scheduled_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    stage_run_id: int = Field(foreign_key="hiring_pipeline_stage_run.id", nullable=False, index=True)
    application_id: int = Field(foreign_key="candidate_application.id", nullable=False)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    job_drive_id: int = Field(foreign_key="job_drive.id", nullable=False, index=True)
    interviewer_id: int = Field(foreign_key="user.id", nullable=False)
    interview_type: str = Field(default="human_interview", nullable=False)
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None
    meeting_location: Optional[str] = None
    meeting_link: Optional[str] = None
    rubric: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    status: str = Field(default="scheduled", nullable=False)
    cancellation_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    reminder_sent_at: Optional[datetime] = None
    manual_entry_id: Optional[int] = Field(default=None, foreign_key="manual_interview_entry.id")
    created_at: datetime = Field(default_factory=utc_now, nullable=False)
    updated_at: datetime = Field(default_factory=utc_now, nullable=False)
