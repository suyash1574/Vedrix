import pytest

from app.services.evaluation_service import EvaluationService
from app.services.nooa_agents import InterviewReport


@pytest.mark.asyncio
async def test_nooa_report_maps_into_legacy_schema(monkeypatch):
    async def fake_report(request):
        assert len(request.evaluations) == 1
        assert request.evaluations[0].correctness == 8
        return InterviewReport(
            overall_score=8.2,
            summary="Evidence-backed report.",
            strengths=["Clear reasoning"],
            development_areas=["Add more measured outcomes"],
            action_plan=["Practice outcome framing"],
            rubric_version="vedrix-v1",
            evaluation_count=1,
        )

    monkeypatch.setattr(
        "app.services.evaluation_service.nooa_interview_adapter.generate_report",
        fake_report,
    )
    service = EvaluationService()
    result = await service.generate_final_report(
        "Backend Engineer",
        [{"role": "assistant", "content": "Q"}, {"role": "user", "content": "A"}],
        evaluation_history=[
            {
                "score": 8,
                "metrics": {"accuracy": 8, "depth": 8, "communication": 8},
                "evidence": ["The candidate described a concrete trade-off."],
                "strengths": ["Clear reasoning"],
                "gaps": ["Add more measured outcomes"],
                "next_step": "Quantify the result.",
                "confidence": 0.9,
            }
        ],
    )
    assert result.agent_framework == "nooa"
    assert result.rubric_version == "vedrix-v1"
    assert result.overall_score == 8.2
    assert result.hire_recommendation == "Hire"
