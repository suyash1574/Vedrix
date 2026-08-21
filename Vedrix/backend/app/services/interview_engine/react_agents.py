"""
ReAct-based agent implementations for the Vedrix interview engine.

These wrap the ReAct framework (react.py) around the existing LLM-backed
interview logic. Each agent:
  1. Reasons about the next step in plain text.
  2. Optionally calls a tool (skill lookup, RAG, memory, bias check, alert).
  3. Reads the tool's observation and decides whether to act again or
     emit a Final Answer.
  4. Records every step to the observability service as a TraceEntry.

Public agents
-------------
- ReActInterviewerAgent  : generates the next interview question
- ReActEvaluatorAgent    : scores the candidate's last answer
- ReActSupervisorAgent   : monitors duration/difficulty/performance trends
- ReActResearchAgent     : orchestrates candidate enrichment
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from app.services.interview_engine.react import (
    BUILTIN_TOOLS,
    ReActAgent,
    ReActStep,
    ReActTrace,
    Tool,
    ToolParameter,
    ToolRegistry,
    _safe_parse_json,
    parse_react_output,
)
from app.services.interview_engine.state import InterviewState
from app.services.interview_engine.coordination import coordination_event, supervisor_action_update
from app.services.observability_service import trace_agent_action

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# TraceEntry recorder
# ─────────────────────────────────────────────────────────────────────────────

async def _persist_step_to_trace_entry(
    agent_name: str,
    action_type: str,
    step: ReActStep,
    session_id: Optional[int] = None,
) -> None:
    """
    Persist a single ReAct step to the TraceEntry table.

    This mirrors how the rest of the interview engine records its actions
    for observability.
    """
    try:
        from app.db.session import async_session
        from app.services.observability_service import ObservabilityService
        from app.models.trace_entry import TraceEntryCreate

        async with async_session() as db:
            obs = ObservabilityService(db)
            input_summary = ""
            if step.action_name:
                input_summary = f"{step.action_name}({json.dumps(step.action_input or {}, ensure_ascii=False)[:200]})"
            elif step.thought:
                input_summary = f"Thought: {step.thought[:200]}"
            elif step.final_answer is not None:
                input_summary = "Final Answer emitted"

            output_summary = ""
            if step.observation is not None:
                output_summary = str(step.observation)[:200]
            elif step.final_answer is not None:
                output_summary = str(step.final_answer)[:200]
            if step.observation_error:
                output_summary = (output_summary + " | ERROR: " + step.observation_error)[:300]

            await obs.record(TraceEntryCreate(
                agent_name=agent_name,
                action_type=action_type,
                session_id=session_id,
                input_summary=input_summary,
                reasoning_summary=(step.thought or "")[:500],
                output_summary=output_summary,
                confidence_score=1.0 if step.action_type.value == "finish" else 0.0,
                duration_ms=step.duration_ms,
            ))
    except Exception as e:
        logger.warning("Failed to persist ReAct step for %s: %s", agent_name, e)


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Interviewer — generates the next interview question
# ─────────────────────────────────────────────────────────────────────────────

INTERVIEWER_QUESTION_SCHEMA_PROMPT = """\
When you emit your Final Answer, output ONLY a JSON object with these exact fields:
{{
  "id": <integer>,
  "question": "<the question text — natural and conversational>",
  "category": "<technical|behavioral|resume-based|situational>",
  "difficulty": "<easy|medium|hard>",
  "time_limit": <seconds>,
  "skill_tested": "<primary skill>",
  "follow_up_topic": "<a related topic for a follow-up question, or null>"
}}
Do not include any other keys, no markdown, no commentary. Pure JSON only.
"""


class ReActInterviewerAgent:
    """
    ReAct-driven interviewer that picks a skill, queries the candidate's
    history, optionally pulls RAG context, and then generates the next
    question via a single LLM call wrapped as a tool.
    """

    name = "react_interviewer"

    def __init__(self, llm, registry: Optional[ToolRegistry] = None) -> None:
        self.llm = llm
        self.registry = registry or BUILTIN_TOOLS

        # Add the local "synthesize_question" tool that uses the same LLM
        # the agent is built on. The tool's callable re-invokes the LLM to
        # produce a single JSON question, which the agent returns as its
        # Final Answer.
        if "synthesize_question" not in self.registry.list_names():
            self.registry.register(Tool(
                name="synthesize_question",
                description="Generate the final interview question JSON. Call this exactly once, "
                            "with the chosen skill, difficulty, and a short hint, before emitting "
                            "your Final Answer.",
                parameters=[
                    ToolParameter(name="skill", type="string", description="Skill to test"),
                    ToolParameter(name="difficulty", type="string", description="easy|medium|hard"),
                    ToolParameter(name="hint", type="string", description="Brief hint about what the question should probe"),
                ],
                callable=self._synthesize_question,
            ))

        self.agent = ReActAgent(
            name=self.name,
            llm=llm,
            registry=self.registry,
            max_steps=5,
            system_prompt=(
                "You are the Vedrix Senior Interviewer. You conduct natural, "
                "conversational, evidence-based interviews. You sound like a "
                "thoughtful senior engineer having a real conversation.\n\n"
                + INTERVIEWER_QUESTION_SCHEMA_PROMPT
            ),
            trace_recorder=self._record_step,
        )

    async def _synthesize_question(self, skill: str, difficulty: str, hint: str) -> Dict[str, Any]:
        """Internal tool: produce a single question JSON from the LLM."""
        from app.services.interview_engine.providers import get_fast_llm
        from langchain_core.output_parsers import JsonOutputParser
        from app.services.interview_engine.nodes import QuestionSchema

        llm = self.llm or get_fast_llm()
        parser = JsonOutputParser(pydantic_object=QuestionSchema)

        prompt = (
            f"Generate ONE interview question for skill '{skill}' at '{difficulty}' difficulty.\n"
            f"Hint/context: {hint or 'general competency probe'}\n"
            f"Sound like a real human interviewer — not robotic.\n"
            f"{parser.get_format_instructions()}"
        )
        response = await llm.ainvoke([
            SystemMessage(content="You are a senior, conversational technical interviewer."),
            HumanMessage(content=prompt),
        ])
        content = response.content if isinstance(response.content, str) else str(response.content)
        # strip markdown fences
        content = content.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            content = "\n".join(lines).strip()
        try:
            return parser.parse(content)
        except Exception as e:
            logger.warning("synthesize_question parse failed: %s — returning minimal fallback", e)
            return {
                "id": 1,
                "question": f"Tell me about your experience with {skill}.",
                "category": "technical",
                "difficulty": difficulty,
                "time_limit": 120,
                "skill_tested": skill,
                "follow_up_topic": None,
            }

    async def _record_step(self, step: ReActStep) -> None:
        await _persist_step_to_trace_entry(
            self.name,
            f"react_{step.action_type.value}",
            step,
        )

    async def run(
        self,
        state: InterviewState,
        pending_skills: List[str],
        difficulty: str,
        question_index: int,
    ) -> Dict[str, Any]:
        """
        Run the ReAct interviewer to produce the next question.

        Returns a dict that can be merged into InterviewState, primarily:
          {"next_question": <dict>, "messages": [<assistant msg>], ...}
        """
        candidate_name = state.get("candidate_first_name") or "the candidate"
        task = (
            f"Generate question #{question_index + 1} for candidate {candidate_name}, "
            f"job role '{state.get('job_role', 'engineer')}'.\n"
            f"Pending skills to cover: {', '.join(pending_skills) or 'general competency'}.\n"
            f"Difficulty target: {difficulty}.\n"
            f"Use the tools as needed to ground your question in the candidate's real history."
        )

        trace = await self.agent.run(task=task)

        final = trace.final_answer
        if not isinstance(final, dict):
            # try to coerce
            if isinstance(final, str):
                final = _safe_parse_json(final) or {"question": final}
            else:
                final = {"question": "Tell me a bit about your background."}

        # ensure required keys
        for key in ("id", "question", "category", "difficulty", "time_limit", "skill_tested", "follow_up_topic"):
            if key not in final:
                final[key] = None
        if final.get("id") is None:
            final["id"] = question_index + 1
        if final.get("difficulty") not in ("easy", "medium", "hard"):
            final["difficulty"] = difficulty
        if final.get("time_limit") is None:
            final["time_limit"] = 120

        return {
            "next_question": final,
            "messages": [{"role": "assistant", "content": final["question"]}],
        }


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Evaluator — scores the candidate's last answer
# ─────────────────────────────────────────────────────────────────────────────

EVALUATOR_SCHEMA_PROMPT = """\
When you emit your Final Answer, output ONLY a JSON object with these exact fields:
{{
  "score": <0.0..10.0>,
  "metrics": {{"accuracy": <0..10>, "clarity": <0..10>, "depth": <0..10>, "communication": <0..10>}},
  "feedback": "<one short paragraph>",
  "topic": "<skill or topic>",
  "skill_category": "<technical|soft_skill|behavioral>",
  "should_deep_dive": <true|false>,
  "is_coding_challenge": <true|false>,
  "needs_easier": <true|false>,
  "low_effort": <true|false>,
  "skill_identified": "<specific skill>"
}}
Pure JSON, no markdown.
"""


class ReActEvaluatorAgent:
    """ReAct-driven answer evaluator."""

    name = "react_evaluator"

    def __init__(self, llm, registry: Optional[ToolRegistry] = None) -> None:
        self.llm = llm
        self.registry = registry or BUILTIN_TOOLS

        if "score_answer" not in self.registry.list_names():
            self.registry.register(Tool(
                name="score_answer",
                description="Call this once with the question text, the candidate's answer text, "
                            "and the skill being tested. It returns a structured evaluation JSON. "
                            "Use the returned scores as your Final Answer.",
                parameters=[
                    ToolParameter(name="question", type="string", description="The interview question text"),
                    ToolParameter(name="answer", type="string", description="The candidate's answer text"),
                    ToolParameter(name="skill", type="string", description="The skill being tested"),
                ],
                callable=self._score_answer,
            ))

        self.agent = ReActAgent(
            name=self.name,
            llm=llm,
            registry=self.registry,
            max_steps=4,
            system_prompt=(
                "You are the Vedrix Senior Hiring Manager. You evaluate candidate answers "
                "objectively using the available tools. Bias mitigation is critical — "
                "score on demonstrated skills, never on accent, style, or background.\n\n"
                + EVALUATOR_SCHEMA_PROMPT
            ),
            trace_recorder=self._record_step,
        )

    async def _score_answer(self, question: str, answer: str, skill: str) -> Dict[str, Any]:
        from langchain_core.output_parsers import JsonOutputParser
        from app.services.interview_engine.nodes import EvaluationSchema
        parser = JsonOutputParser(pydantic_object=EvaluationSchema)
        prompt = (
            f"Evaluate this answer.\n\nQUESTION ({skill}): {question}\n\n"
            f"ANSWER: {answer}\n\n{parser.get_format_instructions()}"
        )
        try:
            response = await self.llm.ainvoke([
                SystemMessage(content="You are an unbiased senior hiring manager. "
                                     "Score 0-10 based on substance. "
                                     "Do not penalize for accent, grammar, or non-native English."),
                HumanMessage(content=prompt),
            ])
            content = response.content if isinstance(response.content, str) else str(response.content)
            content = content.strip()
            if content.startswith("```"):
                lines = content.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                content = "\n".join(lines).strip()
            return parser.parse(content)
        except Exception as e:
            logger.warning("score_answer failed: %s", e)
            return {
                "score": 5.0,
                "metrics": {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5},
                "feedback": "Could not evaluate automatically.",
                "topic": skill,
                "skill_category": "technical",
                "should_deep_dive": False,
                "is_coding_challenge": False,
                "needs_easier": False,
                "low_effort": False,
                "skill_identified": skill,
            }

    async def _record_step(self, step: ReActStep) -> None:
        await _persist_step_to_trace_entry(self.name, f"react_{step.action_type.value}", step)

    async def run(self, question: str, answer: str, skill: str) -> Dict[str, Any]:
        task = (
            f"Evaluate this answer for skill '{skill}'.\n\n"
            f"QUESTION: {question}\n\n"
            f"ANSWER: {answer}\n"
            "Use the score_answer tool, then return its output as your Final Answer."
        )
        trace = await self.agent.run(task=task)
        final = trace.final_answer
        # Coerce to a dict — handle string, dict, or unexpected types
        if isinstance(final, str):
            parsed = _safe_parse_json(final)
            final = parsed if isinstance(parsed, dict) else {}
        if not isinstance(final, dict):
            final = {}
        # ensure required keys
        final.setdefault("score", 5.0)
        final.setdefault("metrics", {"accuracy": 5, "clarity": 5, "depth": 5, "communication": 5})
        final.setdefault("feedback", "")
        final.setdefault("topic", skill)
        final.setdefault("skill_category", "technical")
        final.setdefault("should_deep_dive", False)
        final.setdefault("is_coding_challenge", False)
        final.setdefault("needs_easier", False)
        final.setdefault("low_effort", False)
        final.setdefault("skill_identified", skill)
        return final


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Supervisor — monitors and recommends actions
# ─────────────────────────────────────────────────────────────────────────────

class ReActSupervisorAgent:
    """ReAct-driven supervisor that monitors interview health and recommends actions."""

    name = "react_supervisor"

    # Available control actions
    ACTIONS = ("no_action", "adjust_difficulty", "suggest_close", "force_pause")

    def __init__(self, llm, registry: Optional[ToolRegistry] = None) -> None:
        self.llm = llm
        if registry is None:
            self.registry = BUILTIN_TOOLS
        else:
            # If a custom registry was passed, augment it with the built-in tools
            # so the supervisor always has access to emit_alert / check_bias / etc.
            self.registry = registry
            for name in BUILTIN_TOOLS.list_names():
                if name not in self.registry.list_names():
                    self.registry.register(BUILTIN_TOOLS.get(name))
        self.agent = ReActAgent(
            name=self.name,
            llm=llm,
            registry=self.registry,
            max_steps=4,
            system_prompt=(
                "You are the Vedrix AI Supervisor. You monitor the live interview for "
                "duration overruns, difficulty issues, performance trends, and stress alerts. "
                "When something needs HR attention, you can call `emit_alert`. When you have "
                "finished your analysis, emit a Final Answer JSON describing the recommended "
                "action.\n\n"
                "Final Answer JSON shape:\n"
                "{\n"
                '  "action_type": "no_action" | "adjust_difficulty" | "suggest_close" | "force_pause",\n'
                '  "confidence": <0.0..1.0>,\n'
                '  "reason": "<short human-readable reason>",\n'
                '  "reason_category": "<time_overrun|performance_declining|skill_coverage_complete|fatigue|stuck|no_action>",\n'
                '  "new_difficulty": "easy" | "medium" | "hard"  (only when action_type=adjust_difficulty)\n'
                "}"
            ),
            trace_recorder=self._record_step,
        )

    async def _record_step(self, step: ReActStep) -> None:
        await _persist_step_to_trace_entry(self.name, f"react_{step.action_type.value}", step)

    async def run(self, state: InterviewState) -> Dict[str, Any]:
        from app.services.supervisor_service import (
            analyze_difficulty,
            analyze_duration,
            analyze_performance_trend,
        )

        # Pre-compute the analyses so the agent has structured input
        score_history = list(state.get("score_history") or [])
        # include latest score if not yet in history
        if state.get("latest_score", 0) and (not score_history or score_history[-1] != state.get("latest_score")):
            score_history = score_history + [state["latest_score"]]

        diff_analysis = analyze_difficulty(
            current_difficulty=state.get("difficulty", "medium"),
            score_history=score_history,
            current_score=state.get("latest_score", 0.0),
            difficulty_history=list(state.get("difficulty_history") or []),
        )
        duration_analysis = analyze_duration(
            question_index=state.get("current_question_index", 0),
            session_start_epoch=state.get("session_start_epoch", time.time()),
            question_start_epoch=state.get("question_start_epoch"),
            per_question_times=list(state.get("per_question_times") or []),
            max_questions=state.get("max_questions", 15),
        )
        perf_trend = analyze_performance_trend(
            score_history=score_history,
            low_quality_count=state.get("low_quality_count", 0),
            high_quality_count=state.get("high_quality_count", 0),
        )

        analysis_payload = {
            "difficulty": diff_analysis.model_dump() if hasattr(diff_analysis, "model_dump") else dict(diff_analysis),
            "duration": duration_analysis.model_dump() if hasattr(duration_analysis, "model_dump") else dict(duration_analysis),
            "performance": perf_trend.model_dump() if hasattr(perf_trend, "model_dump") else dict(perf_trend),
        }

        task = (
            "Analyze the following interview signals and decide whether to take any action. "
            "Use the available tools to look up skill definitions, query RAG, or emit HR alerts as needed. "
            "Then emit a Final Answer JSON describing the action to take.\n\n"
            f"SIGNALS: {json.dumps(analysis_payload, default=str)}\n"
            f"Question index: {state.get('current_question_index', 0)}\n"
            f"Avg score: {state.get('avg_score', 0.0):.2f}\n"
            f"Skill coverage: {state.get('skill_coverage_percentage', 0.0):.0f}%"
        )

        trace = await self.agent.run(task=task)
        final = trace.final_answer
        if not isinstance(final, dict):
            if isinstance(final, str):
                final = _safe_parse_json(final) or {}
            else:
                final = {}

        action = final.get("action_type") or "no_action"
        if action not in self.ACTIONS:
            action = "no_action"

        action_payload = {"new_difficulty": final.get("new_difficulty")} if final.get("new_difficulty") else {}
        action_dict = {
            "action_type": action,
            "confidence": float(final.get("confidence", 0.0) or 0.0),
            "reason": final.get("reason", ""),
            "reason_category": final.get("reason_category", "no_action"),
            "payload": action_payload,
        }
        update = supervisor_action_update(
            state=state,
            action=action_dict,
            control_mode=state.get("supervisor_mode", "suggest"),
        )
        update["supervisor_observations"] = [
            {
                "type": "react_supervisor_action",
                "subtype": action,
                "severity": "warning" if action != "no_action" else "info",
                "message": final.get("reason", ""),
                "details": analysis_payload,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ]
        update["coordination_trace"].append(
            coordination_event(
                agent="react_supervisor",
                event="analysis_completed",
                state=state,
                details={"action": action, "control_mode": state.get("supervisor_mode", "suggest")},
            )
        )
        update["_supervisor_summary"] = {
            "difficulty": analysis_payload["difficulty"],
            "duration": analysis_payload["duration"],
            "performance": analysis_payload["performance"],
            "action": update.get("supervisor_last_action"),
        }
        return update


# ─────────────────────────────────────────────────────────────────────────────
# ReAct Research — orchestrates candidate enrichment
# ─────────────────────────────────────────────────────────────────────────────

async def _tool_fetch_github(username: str) -> Dict[str, Any]:
    try:
        from app.services.research_service import research_service
        if not username:
            return {"error": "no username"}
        return await research_service.index_github(
            session_id="ad-hoc", github_username=username
        )
    except Exception as e:
        return {"error": f"github fetch failed: {e}"}


async def _tool_fetch_linkedin(url: str) -> Dict[str, Any]:
    try:
        from app.services.research_service import research_service
        if not url:
            return {"error": "no url"}
        return await research_service.extract_linkedin(
            session_id="ad-hoc", linkedin_url=url
        )
    except Exception as e:
        return {"error": f"linkedin fetch failed: {e}"}


class ReActResearchAgent:
    """ReAct-driven candidate enrichment agent."""

    name = "react_research"

    def __init__(self, llm, registry: Optional[ToolRegistry] = None) -> None:
        self.llm = llm
        self.registry = registry or BUILTIN_TOOLS

        if "fetch_github" not in self.registry.list_names():
            self.registry.register(Tool(
                name="fetch_github",
                description="Fetch public GitHub repositories and READMEs for a given username.",
                parameters=[ToolParameter(name="username", type="string", description="GitHub username")],
                callable=_tool_fetch_github,
            ))
        if "fetch_linkedin" not in self.registry.list_names():
            self.registry.register(Tool(
                name="fetch_linkedin",
                description="Extract structured profile data from a public LinkedIn URL.",
                parameters=[ToolParameter(name="url", type="string", description="Public LinkedIn URL")],
                callable=_tool_fetch_linkedin,
            ))

        self.agent = ReActAgent(
            name=self.name,
            llm=llm,
            registry=self.registry,
            max_steps=6,
            system_prompt=(
                "You are the Vedrix Research Agent. You enrich a candidate's profile by "
                "fetching public data from GitHub and LinkedIn, querying the RAG index, "
                "and consolidating an enrichment summary.\n\n"
                "When done, emit a Final Answer JSON:\n"
                "{\n"
                '  "candidate_id": <number>,\n'
                '  "sources": ["github", "linkedin", "rag"],\n'
                '  "skills": ["..."],\n'
                '  "summary": "<one paragraph>",\n'
                '  "errors": []\n'
                "}"
            ),
            trace_recorder=self._record_step,
        )

    async def _record_step(self, step: ReActStep) -> None:
        await _persist_step_to_trace_entry(self.name, f"react_{step.action_type.value}", step)

    async def run(
        self,
        candidate_id: int,
        github_username: Optional[str] = None,
        linkedin_url: Optional[str] = None,
    ) -> Dict[str, Any]:
        task = (
            f"Enrich candidate {candidate_id}.\n"
            f"GitHub username: {github_username or '(not provided)'}\n"
            f"LinkedIn URL: {linkedin_url or '(not provided)'}\n"
            "Fetch each available source, query the RAG index for resume content, "
            "then emit a consolidated enrichment summary as your Final Answer."
        )
        trace = await self.agent.run(task=task, session_id=str(candidate_id))
        final = trace.final_answer
        if not isinstance(final, dict):
            if isinstance(final, str):
                final = _safe_parse_json(final) or {}
            else:
                final = {}
        final.setdefault("candidate_id", candidate_id)
        final.setdefault("sources", [])
        final.setdefault("skills", [])
        final.setdefault("summary", "")
        final.setdefault("errors", [])
        return final
