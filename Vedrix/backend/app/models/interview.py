from datetime import datetime, timezone
from typing import Optional, List, Any, TYPE_CHECKING
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, JSON, Text, Index, Integer, ForeignKey
from app.core.encryption import EncryptedJSON

if TYPE_CHECKING:
    from .user import User
    from .profile import HRProfile


class DriveInviteToken(SQLModel, table=True):
    __tablename__ = "drive_invite_token"

    id: Optional[int] = Field(default=None, primary_key=True)
    drive_id: int = Field(foreign_key="job_drive.id", nullable=False)
    token: str = Field(unique=True, index=True, nullable=False)
    candidate_email: Optional[str] = None
    is_used: bool = Field(default=False)
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    job_drive: "JobDrive" = Relationship(back_populates="invite_tokens")


class JobDrive(SQLModel, table=True):
    __tablename__ = "job_drive"

    id: Optional[int] = Field(default=None, primary_key=True)
    hr_id: int = Field(foreign_key="hr_profile.id", nullable=False)
    title: str = Field(nullable=False)
    description: Optional[str] = None
    job_role: str = Field(nullable=False)
    experience_required: Optional[str] = None
    skills_required: Optional[str] = None
    application_form_config: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    assessment_policy: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    workflow_policy: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    jd_version: int = Field(default=1, nullable=False)
    jd_parsed_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Phase 1.5: Soft delete support
    deleted_at: Optional[datetime] = Field(default=None)

    hr: "HRProfile" = Relationship(back_populates="job_drives")
    interview_sessions: List["InterviewSession"] = Relationship(back_populates="job_drive")
    invite_tokens: List["DriveInviteToken"] = Relationship(back_populates="job_drive")


class InterviewSession(SQLModel, table=True):
    __tablename__ = "interview_session"
    __table_args__ = (
        Index("ix_interview_candidate_id", "candidate_id"),
        Index("ix_interview_job_drive_id", "job_drive_id"),
        Index("ix_interview_status", "status"),
        Index("ix_interview_created_at", "created_at"),
    )

    id: Optional[int] = Field(default=None, primary_key=True)
    candidate_id: int = Field(foreign_key="user.id", nullable=False, index=True)
    job_drive_id: Optional[int] = Field(default=None, foreign_key="job_drive.id", index=True)
    session_type: str = Field(nullable=False)
    status: str = Field(default="scheduled", index=True)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[int] = None
    overall_score: Optional[float] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Native JSON columns — no more manual json.dumps/loads
    questions: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    responses: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    ai_feedback: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    
    # Enhanced skill matrix and AI transparency fields (Phase 1)
    skill_matrix: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    confidence_scores: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    evidence_log: Optional[Any] = Field(default=None, sa_column=Column(EncryptedJSON))
    agent_states: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    
    # Bias mitigation and fairness metrics
    bias_metrics: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    question_difficulty: Optional[Any] = Field(default=None, sa_column=Column(JSON))

    # Phase 1A: AI Interview Advisor fields
    advisor_ready_to_close: bool = Field(default=False)
    advisor_confidence: Optional[float] = None
    advisor_reason: Optional[str] = Field(default=None, sa_column=Column(Text))
    advisor_reason_category: Optional[str] = None
    advisor_suggested_at: Optional[datetime] = None
    advisor_action_taken: bool = Field(default=False)

    # Phase 1.5: Soft delete support
    deleted_at: Optional[datetime] = Field(default=None)

    # Agentic Platform: planner / orchestrator / proctor / sentiment / QA fields
    interview_plan_id: Optional[int] = Field(
        default=None,
        sa_column=Column(
            Integer,
            ForeignKey("interview_plan.id", use_alter=True, name="fk_interview_session_plan_id"),
            nullable=True,
        ),
    )
    workflow_state: Optional[str] = None
    empathy_timeline: Optional[Any] = Field(default=None, sa_column=Column(JSON))
    qa_quality_score: Optional[float] = None
    proctor_consent_granted: Optional[bool] = Field(default=False)

    # Relationships — must match back_populates on User and JobDrive
    candidate: "User" = Relationship(back_populates="interview_sessions")
    job_drive: Optional["JobDrive"] = Relationship(back_populates="interview_sessions")
class ScenarioTemplate(SQLModel, table=True):
    __tablename__ = "scenario_templates"
    __table_args__ = {"extend_existing": True}

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(nullable=False)
    description: Optional[str] = None
    type: str = Field(nullable=False)  # 'coding', 'system_design', 'behavioral'
    difficulty_level: int = Field(default=1)  # 1-5 scale
    estimated_time: int = Field(default=30)  # minutes
    scenarios: Optional[Any] = Field(default=None, sa_column=Column(JSON))  # Array of scenario objects
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
