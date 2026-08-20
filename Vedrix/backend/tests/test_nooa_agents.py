"""Tests for the NVIDIA NOOA migration boundary."""

import pytest

from app.services.nooa_agents import (
    AnswerEvaluationRequest,
    InterviewContext,
    InterviewQuestion,
    QuestionPlanRequest,
)
from app.services.nooa_agents.adapter import _fallback_question
from app.services.interview_engine import nooa_nodes


@pytest.mark.asyncio
async def test_nooa_interviewer_node_translates_typed_question(monkeypatch):
    async def fake_plan_question(request):
        assert request.context.role == "Backend Engineer"
        assert request.context.skills_to_cover == ["Python"]
        return InterviewQuestion(
            question="How would you make a Python API idempotent?",
            category="technical",
            skill_tested="Python",
            difficulty="medium",
            rationale="synthetic test result",
        )

    monkeypatch.setattr(
        nooa_nodes.nooa_interview_adapter,
        "plan_question",
        fake_plan_question,
    )
    result = await nooa_nodes.nooa_interviewer_node(
        {
            "messages": [],
            "job_role": "Backend Engineer",
            "current_phase": "technical",
            "difficulty": "medium",
            "skills_to_cover": ["Python"],
            "covered_skills": [],
            "pending_skills": ["Python"],
            "current_question_index": 0,
            "max_questions": 10,
            "supervisor_mode": "monitor",
            "qa_paused": False,
        }
    )
    assert result["next_question"]["question"].startswith("How would you")
    assert result["next_question"]["skill_tested"] == "Python"
    assert result["next_question"]["id"] == 1


@pytest.mark.asyncio
async def test_nooa_evaluator_node_preserves_policy_for_short_answer(monkeypatch):
    called = False

    async def should_not_call(request):
        nonlocal called
        called = True
        raise AssertionError("short answers must use deterministic policy")

    monkeypatch.setattr(
        nooa_nodes,
        "evaluate_answer_node",
        lambda state: {"last_evaluation": {"low_effort": True}},
    )
    monkeypatch.setattr(
        nooa_nodes.nooa_interview_adapter,
        "evaluate_answer",
        should_not_call,
    )
    result = await nooa_nodes.nooa_evaluator_node(
        {
            "messages": [{"role": "user", "content": "yes"}],
            "next_question": {"question": "Explain Python", "skill_tested": "Python"},
        }
    )
    assert result["last_evaluation"]["low_effort"] is True
    assert called is False


def test_fallback_question_is_bounded_and_targets_pending_skill():
    request = QuestionPlanRequest(
        context=InterviewContext(
            role="Data Engineer",
            phase="technical",
            difficulty="hard",
            skills_to_cover=["SQL", "Python"],
            covered_skills=["SQL"],
        ),
        question_number=2,
        max_questions=10,
    )
    result = _fallback_question(request)
    assert result.skill_tested == "Python"
    assert result.difficulty == "hard"
    assert 8 <= len(result.question) <= 1200
    assert result.rationale.startswith("Deterministic fallback")
