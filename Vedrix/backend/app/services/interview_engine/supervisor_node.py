"""AI Supervisor LangGraph Node.

Runs after update_memory in the interview graph loop. Analyzes:
  1. Duration — per-question and total elapsed time
  2. Difficulty — progression, anomalies, stuck detection
  3. Performance — score trends, fatigue, diminishing returns
  4. Skill coverage — breadth and depth

Depending on supervisor_mode, it can:
  - "monitor": Log observations only, never takes action
  - "suggest": Logs observations + suggests actions (advisor badge on dashboard)
  - "auto": Logs observations + automatically executes actions

The node emits a supervisor_observation dict that the WebSocket handler forwards
to the client and persists to the supervisor_registry.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from .state import InterviewState
from .coordination import coordination_event
from ..supervisor_service import (
    analyze_difficulty,
    analyze_duration,
    analyze_performance_trend,
    recommend_action,
    SupervisorObservation,
    SupervisorAction,
    supervisor_registry,
)

logger = logging.getLogger(__name__)


def supervisor_node(state: InterviewState) -> Dict[str, Any]:
    """LangGraph node: Monitor interview and recommend/execute control actions.

    This node is the successor to advisor_monitor_node. It expands monitoring
    to include duration, difficulty, and performance trends, and supports
    three control modes (monitor, suggest, auto).

    Returns state updates to be merged into the LangGraph state.
    """
    output: Dict[str, Any] = {}
    session_id = state.get("supervisor_session_id", "unknown")

    # ── Guard: Skip if supervisor is paused ────────────────────────────────
    if state.get("supervisor_paused", False):
        return {"supervisor_observations": [{
            "type": "supervisor_paused",
            "message": "Supervisor paused — skipping analysis",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }]}

    # ── 1. Duration Analysis ───────────────────────────────────────────────
    session_start = state.get("session_start_epoch", time.time())
    question_start = state.get("question_start_epoch")
    per_q_times = state.get("per_question_times", [])
    question_idx = state.get("current_question_index", 0)

    # Record this question's duration if we just finished one
    if question_start is not None and per_q_times:
        now = time.time()
        elapsed = now - question_start
        per_q_times = list(per_q_times) + [elapsed]
        output["per_question_times"] = per_q_times
        output["question_start_epoch"] = now  # reset for next question

    duration_analysis = analyze_duration(
        question_index=question_idx,
        session_start_epoch=session_start,
        question_start_epoch=question_start,
        per_question_times=per_q_times,
        max_questions=state.get("max_questions", 15),
    )

    # Record duration observations
    observations: list = []
    for alert in duration_analysis.time_alerts:
        severity = "warning" if alert == "question_taking_too_long" else "info"
        observations.append({
            "type": "duration_observation",
            "subtype": alert,
            "severity": severity,
            "message": {
                "question_taking_too_long": f"Current question taking >5 min ({duration_analysis.current_question_duration:.0f}s)",
                "running_overtime": f"Total interview time >45 min ({duration_analysis.total_elapsed_seconds/60:.0f} min)",
                "too_slow_pace": f"Average response time {duration_analysis.avg_time_per_question:.0f}s — slow pace",
                "too_fast_pace": f"Average response time {duration_analysis.avg_time_per_question:.0f}s — very fast",
            }.get(alert, alert),
            "details": duration_analysis.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # Log duration observations to registry
    for obs_data in observations:
        supervisor_registry.record_observation(
            session_id,
            SupervisorObservation(
                observation_type=obs_data["type"],
                severity=obs_data["severity"],
                message=obs_data["message"],
                details=obs_data.get("details"),
            )
        )

    # ── 2. Difficulty Analysis ─────────────────────────────────────────────
    score_history = state.get("score_history", [])
    latest_score = state.get("latest_score", 0.0)

    # Update score history
    if latest_score > 0:
        score_history = list(score_history) + [latest_score]
        output["score_history"] = score_history

    current_diff = state.get("difficulty", "medium")
    diff_history = state.get("difficulty_history", [])

    diff_analysis = analyze_difficulty(
        current_difficulty=current_diff,
        score_history=score_history,
        current_score=latest_score,
        difficulty_history=diff_history,
    )

    if diff_analysis.recommended_difficulty != current_diff:
        observations.append({
            "type": "difficulty_observation",
            "subtype": "difficulty_adjustment_recommended",
            "severity": "info",
            "message": f"Difficulty adjustment recommended: {current_diff} → {diff_analysis.recommended_difficulty}",
            "details": diff_analysis.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    if diff_analysis.is_stuck_on_easy or diff_analysis.is_stuck_on_hard:
        observations.append({
            "type": "difficulty_observation",
            "subtype": "stuck_on_difficulty" if diff_analysis.is_stuck_on_hard else "under_challenged",
            "severity": "warning",
            "message": f"Candidate stuck on '{current_diff}' difficulty — adjusting to '{diff_analysis.recommended_difficulty}'",
            "details": diff_analysis.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ── 3. Performance Trend Analysis ──────────────────────────────────────
    perf_trend = analyze_performance_trend(
        score_history=score_history,
        low_quality_count=state.get("low_quality_count", 0),
        high_quality_count=state.get("high_quality_count", 0),
    )

    if perf_trend.trend == "declining" and perf_trend.volatility > 2.0:
        observations.append({
            "type": "performance_observation",
            "subtype": "declining_performance",
            "severity": "warning",
            "message": f"Performance declining (trend: {perf_trend.trend}, volatility: {perf_trend.volatility:.1f})",
            "details": perf_trend.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    if perf_trend.fatigue_detected:
        observations.append({
            "type": "fatigue_observation",
            "subtype": "fatigue_detected",
            "severity": "warning",
            "message": "Candidate fatigue signals detected — consider wrapping up",
            "details": perf_trend.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ── 4. Recommend Action ────────────────────────────────────────────────
    control_mode = state.get("supervisor_mode", "suggest")
    avg_score = state.get("avg_score", 0.0)
    skill_coverage = state.get("skill_coverage_percentage", 0.0)

    action = recommend_action(
        difficulty_analysis=diff_analysis,
        duration_analysis=duration_analysis,
        performance_trend=perf_trend,
        question_index=question_idx,
        avg_score=avg_score,
        skill_coverage=skill_coverage,
        control_mode=control_mode,
    )

    last_action_dict: Optional[Dict] = None

    if action is not None:
        action_dict = action.model_dump()

        # Execute action based on control mode
        if control_mode == "auto" and action.action_type != "no_action":
            # In "auto" mode, execute the action immediately
            output["supervisor_override"] = {
                "action": action.action_type,
                "confidence": action.confidence,
                "reason": action.reason,
                "payload": action.payload,
                "executed_at": datetime.now(timezone.utc).isoformat(),
                "auto_executed": True,
            }

            # Apply action payloads
            if action.action_type == "adjust_difficulty" and action.payload:
                new_diff = action.payload.get("new_difficulty", current_diff)
                if new_diff != current_diff:
                    output["difficulty"] = new_diff
                    diff_history = list(diff_history) + [new_diff]
                    output["difficulty_history"] = diff_history

            if action.action_type == "suggest_close":
                # In auto mode, we can mark suggest_close — the client decides
                # We still set ready_to_close flag like the advisor
                if not state.get("advisor_action_taken", False):
                    output["advisor_ready_to_close"] = True
                    output["advisor_confidence"] = action.confidence
                    output["advisor_reason"] = action.reason
                    output["advisor_reason_category"] = action.payload.get("reason_category", "supervisor_recommendation") if action.payload else "supervisor_recommendation"

            supervisor_registry.execute_action(session_id, action)

        elif control_mode == "suggest" and action.action_type != "no_action":
            # In "suggest" mode, set advisor-like flags for the UI to show
            if action.action_type == "suggest_close":
                if not state.get("advisor_action_taken", False):
                    output["advisor_ready_to_close"] = True
                    output["advisor_confidence"] = action.confidence
                    output["advisor_reason"] = action.reason
                    output["advisor_reason_category"] = action.payload.get("reason_category", "supervisor_recommendation") if action.payload else "supervisor_recommendation"

            supervisor_registry.execute_action(session_id, action)

        last_action_dict = action_dict
        supervisor_registry.record_observation(
            session_id,
            SupervisorObservation(
                observation_type="control_action",
                severity="info",
                message=f"Action recommended: {action.action_type} ({action.reason})",
                details=action.model_dump(),
            )
        )

        observations.append({
            "type": "supervisor_action",
            "subtype": action.action_type,
            "severity": "info",
            "message": f"[mode:{control_mode}] {action.action_type}: {action.reason}",
            "details": action.model_dump(),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

    # ── 5. Build summary for state ─────────────────────────────────────────
    observation_summary = {
        "difficulty": diff_analysis.model_dump(),
        "duration": duration_analysis.model_dump(),
        "performance": perf_trend.model_dump(),
        "action": last_action_dict,
        "control_mode": control_mode,
    }

    output["supervisor_observations"] = observations
    output["supervisor_last_action"] = last_action_dict
    output["coordination_trace"] = [
        coordination_event(
            agent="supervisor",
            event="analysis_completed",
            state=state,
            details={"action": last_action_dict, "control_mode": control_mode, "observation_count": len(observations)},
        )
    ]

    # Add the summary as the latest observation for WebSocket forwarding
    output["_supervisor_summary"] = observation_summary

    logger.debug(
        f"Supervisor [{session_id[:8]}]: q={question_idx}, "
        f"diff={current_diff}→{diff_analysis.recommended_difficulty}, "
        f"trend={perf_trend.trend}, "
        f"action={action.action_type if action else 'none'}"
    )

    return output


# ── Legacy Adapter ────────────────────────────────────────────────────────────

def advisor_monitor_node_legacy(state: InterviewState) -> Dict[str, Any]:
    """Legacy wrapper that delegates to supervisor_node.

    Maintains the original advisor_monitor_node interface contract
    for backward compatibility during migration.
    """
    result = supervisor_node(state)

    # Extract advisor-compatible fields for clients expecting the old format
    advisor_output: Dict[str, Any] = {}

    if result.get("supervisor_last_action"):
        action = result["supervisor_last_action"]
        if action.get("action_type") == "suggest_close":
            advisor_output["advisor_ready_to_close"] = True
            advisor_output["advisor_confidence"] = action.get("confidence")
            advisor_output["advisor_reason"] = action.get("reason")
            advisor_output["advisor_reason_category"] = action.get("payload", {}).get("reason_category")
            advisor_output["advisor_notified"] = True

    # Pass through supervisor data
    advisor_output["supervisor_observations"] = result.get("supervisor_observations", [])
    advisor_output["supervisor_last_action"] = result.get("supervisor_last_action")
    advisor_output["_supervisor_summary"] = result.get("_supervisor_summary")

    # Pass through any auto-executed overrides
    if "supervisor_override" in result:
        advisor_output["supervisor_override"] = result["supervisor_override"]
    if "difficulty" in result:
        advisor_output["difficulty"] = result["difficulty"]
    if "difficulty_history" in result:
        advisor_output["difficulty_history"] = result["difficulty_history"]
    if "score_history" in result:
        advisor_output["score_history"] = result["score_history"]
    if "per_question_times" in result:
        advisor_output["per_question_times"] = result["per_question_times"]
    if "question_start_epoch" in result:
        advisor_output["question_start_epoch"] = result["question_start_epoch"]

    return advisor_output
