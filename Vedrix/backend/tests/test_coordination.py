"""Regression tests for the multi-agent coordination protocol."""

import pytest

from app.services.interview_engine.coordination import (
    build_debate_round_id,
    build_turn_id,
    coordination_event,
    supervisor_action_update,
)
from app.services.interview_engine.nodes import debate_router_node


@pytest.fixture
def coordination_state():
    return {
        "messages": [
            {"role": "assistant", "content": "Explain caching."},
            {"role": "user", "content": "Caching stores reusable results."},
        ],
        "current_question_index": 3,
        "total_responses": 2,
        "turn_id": None,
        "coordination_round_id": None,
        "difficulty": "medium",
        "difficulty_history": ["medium"],
        "advisor_action_taken": False,
        "supervisor_mode": "suggest",
    }


def test_turn_and_round_ids_are_stable(coordination_state):
    assert build_turn_id(coordination_state) == "q3:r2:m2"
    assert build_debate_round_id(coordination_state) == "q3:r2:m2:debate"
    seeded = {**coordination_state, "turn_id": "turn-fixed", "coordination_round_id": "round-fixed"}
    assert build_turn_id(seeded) == "turn-fixed"
    assert build_debate_round_id(seeded) == "round-fixed"


@pytest.mark.asyncio
async def test_debate_router_starts_shared_round(coordination_state):
    result = await debate_router_node(coordination_state)
    assert result["coordination_round_id"] == "q3:r2:m2:debate"
    assert result["debate_rounds"]["status"] == "running"
    assert result["debate_rounds"]["expected_agents"] == ["skeptic", "pragmatist", "bias_auditor"]
    assert result["coordination_trace"][0]["event"] == "debate_started"
    assert result["coordination_trace"][0]["round_id"] == "q3:r2:m2:debate"


def test_coordination_event_is_serializable(coordination_state):
    event = coordination_event(
        agent="qa",
        event="question_approved",
        state={**coordination_state, "coordination_round_id": "q3:r2:m2:debate"},
        details={"approved": True},
    )
    assert event["event_id"] == "q3:r2:m2:qa:question_approved"
    assert event["protocol_version"] == "vedrix-coordination-v1"
    assert event["details"] == {"approved": True}


def test_supervisor_suggest_mode_is_observable_but_non_mutating(coordination_state):
    result = supervisor_action_update(
        state=coordination_state,
        action={
            "action_type": "adjust_difficulty",
            "confidence": 0.8,
            "reason": "Three strong answers",
            "reason_category": "performance_improving",
            "payload": {"new_difficulty": "hard"},
        },
        control_mode="suggest",
    )
    assert result["supervisor_last_action"]["action_type"] == "adjust_difficulty"
    assert "difficulty" not in result
    assert "supervisor_override" not in result
    assert result["coordination_trace"][0]["event"] == "action_recommended"


def test_supervisor_auto_mode_applies_safe_mutation(coordination_state):
    result = supervisor_action_update(
        state={**coordination_state, "supervisor_mode": "auto"},
        action={
            "action_type": "adjust_difficulty",
            "confidence": 1.4,
            "reason": "Three strong answers",
            "reason_category": "performance_improving",
            "payload": {"new_difficulty": "hard"},
        },
        control_mode="auto",
    )
    assert result["difficulty"] == "hard"
    assert result["difficulty_history"] == ["medium", "hard"]
    assert result["supervisor_override"]["auto_executed"] is True
    assert result["supervisor_last_action"]["confidence"] == 1.0


def test_supervisor_auto_mode_can_close_interview(coordination_state):
    result = supervisor_action_update(
        state={**coordination_state, "supervisor_mode": "auto"},
        action={
            "action_type": "force_close",
            "confidence": 0.9,
            "reason": "Maximum duration reached",
            "reason_category": "time_overrun",
            "payload": {},
        },
        control_mode="auto",
    )
    assert result["interview_complete"] is True
    assert result["completion_reason"] == "Maximum duration reached"
