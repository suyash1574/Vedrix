from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
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
