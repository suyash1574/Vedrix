"""add hiring workflow entities

Revision ID: b7c9d1e2f3a4
Revises: 759cc7077951
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b7c9d1e2f3a4"
down_revision: Union[str, None] = "759cc7077951"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("job_drive", sa.Column("application_form_config", sa.JSON(), nullable=True))
    op.add_column("job_drive", sa.Column("assessment_policy", sa.JSON(), nullable=True))
    op.add_column("job_drive", sa.Column("workflow_policy", sa.JSON(), nullable=True))
    op.add_column("job_drive", sa.Column("jd_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("job_drive", sa.Column("jd_parsed_at", sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        "candidate_application",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("job_drive_id", sa.Integer(), sa.ForeignKey("job_drive.id"), nullable=False),
        sa.Column("source", sa.String(), nullable=False, server_default="application_form"),
        sa.Column("status", sa.String(), nullable=False, server_default="submitted"),
        sa.Column("form_data", sa.JSON(), nullable=True),
        sa.Column("resume_text", sa.Text(), nullable=True),
        sa.Column("resume_url", sa.String(), nullable=True),
        sa.Column("consent_granted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("consent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=True),
        sa.Column("match_breakdown", sa.JSON(), nullable=True),
        sa.Column("screening_notes", sa.Text(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_application_candidate_drive", "candidate_application", ["candidate_id", "job_drive_id"], unique=True)
    op.create_index("ix_application_candidate_id", "candidate_application", ["candidate_id"])
    op.create_index("ix_application_job_drive_id", "candidate_application", ["job_drive_id"])
    op.create_index("ix_application_drive_status", "candidate_application", ["job_drive_id", "status"])

    op.create_table(
        "assessment_assignment",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("candidate_application.id"), nullable=False),
        sa.Column("job_drive_id", sa.Integer(), sa.ForeignKey("job_drive.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("assessment_type", sa.String(), nullable=False, server_default="online_test"),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("passing_score", sa.Float(), nullable=True),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("proctoring_enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("status", sa.String(), nullable=False, server_default="assigned"),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessment_assignment_application", "assessment_assignment", ["application_id"])
    op.create_index("ix_assessment_assignment_job_drive_id", "assessment_assignment", ["job_drive_id"])
    op.create_index("ix_assessment_assignment_candidate_id", "assessment_assignment", ["candidate_id"])
    op.create_index("ix_assessment_assignment_status", "assessment_assignment", ["status"])

    op.create_table(
        "assessment_attempt",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assignment_id", sa.Integer(), sa.ForeignKey("assessment_assignment.id"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("candidate_application.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="not_started"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("result", sa.String(), nullable=True),
        sa.Column("answers", sa.JSON(), nullable=True),
        sa.Column("proctor_summary", sa.JSON(), nullable=True),
        sa.Column("cheating_status", sa.String(), nullable=False, server_default="not_reviewed"),
        sa.Column("reviewer_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_assessment_attempt_application", "assessment_attempt", ["application_id"])
    op.create_index("ix_assessment_attempt_candidate_id", "assessment_attempt", ["candidate_id"])
    op.create_index("ix_assessment_attempt_status", "assessment_attempt", ["status"])
    op.create_index("ix_assessment_attempt_cheating", "assessment_attempt", ["cheating_status"])

    op.create_table(
        "manual_interview_entry",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("candidate_application.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("job_drive_id", sa.Integer(), sa.ForeignKey("job_drive.id"), nullable=False),
        sa.Column("interviewer_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("interview_type", sa.String(), nullable=False, server_default="manual_interview"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("rubric", sa.JSON(), nullable=True),
        sa.Column("notes", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("recommendation", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_manual_interview_application", "manual_interview_entry", ["application_id"])
    op.create_index("ix_manual_interview_candidate_id", "manual_interview_entry", ["candidate_id"])
    op.create_index("ix_manual_interview_job_drive_id", "manual_interview_entry", ["job_drive_id"])
    op.create_index("ix_manual_interview_candidate_drive", "manual_interview_entry", ["candidate_id", "job_drive_id"])

    op.create_table(
        "workflow_audit_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_drive_id", sa.Integer(), sa.ForeignKey("job_drive.id"), nullable=True),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("candidate_application.id"), nullable=True),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("actor_type", sa.String(), nullable=False, server_default="system"),
        sa.Column("entity_type", sa.String(), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("from_state", sa.String(), nullable=True),
        sa.Column("to_state", sa.String(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_workflow_audit_candidate_drive", "workflow_audit_event", ["candidate_id", "job_drive_id"])
    op.create_index("ix_workflow_audit_candidate_id", "workflow_audit_event", ["candidate_id"])
    op.create_index("ix_workflow_audit_job_drive_id", "workflow_audit_event", ["job_drive_id"])
    op.create_index("ix_workflow_audit_application_id", "workflow_audit_event", ["application_id"])
    op.create_index("ix_workflow_audit_actor_id", "workflow_audit_event", ["actor_id"])
    op.create_index("ix_workflow_audit_action", "workflow_audit_event", ["action"])
    op.create_index("ix_workflow_audit_occurred_at", "workflow_audit_event", ["occurred_at"])


def downgrade() -> None:
    op.drop_table("workflow_audit_event")
    op.drop_table("manual_interview_entry")
    op.drop_table("assessment_attempt")
    op.drop_table("assessment_assignment")
    op.drop_table("candidate_application")
    op.drop_column("job_drive", "jd_parsed_at")
    op.drop_column("job_drive", "jd_version")
    op.drop_column("job_drive", "workflow_policy")
    op.drop_column("job_drive", "assessment_policy")
    op.drop_column("job_drive", "application_form_config")
