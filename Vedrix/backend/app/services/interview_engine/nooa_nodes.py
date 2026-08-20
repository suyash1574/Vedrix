"""LangGraph wrappers for NVIDIA Object-Oriented Agents (NOOA).

The graph remains the source of truth. These nodes translate the existing
InterviewState into typed NOOA requests and translate validated outputs back
into the state fields consumed by downstream QA, sentiment, debate, and
supervisor nodes.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict

from .state import InterviewState
from .response_handling import classify_response_intent
from .nodes import generate_question_node, evaluate_answer_node
from ..nooa_agents import (
    AnswerEvaluationRequest,
    InterviewContext,
    QuestionPlanRequest,
    nooa_interview_adapter,
)

logger = logging.getLogger(__name__)


def _context_from_state(state: InterviewState) -> InterviewContext:
    messages = state.get("messages") or []
    prior_questions = [
        str(item.get("content") or "")[:1200]
        for item in messages
        if isinstance(item, dict) and item.get("role") == "assistant"
    ][-20:]
    prior_answers = [
        str(item.get("content") or "")[:12000]
        for item in messages
        if isinstance(item, dict) and item.get("role") == "user"
    ][-20:]
    return InterviewContext(
        role=state.get("job_role") or "Software Engineer",
        phase=state.get("current_phase") or "technical",
        difficulty=state.get("difficulty") or "medium",
        skills_to_cover=list(state.get("skills_to_cover") or [])[:32],
        covered_skills=list(state.get("covered_skills") or [])[:32],
        prior_questions=prior_questions,
        prior_answers=prior_answers,
        rubric_version="vedrix-v1",
    )


def _latest_answer(state: InterviewState) -> str:
    explicit = state.get("last_candidate_answer")
    if explicit:
        return str(explicit)
    for message in reversed(state.get("messages") or []):
        if isinstance(message, dict) and message.get("role") == "user":
            return str(message.get("content") or "")
    return ""


async def nooa_interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """Generate the next question with a typed NOOA planner."""
    if state.get("supervisor_mode") == "hr_takeover" or state.get("qa_paused"):
        return await _call_fallback(generate_question_node, state)

    context = _context_from_state(state)
    index = int(state.get("current_question_index") or 0)
    request = QuestionPlanRequest(
        context=context,
        question_number=index + 1,
        max_questions=int(state.get("max_questions") or 10),
        last_answer=_latest_answer(state)[-12000:],
    )
    question = await nooa_interview_adapter.plan_question(request)
    return {
        "next_question": {
            "id": index + 1,
            "question": question.question,
            "category": question.category,
            "difficulty": question.difficulty,
            "time_limit": 600,
            "skill_tested": question.skill_tested,
            "follow_up_topic": question.skill_tested,
            "follow_up": question.follow_up,
            "rationale": question.rationale,
        },
        "current_phase": context.phase,
        "difficulty": question.difficulty,
    }


async def _call_fallback(fn, state: InterviewState) -> Dict[str, Any]:
    result = fn(state)
    if asyncio.iscoroutine(result):
        return await result
    return result


async def nooa_evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """Evaluate one substantive answer with a typed NOOA evaluator."""
    # Preserve the existing deterministic protections for pauses and extremely
    # short answers. They are product policy, not model decisions.
    answer = _latest_answer(state)
    response_intent = classify_response_intent(answer)
    if response_intent in {"thinking_pause", "clarification_request"}:
        is_clarification = response_intent == "clarification_request"
        return {
            "last_evaluation": {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "topic": response_intent,
                "skill_category": "behavioral",
                "should_deep_dive": False,
                "needs_easier": False,
                "low_effort": False,
                "is_thinking_pause": not is_clarification,
                "is_clarification_request": is_clarification,
                "skill_identified": "patience" if not is_clarification else "clarification",
            },
            "latest_score": 5.0,
            "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
            "total_responses": int(state.get("total_responses") or 0),
            "follow_up_requested": is_clarification,
        }
    if len(answer.strip()) < 15:
        return await _call_fallback(evaluate_answer_node, state)

    last_question = state.get("next_question") or {}
    if not isinstance(last_question, dict) or not last_question.get("question"):
        return await _call_fallback(evaluate_answer_node, state)

    request = AnswerEvaluationRequest(
        context=_context_from_state(state),
        question=str(last_question.get("question") or ""),
        answer=answer[-20000:],
        expected_skill=str(last_question.get("skill_tested") or "general reasoning"),
    )
    evaluation = await nooa_interview_adapter.evaluate_answer(request)
    metrics = {
        "accuracy": round(evaluation.correctness, 2),
        "clarity": round(evaluation.communication, 2),
        "depth": round(evaluation.depth, 2),
        "communication": round(evaluation.communication, 2),
    }
    score = round(sum(metrics.values()) / len(metrics), 2)
    evaluation_record = {
        "score": score,
        "metrics": metrics,
        "topic": str(last_question.get("category") or "general"),
        "skill_category": str(last_question.get("category") or "general"),
        "skill_identified": str(last_question.get("skill_tested") or "general"),
        "should_deep_dive": score >= 7.5,
        "needs_easier": score < 4.0,
        "low_effort": False,
        "is_thinking_pause": False,
        "evidence": evaluation.evidence,
        "strengths": evaluation.strengths,
        "gaps": evaluation.gaps,
        "next_step": evaluation.next_step,
        "confidence": evaluation.confidence,
        "agent_framework": "nooa",
        "question": str(last_question.get("question") or ""),
    }
    return {
        "last_evaluation": evaluation_record,
        "evaluation_history": [*(state.get("evaluation_history") or [])[-99:], evaluation_record],
        "latest_score": score,
        "metrics": metrics,
        "total_responses": int(state.get("total_responses") or 0) + 1,
        "high_quality_count": int(state.get("high_quality_count") or 0) + (1 if score >= 6 else 0),
        "low_quality_count": int(state.get("low_quality_count") or 0),
    }
