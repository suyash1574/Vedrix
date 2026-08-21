"""NVIDIA Object-Oriented Agents integration for Vedrix.

NOOA is intentionally isolated behind this module.  The current LangGraph
engine, WebSocket protocol, persistence layer, and frontend do not need to
know whether a result came from NOOA or the existing fallback services.

The first rollout uses NOOA's typed PREDICT strategy for bounded structured
outputs.  It does not expose shell, filesystem, network, database, or browser
capabilities to the model.  Every public method has a deterministic fallback
so a research-preview dependency or provider failure cannot lose an answer.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.core.config import settings

logger = logging.getLogger(__name__)

try:  # NOOA is optional during the migration and local test collection.
    from nooa import Agent, strategy
    from nooa.strategies import PredictStrategy
    from nooa.unifiedllm.registry import get_llm_client

    NOOA_AVAILABLE = True
except Exception:  # pragma: no cover - exercised in minimal environments.
    Agent = object  # type: ignore[misc,assignment]
    strategy = None  # type: ignore[assignment]
    PredictStrategy = None  # type: ignore[assignment]
    get_llm_client = None  # type: ignore[assignment]
    NOOA_AVAILABLE = False


class InterviewContext(BaseModel):
    """Minimal, redacted context exposed to an interview agent."""

    role: str = "Software Engineer"
    phase: str = "technical"
    difficulty: Literal["easy", "medium", "hard"] = "medium"
    skills_to_cover: list[str] = Field(default_factory=list, max_length=32)
    covered_skills: list[str] = Field(default_factory=list, max_length=32)
    prior_questions: list[str] = Field(default_factory=list, max_length=20)
    prior_answers: list[str] = Field(default_factory=list, max_length=20)
    rubric_version: str = "vedrix-v1"


class QuestionPlanRequest(BaseModel):
    context: InterviewContext
    question_number: int = Field(ge=1, le=100)
    max_questions: int = Field(ge=1, le=100)
    last_answer: str = Field(default="", max_length=12000)


class InterviewQuestion(BaseModel):
    question: str = Field(min_length=8, max_length=1200)
    category: str = Field(min_length=2, max_length=80)
    skill_tested: str = Field(min_length=2, max_length=120)
    difficulty: Literal["easy", "medium", "hard"]
    follow_up: bool = False
    rationale: str = Field(default="", max_length=800)


class AnswerEvaluationRequest(BaseModel):
    context: InterviewContext
    question: str = Field(min_length=1, max_length=1200)
    answer: str = Field(min_length=1, max_length=20000)
    expected_skill: str = Field(default="general reasoning", max_length=120)


class AnswerEvaluation(BaseModel):
    correctness: float = Field(ge=0, le=10)
    relevance: float = Field(ge=0, le=10)
    depth: float = Field(ge=0, le=10)
    communication: float = Field(ge=0, le=10)
    evidence: list[str] = Field(min_length=1, max_length=6)
    strengths: list[str] = Field(default_factory=list, max_length=6)
    gaps: list[str] = Field(default_factory=list, max_length=6)
    next_step: str = Field(min_length=4, max_length=600)
    confidence: float = Field(ge=0, le=1)


class ReportRequest(BaseModel):
    context: InterviewContext
    evaluations: list[AnswerEvaluation] = Field(min_length=1, max_length=100)


class InterviewReport(BaseModel):
    overall_score: float = Field(ge=0, le=10)
    summary: str = Field(min_length=10, max_length=2000)
    strengths: list[str] = Field(default_factory=list, max_length=8)
    development_areas: list[str] = Field(default_factory=list, max_length=8)
    action_plan: list[str] = Field(min_length=1, max_length=8)
    rubric_version: str
    evaluation_count: int = Field(ge=1, le=100)


class CoachingRequest(BaseModel):
    context: InterviewContext
    report: InterviewReport


class CoachingPlan(BaseModel):
    priorities: list[str] = Field(min_length=1, max_length=6)
    exercises: list[str] = Field(min_length=1, max_length=8)
    rationale: str = Field(min_length=10, max_length=1200)


def _nooa_enabled() -> bool:
    """Feature flag NOOA independently from the availability of the package."""

    configured = os.getenv("NOOA_ENABLED", str(settings.NOOA_ENABLED)).strip().lower()
    return configured not in {"0", "false", "off", "no"} and bool(settings.NVIDIA_API_KEY)


def _build_nooa_llm() -> Any:
    """Create a NVIDIA NIM-backed NOOA client without exposing credentials."""

    if not NOOA_AVAILABLE or get_llm_client is None or not settings.NVIDIA_API_KEY:
        return None

    model = os.getenv("NOOA_MODEL", settings.NOOA_MODEL)
    return get_llm_client(model, api_key=settings.NVIDIA_API_KEY)


_NOOA_LLM = _build_nooa_llm() if _nooa_enabled() else None


if NOOA_AVAILABLE and _NOOA_LLM is not None:

    class _QuestionPlannerAgent(Agent, llm=_NOOA_LLM):  # type: ignore[misc,valid-type]
        """Generate one bounded interview question from typed context."""

        @strategy(PredictStrategy())
        async def plan_next_question(self, request: QuestionPlanRequest) -> InterviewQuestion:
            """Choose the next role-relevant question; never invent capabilities or tools."""
            ...

    class _AnswerEvaluatorAgent(Agent, llm=_NOOA_LLM):  # type: ignore[misc,valid-type]
        """Evaluate one answer against the Vedrix rubric."""

        @strategy(PredictStrategy())
        async def evaluate(self, request: AnswerEvaluationRequest) -> AnswerEvaluation:
            """Return evidence-backed scores and coaching, not a hiring decision."""
            ...

    class _ReportAgent(Agent, llm=_NOOA_LLM):  # type: ignore[misc,valid-type]
        """Aggregate validated answer evaluations into a candidate report."""

        @strategy(PredictStrategy())
        async def generate_report(self, request: ReportRequest) -> InterviewReport:
            """Summarize only the supplied evaluations and preserve the rubric version."""
            ...

    class _CoachingAgent(Agent, llm=_NOOA_LLM):  # type: ignore[misc,valid-type]
        """Create a focused practice plan from a validated interview report."""

        @strategy(PredictStrategy())
        async def create_plan(self, request: CoachingRequest) -> CoachingPlan:
            """Produce concrete exercises without making employment recommendations."""
            ...

else:
    _QuestionPlannerAgent = None  # type: ignore[assignment,misc]
    _AnswerEvaluatorAgent = None  # type: ignore[assignment,misc]
    _ReportAgent = None  # type: ignore[assignment,misc]
    _CoachingAgent = None  # type: ignore[assignment,misc]


def _fallback_question(request: QuestionPlanRequest) -> InterviewQuestion:
    context = request.context
    skill = next(
        (skill for skill in context.skills_to_cover if skill not in context.covered_skills),
        "problem solving",
    )
    follow_up = bool(request.last_answer.strip())
    if follow_up:
        question = (
            f"You mentioned: {request.last_answer[:240]}. What trade-off or concrete result "
            f"would you add to make that example stronger?"
        )
    else:
        question = (
            f"For a {context.role} role, describe a recent situation where you used "
            f"{skill}. What was your reasoning, and what was the outcome?"
        )
    return InterviewQuestion(
        question=question,
        category=context.phase,
        skill_tested=skill,
        difficulty=context.difficulty,
        follow_up=follow_up,
        rationale="Deterministic fallback used because the NOOA provider was unavailable.",
    )


def _fallback_evaluation(request: AnswerEvaluationRequest) -> AnswerEvaluation:
    answer = request.answer.strip()
    words = len(answer.split())
    detail = min(10.0, max(2.0, words / 18.0))
    evidence = [answer[:500]] if answer else ["No answer text was received."]
    return AnswerEvaluation(
        correctness=detail,
        relevance=min(10.0, detail + 0.5),
        depth=detail,
        communication=min(10.0, max(2.0, detail + 0.5)),
        evidence=evidence,
        strengths=["The response was captured successfully."] if answer else [],
        gaps=["Add a concrete example, decision, and measurable result."],
        next_step="Use a concise situation, action, trade-off, and outcome structure.",
        confidence=0.25,
    )


def _fallback_report(request: ReportRequest) -> InterviewReport:
    evaluations = request.evaluations
    overall = sum(
        (item.correctness + item.relevance + item.depth + item.communication) / 4
        for item in evaluations
    ) / len(evaluations)
    strengths = [item for evaluation in evaluations for item in evaluation.strengths][:4]
    gaps = [item for evaluation in evaluations for item in evaluation.gaps][:4]
    return InterviewReport(
        overall_score=round(overall, 2),
        summary="The report was generated from validated per-answer evaluations.",
        strengths=strengths or ["Completed the available interview responses."],
        development_areas=gaps or ["Continue practicing evidence-backed answers."],
        action_plan=[
            "Practice one role-specific answer using situation, action, and outcome.",
            "Review the evidence attached to each lower-scoring dimension.",
        ],
        rubric_version=request.context.rubric_version,
        evaluation_count=len(evaluations),
    )


class NooaInterviewAdapter:
    """Application-facing NOOA adapter with per-operation budgets and safe fallbacks."""

    def __init__(self, timeout_seconds: float | None = None):
        self.timeout_seconds = timeout_seconds or float(getattr(settings, "INTERVIEW_TURN_TIMEOUT_SECONDS", 20.0))
        self._question_agent = None
        self._evaluation_agent = None
        self._report_agent = None
        self._coaching_agent = None

    def _timeout(self, operation: str) -> float:
        configured = {
            "question": getattr(settings, "INTERVIEW_QUESTION_TIMEOUT_SECONDS", 10.0),
            "evaluation": getattr(settings, "INTERVIEW_EVALUATION_TIMEOUT_SECONDS", 12.0),
            "report": max(self.timeout_seconds, 20.0),
            "coaching": max(self.timeout_seconds, 20.0),
        }.get(operation, self.timeout_seconds)
        return max(1.0, min(float(configured), self.timeout_seconds if operation in {"question", "evaluation"} else float(configured)))

    @property
    def enabled(self) -> bool:
        return bool(_NOOA_LLM and _nooa_enabled())

    async def plan_question(self, request: QuestionPlanRequest) -> InterviewQuestion:
        if not self.enabled or _QuestionPlannerAgent is None:
            return _fallback_question(request)
        try:
            if self._question_agent is None:
                self._question_agent = _QuestionPlannerAgent()
            return await asyncio.wait_for(
                self._question_agent.plan_next_question(request), timeout=self._timeout("question")
            )
        except Exception:
            logger.exception("NOOA question planning failed; using deterministic fallback")
            return _fallback_question(request)

    async def evaluate_answer(self, request: AnswerEvaluationRequest) -> AnswerEvaluation:
        if not self.enabled or _AnswerEvaluatorAgent is None:
            return _fallback_evaluation(request)
        try:
            if self._evaluation_agent is None:
                self._evaluation_agent = _AnswerEvaluatorAgent()
            return await asyncio.wait_for(
                self._evaluation_agent.evaluate(request), timeout=self._timeout("evaluation")
            )
        except Exception:
            logger.exception("NOOA answer evaluation failed; using deterministic fallback")
            return _fallback_evaluation(request)

    async def generate_report(self, request: ReportRequest) -> InterviewReport:
        if not self.enabled or _ReportAgent is None:
            return _fallback_report(request)
        try:
            if self._report_agent is None:
                self._report_agent = _ReportAgent()
            return await asyncio.wait_for(
                self._report_agent.generate_report(request), timeout=self._timeout("report")
            )
        except Exception:
            logger.exception("NOOA report generation failed; using deterministic fallback")
            return _fallback_report(request)

    async def create_coaching_plan(self, request: CoachingRequest) -> CoachingPlan:
        if not self.enabled or _CoachingAgent is None:
            report = request.report
            priorities = report.development_areas[:3] or ["Structured communication"]
            return CoachingPlan(
                priorities=priorities,
                exercises=[
                    "Rewrite one answer with a clear situation, action, and outcome.",
                    "Explain one technical trade-off in under two minutes.",
                ],
                rationale="Deterministic fallback coaching plan from the validated report.",
            )
        try:
            if self._coaching_agent is None:
                self._coaching_agent = _CoachingAgent()
            return await asyncio.wait_for(
                self._coaching_agent.create_plan(request), timeout=self._timeout("coaching")
            )
        except Exception:
            logger.exception("NOOA coaching generation failed; using deterministic fallback")
            return CoachingPlan(
                priorities=request.report.development_areas[:3] or ["Structured communication"],
                exercises=["Practice one evidence-backed answer."],
                rationale="Fallback coaching plan generated after a NOOA failure.",
            )


nooa_interview_adapter = NooaInterviewAdapter()
