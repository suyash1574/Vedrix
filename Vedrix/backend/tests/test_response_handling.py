"""Tests for interview response validation and turn handling."""

from app.services.interview_engine.response_handling import (
    MAX_ANSWER_CHARS,
    decide_response,
    response_fingerprint,
    response_notice,
    response_state_update,
)


def make_state(**overrides):
    state = {
        "messages": [{"role": "assistant", "content": "Tell me about your project."}],
        "current_question_index": 1,
        "total_responses": 0,
        "turn_id": "q1:r0:m1",
        "awaiting_candidate_response": True,
        "last_response_turn_id": None,
        "last_response_fingerprint": None,
        "last_response_id": None,
        "active_question_id": "2",
    }
    state.update(overrides)
    return state


def test_answer_is_normalized_without_collapsing_newlines():
    result = decide_response(
        {"type": "answer", "data": "  I   designed   an API.  ", "question_id": "2"},
        make_state(),
    )
    assert result.accepted is True
    assert result.content == "I designed an API."
    assert result.reason_code == "accepted"


def test_empty_answer_is_rejected_and_retryable():
    result = decide_response({"type": "answer", "data": "   "}, make_state())
    assert result.accepted is False
    assert result.reason_code == "empty_response"
    assert result.retryable is True
    assert response_notice(result)["accepted"] is False


def test_oversized_answer_is_rejected():
    result = decide_response({"type": "answer", "data": "x" * (MAX_ANSWER_CHARS + 1)}, make_state())
    assert result.accepted is False
    assert result.reason_code == "response_too_long"


def test_wrong_question_id_is_rejected_as_stale():
    result = decide_response(
        {"type": "answer", "data": "A valid answer", "question_id": "1"},
        make_state(),
    )
    assert result.accepted is False
    assert result.reason_code == "stale_question_response"
    assert result.retryable is True


def test_duplicate_response_is_rejected_without_reprocessing():
    content = "A valid answer with enough detail."
    fingerprint = response_fingerprint("answer", content)
    result = decide_response(
        {"type": "answer", "data": content, "response_id": "resp-1", "question_id": "2"},
        make_state(last_response_fingerprint=fingerprint, last_response_id="resp-1", last_response_turn_id="q1:r0:m1"),
    )
    assert result.accepted is False
    assert result.reason_code == "duplicate_response"
    assert result.retryable is False


def test_accepted_response_claims_the_turn():
    result = decide_response(
        {"type": "code", "data": "def solve():\n    return 1", "response_id": "resp-2", "question_id": "2"},
        make_state(),
    )
    update = response_state_update(result)
    assert result.accepted is True
    assert update["awaiting_candidate_response"] is False
    assert update["last_response_kind"] == "code"
    assert update["last_response_id"] == "resp-2"
