"""Tests for the end-to-end recruiter-controlled hiring workflow primitives."""

from types import SimpleNamespace

import pytest

from app.models.hiring_workflow import CandidateApplication
from app.services.hiring_workflow_service import score_application_against_drive
from app.services.orchestrator_service import WORKFLOW_TRANSITIONS


def test_jd_match_score_is_explainable_and_bounded():
    drive = SimpleNamespace(
        title="Senior Python Engineer",
        description="Build reliable APIs and distributed systems.",
        job_role="Backend Engineer",
        experience_required="5 years",
        skills_required="Python FastAPI PostgreSQL Redis",
    )
    application = CandidateApplication(
        candidate_id=1,
        job_drive_id=1,
        resume_text="I built Python and FastAPI APIs with PostgreSQL and Redis.",
        form_data={"portfolio": "distributed systems"},
    )
    result = score_application_against_drive(drive, application)
    assert 0 <= result["score"] <= 100
    assert result["method"] == "deterministic_token_overlap_v1"
    assert "python" in result["matched_terms"]
    assert isinstance(result["missing_terms"], list)


def test_expanded_workflow_keeps_legacy_path():
    assert WORKFLOW_TRANSITIONS["invited"]["schedule"] == "scheduled"
    assert WORKFLOW_TRANSITIONS["scheduled"]["start"] == "in_progress"
    assert WORKFLOW_TRANSITIONS["in_progress"]["complete"] == "evaluated"
    assert WORKFLOW_TRANSITIONS["evaluated"]["shortlist"] == "shortlisted"
    assert WORKFLOW_TRANSITIONS["shortlisted"]["hire"] == "decided"


def test_application_to_assessment_to_cheat_review_path():
    assert WORKFLOW_TRANSITIONS["screening"]["assign_assessment"] == "assessment_assigned"
    assert WORKFLOW_TRANSITIONS["assessment_assigned"]["start"] == "assessment_in_progress"
    assert WORKFLOW_TRANSITIONS["assessment_in_progress"]["complete"] == "assessment_review"
    assert WORKFLOW_TRANSITIONS["assessment_review"]["flag_cheat"] == "cheat_review"
    assert WORKFLOW_TRANSITIONS["cheat_review"]["clear"] == "interview_scheduled"
    assert WORKFLOW_TRANSITIONS["cheat_review"]["confirm_cheat"] == "decided"


def test_recruiter_can_route_around_assessment_for_manual_interview():
    assert WORKFLOW_TRANSITIONS["screening"]["skip_assessment"] == "interview_scheduled"
    assert WORKFLOW_TRANSITIONS["screening"]["manual_interview"] == "manual_interview"
    assert WORKFLOW_TRANSITIONS["assessment_review"]["manual_interview"] == "manual_interview"


def test_recruiter_decision_is_not_implied_by_proctor_signal():
    # A suspected signal only enters review; a human must explicitly confirm it.
    assert WORKFLOW_TRANSITIONS["assessment_review"]["flag_cheat"] == "cheat_review"
    assert WORKFLOW_TRANSITIONS["cheat_review"]["confirm_cheat"] == "decided"
    assert WORKFLOW_TRANSITIONS["cheat_review"]["clear"] == "interview_scheduled"
