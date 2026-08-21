"""Shared coordination protocol for interview agents.

The interview graph is the source of truth, while this module provides stable
identifiers and append-only trace events that let parallel agents coordinate
without overwriting one another's observations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Mapping, Optional


COORDINATION_PROTOCOL_VERSION = "vedrix-coordination-v1"


def build_turn_id(state: Mapping[str, Any]) -> str:
    """Build a deterministic identifier for the candidate response under review."""
    explicit = state.get("turn_id")
    if explicit:
        return str(explicit)
    question_index = int(state.get("current_question_index") or 0)
    response_count = int(state.get("total_responses") or 0)
    message_count = len(state.get("messages") or [])
    return f"q{question_index}:r{response_count}:m{message_count}"


def build_debate_round_id(state: Mapping[str, Any]) -> str:
    """Build the unique coordination key for one parallel debate fan-out."""
    existing = state.get("coordination_round_id")
    if existing:
        return str(existing)
    return f"{build_turn_id(state)}:debate"


def coordination_event(
    *,
    agent: str,
    event: str,
    state: Mapping[str, Any],
    status: str = "completed",
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a compact, serializable event for the append-only trace."""
    payload: Dict[str, Any] = {
        "protocol_version": COORDINATION_PROTOCOL_VERSION,
        "event_id": f"{build_turn_id(state)}:{agent}:{event}",
        "turn_id": build_turn_id(state),
        "round_id": state.get("coordination_round_id"),
        "agent": agent,
        "event": event,
        "status": status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if details:
        payload["details"] = details
    return payload


def supervisor_action_update(
    *,
    state: Mapping[str, Any],
    action: Mapping[str, Any],
    control_mode: str,
) -> Dict[str, Any]:
    """Translate a supervisor recommendation into graph-safe state updates.

    Suggestions are observable but only ``auto`` mode mutates interview control
    fields. This keeps ReAct and deterministic supervisors behaviorally aligned.
    """
    action_type = str(action.get("action_type") or "no_action")
    payload = action.get("payload") or {}
    confidence = float(action.get("confidence") or 0.0)
    normalized = {
        "action_type": action_type,
        "confidence": max(0.0, min(1.0, confidence)),
        "reason": str(action.get("reason") or ""),
        "reason_category": str(action.get("reason_category") or "no_action"),
        "payload": dict(payload) if isinstance(payload, Mapping) else {},
    }
    update: Dict[str, Any] = {
        "supervisor_last_action": normalized,
        "coordination_trace": [
            coordination_event(
                agent="supervisor",
                event="action_recommended",
                state=state,
                details={"action": normalized, "control_mode": control_mode},
            )
        ],
    }

    if action_type == "suggest_close" and not state.get("advisor_action_taken", False):
        update.update(
            {
                "advisor_ready_to_close": True,
                "advisor_confidence": normalized["confidence"],
                "advisor_reason": normalized["reason"],
                "advisor_reason_category": normalized["reason_category"],
            }
        )

    if control_mode == "auto":
        if action_type == "adjust_difficulty":
            new_difficulty = payload.get("new_difficulty")
            if new_difficulty in {"easy", "medium", "hard"} and new_difficulty != state.get("difficulty"):
                history = list(state.get("difficulty_history") or [])
                update["difficulty"] = new_difficulty
                update["difficulty_history"] = history + [new_difficulty]
        elif action_type in {"pause_interview", "force_pause"}:
            update["supervisor_paused"] = True
        elif action_type == "force_close":
            update["interview_complete"] = True
            update["completion_reason"] = normalized["reason"] or "Supervisor forced interview closure"

        update["supervisor_override"] = {
            "action": action_type,
            "confidence": normalized["confidence"],
            "reason": normalized["reason"],
            "payload": normalized["payload"],
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "auto_executed": action_type != "no_action",
        }

    return update
