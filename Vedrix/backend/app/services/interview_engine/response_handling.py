"""Validation and deduplication rules for candidate interview responses."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Any, Mapping, Optional

from .coordination import build_turn_id


MAX_ANSWER_CHARS = 20_000
MAX_CODE_CHARS = 50_000
SUPPORTED_RESPONSE_TYPES = {"answer", "code"}
THINKING_PHRASES = (
    "hmm",
    "let me think",
    "give me a moment",
    "thinking",
    "one second",
    "hold on",
    "give me a second",
)
CLARIFICATION_PHRASES = (
    "can you repeat",
    "could you repeat",
    "please repeat",
    "say that again",
    "what do you mean",
    "can you clarify",
    "could you clarify",
    "i don't understand",
    "i do not understand",
    "not sure what you mean",
)


@dataclass(frozen=True)
class ResponseDecision:
    """Result of validating one client candidate-response message."""

    accepted: bool
    kind: str
    content: str
    reason_code: str
    retryable: bool
    turn_id: str
    fingerprint: str
    client_response_id: Optional[str] = None


def normalize_response(value: Any, *, kind: str) -> str:
    """Normalize user text while preserving code line structure."""
    if not isinstance(value, str):
        raise ValueError("response_data_must_be_string")

    cleaned = value.replace("\x00", "").strip()
    if kind == "answer":
        cleaned = re.sub(r"[ \t]+", " ", cleaned)
        limit = MAX_ANSWER_CHARS
    else:
        limit = MAX_CODE_CHARS

    if not cleaned:
        raise ValueError("empty_response")
    if len(cleaned) > limit:
        raise ValueError("response_too_long")
    return cleaned


def classify_response_intent(content: str) -> str:
    """Classify conversational control intents before scoring the answer."""
    normalized = " ".join(content.lower().split())
    if len(normalized) <= 60 and any(phrase in normalized for phrase in THINKING_PHRASES):
        return "thinking_pause"
    if len(normalized) <= 160 and any(phrase in normalized for phrase in CLARIFICATION_PHRASES):
        return "clarification_request"
    return "answer"


def response_fingerprint(kind: str, content: str) -> str:
    """Return a short stable hash used for same-turn duplicate detection."""
    digest = hashlib.sha256(f"{kind}:\n{content}".encode("utf-8")).hexdigest()
    return digest[:24]


def decide_response(payload: Mapping[str, Any], state: Mapping[str, Any]) -> ResponseDecision:
    """Validate and deduplicate a candidate response against the current turn."""
    kind = str(payload.get("type") or "")
    turn_id = str(state.get("turn_id") or build_turn_id(state))

    if kind not in SUPPORTED_RESPONSE_TYPES:
        return ResponseDecision(False, kind, "", "unsupported_response_type", True, turn_id, "")

    try:
        content = normalize_response(payload.get("data"), kind=kind)
    except ValueError as exc:
        return ResponseDecision(False, kind, "", str(exc), True, turn_id, "")

    if state.get("awaiting_candidate_response") is False:
        return ResponseDecision(False, kind, content, "response_not_expected", True, turn_id, "")

    expected_question_id = state.get("active_question_id")
    submitted_question_id = payload.get("question_id")
    if expected_question_id is not None and submitted_question_id is not None:
        if str(expected_question_id) != str(submitted_question_id):
            return ResponseDecision(False, kind, content, "stale_question_response", True, turn_id, "")

    fingerprint = response_fingerprint(kind, content)
    client_response_id = payload.get("response_id") or payload.get("id")
    if client_response_id is not None:
        client_response_id = str(client_response_id)

    same_turn = str(state.get("last_response_turn_id") or "") == turn_id
    duplicate_id = bool(client_response_id) and same_turn and client_response_id == state.get("last_response_id")
    duplicate_content = same_turn and fingerprint == state.get("last_response_fingerprint")
    if duplicate_id or duplicate_content:
        return ResponseDecision(
            False,
            kind,
            content,
            "duplicate_response",
            False,
            turn_id,
            fingerprint,
            client_response_id,
        )

    return ResponseDecision(
        True,
        kind,
        content,
        "accepted",
        False,
        turn_id,
        fingerprint,
        client_response_id,
    )


def response_state_update(decision: ResponseDecision) -> dict[str, Any]:
    """Build the state mutation that claims a response for the current turn."""
    return {
        "awaiting_candidate_response": False,
        "last_response_turn_id": decision.turn_id,
        "last_response_fingerprint": decision.fingerprint,
        "last_response_id": decision.client_response_id,
        "last_response_kind": decision.kind,
    }


def response_notice(decision: ResponseDecision) -> dict[str, Any]:
    """Build a stable client acknowledgement/rejection payload."""
    return {
        "turn_id": decision.turn_id,
        "response_type": decision.kind,
        "reason_code": decision.reason_code,
        "retryable": decision.retryable,
        "accepted": decision.accepted,
    }
