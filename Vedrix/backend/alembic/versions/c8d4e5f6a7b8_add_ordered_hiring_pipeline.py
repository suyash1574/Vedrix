"""Add ordered online-test, AI-interview, and human-interview pipeline entities.

Revision ID: c8d4e5f6a7b8
Revises: b7c9d1e2f3a4
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c8d4e5f6a7b8"
down_revision: Union[str, None] = "b7c9d1e2f3a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("candidate_application", sa.Column("workflow_policy_snapshot", sa.JSON(), nullable=True))
    op.add_column("candidate_application", sa.Column("workflow_policy_version", sa.Integer(), nullable=False, server_default="1"))
    op.add_column("candidate_application", sa.Column("proctoring_consent_version", sa.String(), nullable=True))

    op.add_column("assessment_assignment", sa.Column("definition_id", sa.Integer(), nullable=True))
    op.add_column("assessment_assignment", sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"))

    op.add_column("assessment_attempt", sa.Column("proctoring_consent_version", sa.String(), nullable=True))
    op.add_column("assessment_attempt", sa.Column("correlation_id", sa.String(), nullable=True))
    op.create_index("ix_assessment_attempt_correlation_id", "assessment_attempt", ["correlation_id"])

    for name, column in (
        ("stage_key", sa.Column("stage_key", sa.String(), nullable=True)),
        ("correlation_id", sa.Column("correlation_id", sa.String(), nullable=True)),
        ("policy_version", sa.Column("policy_version", sa.Integer(), nullable=True)),
        ("source", sa.Column("source", sa.String(), nullable=False, server_default="application")),
        ("event_hash", sa.Column("event_hash", sa.String(), nullable=True)),
        ("previous_event_hash", sa.Column("previous_event_hash", sa.String(), nullable=True)),
    ):
        op.add_column("workflow_audit_event", column)
    op.create_index("ix_workflow_audit_event_stage_key", "workflow_audit_event", ["stage_key"])
    op.create_index("ix_workflow_audit_event_correlation_id", "workflow_audit_event", ["correlation_id"])

    op.create_table(
        "hiring_pipeline_stage_run",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("candidate_application.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("job_drive_id", sa.Integer(), sa.ForeignKey("job_drive.id"), nullable=False),
        sa.Column("stage_key", sa.String(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("policy_snapshot", sa.JSON(), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("outcome", sa.String(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("source", sa.String(), nullable=False, server_default="system"),
        sa.Column("related_entity_type", sa.String(), nullable=True),
        sa.Column("related_entity_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_stage_run_application_stage", "hiring_pipeline_stage_run", ["application_id", "stage_key"])
    op.create_index("ix_stage_run_candidate_drive", "hiring_pipeline_stage_run", ["candidate_id", "job_drive_id"])
    op.create_index("ix_stage_run_status_due", "hiring_pipeline_stage_run", ["status", "due_at"])
    op.create_index(
        "uq_stage_run_application_stage_attempt",
        "hiring_pipeline_stage_run",
        ["application_id", "stage_key", "attempt_number"],
        unique=True,
    )

    op.create_table(
        "assessment_definition",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("job_drive_id", sa.Integer(), sa.ForeignKey("job_drive.id"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("duration_minutes", sa.Integer(), nullable=False, server_default="45"),
        sa.Column("passing_score", sa.Float(), nullable=True),
        sa.Column("question_order_policy", sa.String(), nullable=False, server_default="fixed"),
        sa.Column("randomization_seed", sa.String(), nullable=True),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assessment_definition_drive_active", "assessment_definition", ["job_drive_id", "is_active"])
    op.create_index("uq_assessment_definition_drive_version", "assessment_definition", ["job_drive_id", "version"], unique=True)
    op.create_foreign_key(
        "fk_assessment_assignment_definition",
        "assessment_assignment",
        "assessment_definition",
        ["definition_id"],
        ["id"],
    )

    op.create_table(
        "assessment_question",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("assessment_definition_id", sa.Integer(), sa.ForeignKey("assessment_definition.id"), nullable=False),
        sa.Column("question_key", sa.String(), nullable=False),
        sa.Column("question_type", sa.String(), nullable=False, server_default="text"),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("options", sa.JSON(), nullable=True),
        # EncryptedJSON is persisted as Text at the database level.
        sa.Column("expected_answer", sa.Text(), nullable=True),
        sa.Column("points", sa.Float(), nullable=False, server_default="1"),
        sa.Column("skill_tags", sa.JSON(), nullable=True),
        sa.Column("coding_config", sa.JSON(), nullable=True),
        sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_assessment_question_definition_order", "assessment_question", ["assessment_definition_id", "display_order"])

    op.create_table(
        "assessment_response",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("assessment_attempt.id"), nullable=False),
        sa.Column("question_id", sa.Integer(), sa.ForeignKey("assessment_question.id"), nullable=False),
        sa.Column("question_version", sa.Integer(), nullable=False, server_default="1"),
        # EncryptedJSON is persisted as Text at the database level.
        sa.Column("response_data", sa.Text(), nullable=True),
        sa.Column("autosaved_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finalized", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("grader_source", sa.String(), nullable=True),
        sa.Column("idempotency_key", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("uq_assessment_response_attempt_question", "assessment_response", ["attempt_id", "question_id", "question_version"], unique=True)
    op.create_index("ix_assessment_response_attempt", "assessment_response", ["attempt_id"])

    op.create_table(
        "proctor_evidence_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("attempt_id", sa.Integer(), sa.ForeignKey("assessment_attempt.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("client_metadata", sa.JSON(), nullable=True),
        sa.Column("evidence_uri", sa.String(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("consent_version", sa.String(), nullable=True),
        sa.Column("correlation_id", sa.String(), nullable=False),
        sa.Column("retention_status", sa.String(), nullable=False, server_default="active"),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_proctor_event_attempt_at", "proctor_evidence_event", ["attempt_id", "occurred_at"])
    op.create_index("ix_proctor_event_type", "proctor_evidence_event", ["event_type"])
    op.create_index("ix_proctor_event_correlation", "proctor_evidence_event", ["correlation_id"])

    op.create_table(
        "ai_interview_stage_review",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stage_run_id", sa.Integer(), sa.ForeignKey("hiring_pipeline_stage_run.id"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("candidate_application.id"), nullable=False),
        sa.Column("interview_session_id", sa.Integer(), sa.ForeignKey("interview_session.id"), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("follow_up_request", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.Integer(), sa.ForeignKey("user.id"), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_ai_stage_review_application", "ai_interview_stage_review", ["application_id"])
    op.create_index("uq_ai_stage_review_session", "ai_interview_stage_review", ["interview_session_id"], unique=True)

    op.create_table(
        "human_interview_schedule",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("stage_run_id", sa.Integer(), sa.ForeignKey("hiring_pipeline_stage_run.id"), nullable=False),
        sa.Column("application_id", sa.Integer(), sa.ForeignKey("candidate_application.id"), nullable=False),
        sa.Column("candidate_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("job_drive_id", sa.Integer(), sa.ForeignKey("job_drive.id"), nullable=False),
        sa.Column("interviewer_id", sa.Integer(), sa.ForeignKey("user.id"), nullable=False),
        sa.Column("interview_type", sa.String(), nullable=False, server_default="human_interview"),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("timezone", sa.String(), nullable=True),
        sa.Column("meeting_location", sa.String(), nullable=True),
        sa.Column("meeting_link", sa.String(), nullable=True),
        sa.Column("rubric", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, server_default="scheduled"),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("manual_entry_id", sa.Integer(), sa.ForeignKey("manual_interview_entry.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_human_schedule_application_status", "human_interview_schedule", ["application_id", "status"])
    op.create_index("ix_human_schedule_interviewer_time", "human_interview_schedule", ["interviewer_id", "scheduled_at"])


def downgrade() -> None:
    op.drop_index("ix_human_schedule_interviewer_time", table_name="human_interview_schedule")
    op.drop_index("ix_human_schedule_application_status", table_name="human_interview_schedule")
    op.drop_table("human_interview_schedule")
    op.drop_index("uq_ai_stage_review_session", table_name="ai_interview_stage_review")
    op.drop_index("ix_ai_stage_review_application", table_name="ai_interview_stage_review")
    op.drop_table("ai_interview_stage_review")
    op.drop_index("ix_proctor_event_correlation", table_name="proctor_evidence_event")
    op.drop_index("ix_proctor_event_type", table_name="proctor_evidence_event")
    op.drop_index("ix_proctor_event_attempt_at", table_name="proctor_evidence_event")
    op.drop_table("proctor_evidence_event")
    op.drop_index("ix_assessment_response_attempt", table_name="assessment_response")
    op.drop_index("uq_assessment_response_attempt_question", table_name="assessment_response")
    op.drop_table("assessment_response")
    op.drop_index("ix_assessment_question_definition_order", table_name="assessment_question")
    op.drop_table("assessment_question")
    op.drop_constraint("fk_assessment_assignment_definition", "assessment_assignment", type_="foreignkey")
    op.drop_index("uq_assessment_definition_drive_version", table_name="assessment_definition")
    op.drop_index("ix_assessment_definition_drive_active", table_name="assessment_definition")
    op.drop_table("assessment_definition")
    op.drop_index("uq_stage_run_application_stage_attempt", table_name="hiring_pipeline_stage_run")
    op.drop_index("ix_stage_run_status_due", table_name="hiring_pipeline_stage_run")
    op.drop_index("ix_stage_run_candidate_drive", table_name="hiring_pipeline_stage_run")
    op.drop_index("ix_stage_run_application_stage", table_name="hiring_pipeline_stage_run")
    op.drop_table("hiring_pipeline_stage_run")
    op.drop_index("ix_workflow_audit_event_correlation_id", table_name="workflow_audit_event")
    op.drop_index("ix_workflow_audit_event_stage_key", table_name="workflow_audit_event")
    for column in ("previous_event_hash", "event_hash", "source", "policy_version", "correlation_id", "stage_key"):
        op.drop_column("workflow_audit_event", column)
    op.drop_index("ix_assessment_attempt_correlation_id", table_name="assessment_attempt")
    op.drop_column("assessment_attempt", "correlation_id")
    op.drop_column("assessment_attempt", "proctoring_consent_version")
    op.drop_column("assessment_assignment", "policy_version")
    op.drop_column("assessment_assignment", "definition_id")
    op.drop_column("candidate_application", "proctoring_consent_version")
    op.drop_column("candidate_application", "workflow_policy_version")
    op.drop_column("candidate_application", "workflow_policy_snapshot")
