import json
import logging
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.interview_engine.model_router import get_report_llm
from app.services.nooa_agents import (
    AnswerEvaluation,
    InterviewContext,
    ReportRequest,
    nooa_interview_adapter,
)

logger = logging.getLogger(__name__)


class DetailedEvaluationSchema(BaseModel):
    overall_score: float = Field(description="Final overall score out of 10.0")
    hire_recommendation: str = Field(description="One of: 'Strong Hire', 'Hire', 'Maybe', 'No Hire'")
    technical_accuracy: float = Field(description="Score 0-10 for correctness of answers")
    communication_clarity: float = Field(description="Score 0-10 for clarity and confidence")
    depth_of_knowledge: float = Field(description="Score 0-10 for seniority and depth")
    strengths: List[str] = Field(description="Top 3 technical or behavioral strengths")
    weaknesses: List[str] = Field(description="Key areas for improvement")
    summary: str = Field(description="A concise executive summary for HR")
    agent_framework: str = Field(default="legacy", description="Framework used to create the report")
    rubric_version: str = Field(default="legacy-v1", description="Evaluation rubric version")


def _recommendation(score: float) -> str:
    if score >= 8.5:
        return "Strong Hire"
    if score >= 7.0:
        return "Hire"
    if score >= 5.0:
        return "Maybe"
    return "No Hire"


class EvaluationService:
    def __init__(self):
        self._llm = None

    @property
    def llm(self):
        """Lazily initialize the report generation LLM on first use."""
        if self._llm is None:
            self._llm = get_report_llm()
        return self._llm

    @llm.setter
    def llm(self, value):
        """Allow injection of mock LLM for testing."""
        self._llm = value

    @staticmethod
    def _typed_evaluations(evaluation_history: Optional[List[Dict[str, Any]]]) -> List[AnswerEvaluation]:
        typed: List[AnswerEvaluation] = []
        for item in evaluation_history or []:
            metrics = item.get("metrics") or {}
            try:
                typed.append(
                    AnswerEvaluation(
                        correctness=float(metrics.get("accuracy", item.get("score", 5.0))),
                        relevance=float(metrics.get("accuracy", item.get("score", 5.0))),
                        depth=float(metrics.get("depth", item.get("score", 5.0))),
                        communication=float(metrics.get("communication", metrics.get("clarity", item.get("score", 5.0)))),
                        evidence=[str(value)[:500] for value in (item.get("evidence") or [item.get("question", "")]) if value][:6]
                        or ["No evidence was attached."],
                        strengths=[str(value)[:400] for value in (item.get("strengths") or [])][:6],
                        gaps=[str(value)[:400] for value in (item.get("gaps") or [])][:6],
                        next_step=str(item.get("next_step") or "Continue practicing evidence-backed answers.")[:600],
                        confidence=float(item.get("confidence", 0.5)),
                    )
                )
            except (TypeError, ValueError):
                logger.warning("Skipping malformed evaluation history item")
        return typed

    async def _generate_nooa_report(
        self,
        job_role: str,
        evaluation_history: List[Dict[str, Any]],
    ) -> Optional[DetailedEvaluationSchema]:
        typed = self._typed_evaluations(evaluation_history)
        if not typed or not nooa_interview_adapter.enabled:
            return None
        request = ReportRequest(
            context=InterviewContext(
                role=job_role or "Software Engineer",
                phase="closing",
                difficulty="medium",
                rubric_version="vedrix-v1",
            ),
            evaluations=typed,
        )
        report = await nooa_interview_adapter.generate_report(request)
        return DetailedEvaluationSchema(
            overall_score=report.overall_score,
            hire_recommendation=_recommendation(report.overall_score),
            technical_accuracy=round(sum(item.correctness for item in typed) / len(typed), 2),
            communication_clarity=round(sum(item.communication for item in typed) / len(typed), 2),
            depth_of_knowledge=round(sum(item.depth for item in typed) / len(typed), 2),
            strengths=report.strengths[:3],
            weaknesses=report.development_areas[:6],
            summary=report.summary,
            agent_framework="nooa",
            rubric_version=report.rubric_version,
        )

    async def generate_final_report(
        self,
        job_role: str,
        history: List[Dict[str, str]],
        evaluation_history: Optional[List[Dict[str, Any]]] = None,
    ) -> DetailedEvaluationSchema:
        """Generate a report from NOOA evidence when enabled, with legacy fallback."""
        try:
            nooa_report = await self._generate_nooa_report(job_role, evaluation_history or [])
            if nooa_report is not None:
                return nooa_report
        except Exception:
            logger.exception("NOOA report generation failed; using legacy report path")

        transcript = "\n".join(
            f"{'Interviewer' if m['role'] == 'assistant' else 'Candidate'}: {m['content']}"
            for m in history
        )
        system_prompt = (
            f"You are a principal engineer and expert hiring manager reviewing an AI-led interview "
            f"for the role of {job_role}.\n\n"
            "Provide a deep, clinical analysis. Be objective.\n"
            "OUTPUT FORMAT: Return a valid JSON object matching the requested schema exactly."
        )
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Transcript:\n{transcript}\n\nGenerate the final evaluation report."),
            ])
            content = response.content
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
            parsed = DetailedEvaluationSchema(**json.loads(content))
            return parsed.model_copy(update={"agent_framework": "legacy"})
        except Exception as e:
            logger.error("Final report generation failed: %s", e)
            return DetailedEvaluationSchema(
                overall_score=5.0,
                hire_recommendation="Maybe",
                technical_accuracy=5.0,
                communication_clarity=5.0,
                depth_of_knowledge=5.0,
                strengths=["Completed the session"],
                weaknesses=["Evaluation engine failed — manual review required"],
                summary="AI evaluation failed. Manual review of transcript required.",
                agent_framework="fallback",
            )


evaluation_service = EvaluationService()
