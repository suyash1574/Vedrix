"""
LangGraph node wrappers that delegate to ReAct agents.

Why this exists
---------------
The Vedrix interview engine is built as a LangGraph state machine. The graph
itself is the canonical, observable source of truth — every state transition
is deterministic, recorded, and replayable.

To gain ReAct's flexibility (dynamic tool use, multi-step reasoning) without
sacrificing the graph's observability, we add *thin wrapper nodes*:

    planner → react_interviewer → qa_agent → sentiment → … → react_supervisor → END

Each wrapper:
  1. Receives the LangGraph `InterviewState`.
  2. Delegates the actual decision to a ReAct agent (react_agents.py).
  3. Merges the agent's output back into the state shape the graph expects.
  4. Falls back to the original deterministic node if ReAct is disabled,
     if the LLM is unavailable, or if the agent exceeds its step budget
     without producing a usable result.

The original deterministic nodes (`generate_question_node`, `evaluate_answer_node`,
`supervisor_node`) are kept intact and reachable via the `VEDRIX_USE_REACT_AGENTS`
feature flag. Default in production: ON. Default in tests: OFF (so existing
test fixtures don't need a live LLM).
"""
from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict

from .state import InterviewState

logger = logging.getLogger(__name__)


# Feature flag — set to "0" / "false" / "no" to fall back to deterministic nodes.
USE_REACT_AGENTS = os.environ.get("VEDRIX_USE_REACT_AGENTS", "1").lower() not in (
    "0", "false", "no", "off", ""
)


def _is_react_enabled() -> bool:
    return USE_REACT_AGENTS


def _is_fast_react_path() -> bool:
    """Use the single structured legacy node when ReAct latency is prioritized."""
    return os.environ.get("VEDRIX_REACT_FAST_PATH", "1").lower() not in ("0", "false", "no", "off", "")


# ─────────────────────────────────────────────────────────────────────────────
# Lazy singletons — ReAct agents are constructed once per process and reused
# across all interview sessions to amortize registry build cost.
# ─────────────────────────────────────────────────────────────────────────────

_singletons: Dict[str, Any] = {}


def _get_interviewer_agent():
    if "interviewer" not in _singletons:
        from .react_agents import ReActInterviewerAgent
        from .providers import get_fast_llm
        from .react import BUILTIN_TOOLS

        _singletons["interviewer"] = ReActInterviewerAgent(
            llm=get_fast_llm(),
            registry=BUILTIN_TOOLS,
        )
    return _singletons["interviewer"]


def _get_evaluator_agent():
    if "evaluator" not in _singletons:
        from .react_agents import ReActEvaluatorAgent
        from .providers import get_strong_llm
        from .react import BUILTIN_TOOLS

        _singletons["evaluator"] = ReActEvaluatorAgent(
            llm=get_strong_llm(),
            registry=BUILTIN_TOOLS,
        )
    return _singletons["evaluator"]


def _get_supervisor_agent():
    if "supervisor" not in _singletons:
        from .react_agents import ReActSupervisorAgent
        from .providers import get_strong_llm
        from .react import BUILTIN_TOOLS

        _singletons["supervisor"] = ReActSupervisorAgent(
            llm=get_strong_llm(),
            registry=BUILTIN_TOOLS,
        )
    return _singletons["supervisor"]


def reset_singletons() -> None:
    """Clear cached ReAct agents. Call between test cases or on LLM rotation."""
    _singletons.clear()


# ─────────────────────────────────────────────────────────────────────────────
# Fallback shims — call the original deterministic LangGraph nodes
# ─────────────────────────────────────────────────────────────────────────────

def _fallback_interviewer(state: InterviewState) -> Dict[str, Any]:
    from .nodes import generate_question_node
    return generate_question_node(state)


def _fallback_evaluator(state: InterviewState) -> Dict[str, Any]:
    from .nodes import evaluate_answer_node
    return evaluate_answer_node(state)


def _fallback_supervisor(state: InterviewState) -> Dict[str, Any]:
    from .supervisor_node import supervisor_node
    return supervisor_node(state)


# ─────────────────────────────────────────────────────────────────────────────
# ReAct wrapper nodes — drop-in replacements for the LangGraph nodes
# ─────────────────────────────────────────────────────────────────────────────

async def react_interviewer_node(state: InterviewState) -> Dict[str, Any]:
    """LangGraph node: generates the next question via the ReAct interviewer.

    Falls back to `generate_question_node` if ReAct is disabled or the agent
    fails to produce a valid question.
    """
    if not _is_react_enabled() or _is_fast_react_path():
        return await _call_fallback(_fallback_interviewer, state)

    # Honor explicit HR takeover / pause states (deterministic guards)
    if state.get("supervisor_mode") == "hr_takeover" or state.get("qa_paused"):
        return await _call_fallback(_fallback_interviewer, state)

    try:
        agent = _get_interviewer_agent()
        result = await agent.run(
            state=state,
            pending_skills=list(state.get("pending_skills") or state.get("skills_to_cover") or []),
            difficulty=state.get("difficulty", "medium"),
            question_index=state.get("current_question_index", 0),
        )
        next_q = result.get("next_question") or {}
        if not next_q.get("question"):
            logger.warning("ReAct interviewer returned empty question — falling back")
            return await _call_fallback(_fallback_interviewer, state)
        return result
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("ReAct interviewer failed: %s — falling back to deterministic node", e)
        return await _call_fallback(_fallback_interviewer, state)


async def react_evaluator_node(state: InterviewState) -> Dict[str, Any]:
    """LangGraph node: scores the last candidate answer via the ReAct evaluator.

    Falls back to `evaluate_answer_node` if ReAct is disabled or the agent
    fails to produce a structured evaluation.
    """
    if not _is_react_enabled() or _is_fast_react_path():
        return await _call_fallback(_fallback_evaluator, state)

    try:
        last_q = state.get("next_question") or {}
        last_a = state.get("last_candidate_answer") or _extract_latest_candidate_message(state)
        if not last_q or not last_a:
            return await _call_fallback(_fallback_evaluator, state)

        skill = last_q.get("skill_tested") or "general"
        question = last_q.get("question") or ""

        agent = _get_evaluator_agent()
        evaluation = await agent.run(question=question, answer=last_a, skill=skill)

        return {"last_evaluation": evaluation}
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("ReAct evaluator failed: %s — falling back to deterministic node", e)
        return await _call_fallback(_fallback_evaluator, state)


async def react_supervisor_node(state: InterviewState) -> Dict[str, Any]:
    """LangGraph node: monitors interview and recommends actions via ReAct supervisor.

    Falls back to `supervisor_node` if ReAct is disabled or the agent fails.
    """
    if not _is_react_enabled():
        return await _call_fallback(_fallback_supervisor, state)

    try:
        agent = _get_supervisor_agent()
        return await agent.run(state)
    except Exception as e:  # pragma: no cover - defensive
        logger.exception("ReAct supervisor failed: %s — falling back to deterministic node", e)
        return await _call_fallback(_fallback_supervisor, state)


async def _call_fallback(fallback, state):
    """Invoke a fallback function, awaiting it if it returns a coroutine.

    Fallback shims may be either sync (returning a dict) or async (returning a
    coroutine), depending on how they were defined. This helper handles both
    uniformly so callers don't have to care.
    """
    out = fallback(state)
    if asyncio.iscoroutine(out):
        out = await out
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _extract_latest_candidate_message(state: InterviewState) -> str:
    """Pull the most recent user-role message out of the state's message list."""
    for msg in reversed(state.get("messages") or []):
        if isinstance(msg, dict) and msg.get("role") == "user":
            return str(msg.get("content") or "")
    return ""
