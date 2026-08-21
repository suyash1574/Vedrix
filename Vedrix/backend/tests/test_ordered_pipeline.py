"""Regression coverage for the ordered online-test → AI → human pipeline."""

import pytest

from app.services.hiring_workflow_service import (
    assert_human_stage_gate,
    normalize_pipeline_policy,
)
from app.services.orchestrator_service import WORKFLOW_TRANSITIONS


def test_default_pipeline_order_is_assessment_ai_then_human():
    policy = normalize_pipeline_policy(None)
    assert policy["stage_order"] == ["assessment", "ai_interview", "human_interview"]
    assert policy["ai_interview_recruiter_approval_required"] is True


def test_policy_rejects_ai_after_human():
    with pytest.raises(ValueError, match="AI interview must occur before human interview"):
        normalize_pipeline_policy({"stage_order": ["assessment", "human_interview", "ai_interview"]})


def test_policy_rejects_required_disabled_stage():
    with pytest.raises(ValueError, match="assessment_required"):
        normalize_pipeline_policy({"assessment_enabled": False, "assessment_required": True})


def test_human_interview_is_blocked_before_ai_review():
    with pytest.raises(ValueError, match="before the AI interview"):
        assert_human_stage_gate("assessment_review")
    assert_human_stage_gate("ai_interview_review") is None
    assert_human_stage_gate("assessment_review", override=True) is None


def test_explicit_ai_and_human_states_are_connected():
    assert WORKFLOW_TRANSITIONS["assessment_review"]["pass_to_ai"] == "ai_interview_scheduled"
    assert WORKFLOW_TRANSITIONS["ai_interview_scheduled"]["start"] == "ai_interview_in_progress"
    assert WORKFLOW_TRANSITIONS["ai_interview_in_progress"]["complete"] == "ai_interview_review"
    assert WORKFLOW_TRANSITIONS["ai_interview_review"]["approve_human"] == "human_interview_scheduled"
    assert WORKFLOW_TRANSITIONS["human_interview"]["submit"] == "final_review"
    assert WORKFLOW_TRANSITIONS["final_review"]["hire"] == "decided"
