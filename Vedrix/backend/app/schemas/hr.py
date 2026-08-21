from typing import Optional, List
from typing import List, Literal, Optional

from pydantic import BaseModel, EmailStr, ConfigDict, Field
from datetime import datetime

class JobDriveBase(BaseModel):
    title: str
    description: Optional[str] = None
    job_role: str
    experience_required: Optional[str] = None
    skills_required: Optional[str] = None
    application_form_config: Optional[dict] = None
    assessment_policy: Optional[dict] = None
    workflow_policy: Optional[dict] = None
    jd_version: int = 1
    is_active: bool = True

class JobDriveCreate(JobDriveBase):
    pass

class JobDriveUpdate(JobDriveBase):
    title: Optional[str] = None
    job_role: Optional[str] = None
    description: Optional[str] = None
    experience_required: Optional[str] = None
    skills_required: Optional[str] = None
    application_form_config: Optional[dict] = None
    assessment_policy: Optional[dict] = None
    workflow_policy: Optional[dict] = None
    jd_version: Optional[int] = None
    is_active: Optional[bool] = None

class JobDriveRead(JobDriveBase):
    id: int
    hr_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class MagicLinkRequest(BaseModel):
    candidate_email: Optional[str] = None  # audit #26: associate email with single link
    expires_in_hours: int = 72

class MagicLinkResponse(BaseModel):
    link: str
    token: str

class BulkInviteRequest(BaseModel):
    emails: List[str]
    expires_in_hours: int = 72

class BulkInviteResponse(BaseModel):
    invited: int
    links: List[MagicLinkResponse]


class CandidateApplicationCreate(BaseModel):
    candidate_id: Optional[int] = None
    candidate_email: Optional[EmailStr] = None
    candidate_first_name: Optional[str] = None
    candidate_last_name: Optional[str] = None
    source: str = "application_form"
    form_data: dict = {}
    resume_text: Optional[str] = None
    resume_url: Optional[str] = None
    consent_granted: bool = False


class CandidateApplicationRead(BaseModel):
    id: int
    candidate_id: int
    job_drive_id: int
    source: str
    status: str
    form_data: Optional[dict] = None
    resume_url: Optional[str] = None
    consent_granted: bool
    match_score: Optional[float] = None
    match_breakdown: Optional[dict] = None
    submitted_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AssessmentAssignmentCreate(BaseModel):
    application_id: int
    definition_id: Optional[int] = None
    title: str
    assessment_type: str = "online_test"
    instructions: Optional[str] = None
    config: dict = {}
    duration_minutes: int = 45
    passing_score: Optional[float] = None
    required: bool = True
    proctoring_enabled: bool = True
    available_from: Optional[datetime] = None
    due_at: Optional[datetime] = None


class AssessmentAssignmentRead(BaseModel):
    id: int
    application_id: int
    job_drive_id: int
    candidate_id: int
    title: str
    assessment_type: str
    instructions: Optional[str] = None
    config: Optional[dict] = None
    duration_minutes: int
    passing_score: Optional[float] = None
    required: bool
    proctoring_enabled: bool
    status: str
    assigned_by: Optional[int] = None
    assigned_at: datetime
    available_from: Optional[datetime] = None
    due_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AssessmentReviewRequest(BaseModel):
    cheating_status: str
    reviewer_notes: Optional[str] = None
    rationale: Optional[str] = None


class ManualInterviewEntryCreate(BaseModel):
    application_id: int
    interview_type: str = "manual_interview"
    scheduled_at: Optional[datetime] = None
    occurred_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    rubric: dict = {}
    notes: dict = {}
    score: Optional[float] = None
    recommendation: Optional[str] = None


class WorkflowOverrideRequest(BaseModel):
    target_state: str
    rationale: str


class WorkflowDecisionRequest(BaseModel):
    decision: str
    rationale: str


class HiringPipelinePolicy(BaseModel):
    """Recruiter-configurable canonical pipeline policy."""

    assessment_enabled: bool = True
    assessment_required: bool = True
    proctoring_enabled: bool = True
    ai_interview_enabled: bool = True
    ai_interview_required: bool = True
    human_interview_enabled: bool = True
    human_interview_required: bool = True
    stage_order: List[str] = Field(
        default_factory=lambda: ["assessment", "ai_interview", "human_interview"]
    )
    assessment_definition_id: Optional[int] = None
    assessment_duration_minutes: int = 45
    assessment_passing_score: Optional[float] = None
    assessment_allowed_attempts: int = 1
    assessment_due_hours: Optional[int] = 72
    assessment_autosave_seconds: int = 10
    assessment_randomization: bool = False
    proctor_consent_version: str = "proctoring-v1"
    proctor_require_camera: bool = False
    proctor_require_microphone: bool = False
    proctor_require_fullscreen: bool = False
    proctor_risk_review_threshold: int = 20
    proctor_continue_after_signal: bool = True
    ai_interview_template: Optional[str] = None
    ai_interview_question_count: int = 8
    ai_interview_time_limit_minutes: int = 30
    ai_interview_auto_progress_confidence: float = 0.85
    ai_interview_recruiter_approval_required: bool = True
    human_interview_types: List[str] = Field(default_factory=lambda: ["human_interview"])
    human_interview_rubric: dict = Field(default_factory=dict)
    human_interview_required_recommendation: bool = False
    allowed_bypasses: List[str] = Field(default_factory=list)
    hold_reasons: List[str] = Field(default_factory=list)


class PipelinePolicyUpdate(BaseModel):
    policy: HiringPipelinePolicy
    rationale: Optional[str] = None


class AssessmentDefinitionCreate(BaseModel):
    title: str
    instructions: Optional[str] = None
    duration_minutes: int = 45
    passing_score: Optional[float] = None
    question_order_policy: Literal["fixed", "randomized"] = "fixed"
    questions: List[dict] = Field(default_factory=list)
    publish: bool = False


class AssessmentResponseUpsert(BaseModel):
    question_id: int
    response_data: object = None
    question_version: int = 1
    idempotency_key: str
    finalize: bool = False


class ProctorEvidenceEventCreate(BaseModel):
    event_type: str
    occurred_at: Optional[datetime] = None
    client_metadata: dict = Field(default_factory=dict)
    evidence_uri: Optional[str] = None
    confidence: Optional[float] = None
    payload: dict = Field(default_factory=dict)


class AIInterviewStageScheduleRequest(BaseModel):
    start_time: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    rationale: Optional[str] = None


class AIInterviewStageReviewRequest(BaseModel):
    session_id: int
    status: Literal["approved", "follow_up", "rejected", "hold"]
    rationale: str
    confidence: Optional[float] = None
    follow_up_request: Optional[str] = None


class HumanInterviewScheduleRequest(BaseModel):
    interviewer_id: int
    interview_type: str = "human_interview"
    scheduled_at: Optional[datetime] = None
    timezone: Optional[str] = None
    meeting_location: Optional[str] = None
    meeting_link: Optional[str] = None
    rubric: dict = Field(default_factory=dict)
    rationale: Optional[str] = None


class HumanInterviewSubmitRequest(BaseModel):
    schedule_id: int
    occurred_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    notes: dict = Field(default_factory=dict)
    score: Optional[float] = None
    recommendation: Optional[str] = None
    evidence_links: List[str] = Field(default_factory=list)


class PipelineOverrideRequest(BaseModel):
    target_stage: str
    rationale: str
    bypassed_stages: List[str] = Field(default_factory=list)


class PipelineDecisionRequest(BaseModel):
    decision: Literal["hired", "rejected", "withdrawn", "on_hold"]
    rationale: str
