from langgraph.graph import StateGraph, END
import logging
from contextlib import AsyncExitStack
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from .state import InterviewState
from .nodes import (
    generate_question_node,
    evaluate_answer_node,
    evaluate_code_node,
    update_memory_node,
    empathy_analyzer_node,
    skeptic_evaluation_node,
    pragmatist_evaluation_node,
    bias_auditor_node,
    consensus_synthesizer_node,
    code_copilot_node,
    debate_router_node,
)
from .supervisor_node import supervisor_node  # Phase 1B: AI Supervisor (replaces advisor_monitor)
from .planner_node import planner_node
from .sentiment_node import sentiment_node
from .qa_node import qa_agent_node
from .react_nodes import (
    react_interviewer_node,
    react_evaluator_node,
    react_supervisor_node,
)
from .nooa_nodes import nooa_interviewer_node, nooa_evaluator_node
from app.core.config import settings
import os

logger = logging.getLogger(__name__)

# Feature flag: when VEDRIX_REACT_GRAPH=1 (default), the graph uses the ReAct
# wrappers (which themselves fall back to the deterministic nodes on failure).
# Set to "0" to force the original nodes.
_USE_REACT_GRAPH = os.environ.get("VEDRIX_REACT_GRAPH", "1").lower() not in (
    "0", "false", "no", "off"
)
_USE_NOOA_GRAPH = os.environ.get(
    "VEDRIX_NOOA_GRAPH", "1" if settings.NOOA_ENABLED else "0"
).lower() not in ("0", "false", "no", "off", "")

# Node references the graph will actually use. NOOA is the opt-in migration
# path; the supervisor remains on the existing ReAct/deterministic contract.
_question_node = (
    nooa_interviewer_node if _USE_NOOA_GRAPH
    else react_interviewer_node if _USE_REACT_GRAPH
    else generate_question_node
)
_evaluator_node = (
    nooa_evaluator_node if _USE_NOOA_GRAPH
    else react_evaluator_node if _USE_REACT_GRAPH
    else evaluate_answer_node
)
_supervisor_node = react_supervisor_node if _USE_REACT_GRAPH else supervisor_node


def should_continue(state: InterviewState):
    if state.get('interview_complete', False):
        return END
    return "continue"


def route_after_input(state: InterviewState):
    if state.get("copilot_request_pending"):
        return "code_copilot"
    return "debate"


def route_after_qa(state: InterviewState):
    """Route after QA agent evaluation.
    
    - If approved: proceed to sentiment analysis
    - If regenerate: loop back to generate_question (up to 3 times)
    - If regeneration count exceeded (escalated): proceed to sentiment
    """
    if state.get("approved", False):
        return "sentiment"
    if state.get("regenerate", False):
        return "generate_question"
    # Default: proceed to sentiment (safety fallback)
    return "sentiment"


def create_interview_graph(checkpointer=None):
    workflow = StateGraph(InterviewState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("generate_question", _question_node)
    workflow.add_node("qa_agent", qa_agent_node)
    workflow.add_node("sentiment", sentiment_node)
    workflow.add_node("empathy_analyzer", empathy_analyzer_node)
    workflow.add_node("code_copilot", code_copilot_node)
    workflow.add_node("debate_router", debate_router_node)
    workflow.add_node("skeptic_evaluation", skeptic_evaluation_node)
    workflow.add_node("pragmatist_evaluation", pragmatist_evaluation_node)
    workflow.add_node("bias_auditor", bias_auditor_node)
    workflow.add_node("consensus_synthesizer", consensus_synthesizer_node)
    workflow.add_node("update_memory", update_memory_node)
    workflow.add_node("supervisor", _supervisor_node)  # Phase 1B: AI Supervisor (ReAct-wrapped by default)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "generate_question")
    
    # From generate_question, proceed to QA agent for bias/relevance check
    workflow.add_edge("generate_question", "qa_agent")
    
    # QA agent routes: approved → sentiment, regenerate → generate_question
    workflow.add_conditional_edges(
        "qa_agent",
        route_after_qa,
        {
            "sentiment": "sentiment",
            "generate_question": "generate_question",
        }
    )
    
    # Sentiment node proceeds to empathy_analyzer
    workflow.add_edge("sentiment", "empathy_analyzer")
    
    # After empathy analyzer, either trigger co-pilot or run evaluation debate
    workflow.add_conditional_edges(
        "empathy_analyzer",
        route_after_input,
        {
            "code_copilot": "code_copilot",
            "debate": "debate_router"
        }
    )
    
    # Loop co-pilot back to sentiment so it halts again awaiting candidate action
    workflow.add_edge("code_copilot", "sentiment")
    
    # debate_router splits to parallel debate nodes
    workflow.add_edge("debate_router", "skeptic_evaluation")
    workflow.add_edge("debate_router", "pragmatist_evaluation")
    workflow.add_edge("debate_router", "bias_auditor")
    
    # Parallel debate nodes join at the synthesizer
    workflow.add_edge("skeptic_evaluation", "consensus_synthesizer")
    workflow.add_edge("pragmatist_evaluation", "consensus_synthesizer")
    workflow.add_edge("bias_auditor", "consensus_synthesizer")
    
    # Synthesizer updates memory and triggers supervisor
    workflow.add_edge("consensus_synthesizer", "update_memory")
    workflow.add_edge("update_memory", "supervisor")  # Supervisor runs after memory
 
    workflow.add_conditional_edges(
        "supervisor",
        should_continue,
        {"continue": "generate_question", END: END}
    )
 
    memory = checkpointer or MemorySaver()
    return workflow.compile(
        checkpointer=memory,
        interrupt_before=["sentiment"]
    )


_checkpointer_stack: AsyncExitStack | None = None
interview_graph = create_interview_graph()


def _checkpoint_dsn() -> str:
    """Convert SQLAlchemy asyncpg URL to a psycopg-compatible checkpoint DSN."""
    raw = settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)
    parts = urlsplit(raw)
    query = dict(parse_qsl(parts.query))
    if settings.DB_SSL_MODE and settings.DB_SSL_MODE != "disable":
        query["sslmode"] = settings.DB_SSL_MODE
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


async def initialize_interview_graph() -> None:
    """Swap the import-time graph for a PostgreSQL-backed graph at startup."""
    global _checkpointer_stack, interview_graph
    if _checkpointer_stack is not None:
        return
    if not settings.LANGGRAPH_CHECKPOINT_ENABLED:
        logger.warning("LangGraph PostgreSQL checkpointing is disabled; using MemorySaver")
        return

    stack = AsyncExitStack()
    await stack.__aenter__()
    try:
        checkpointer = await stack.enter_async_context(
            AsyncPostgresSaver.from_conn_string(_checkpoint_dsn())
        )
        await checkpointer.setup()
        interview_graph = create_interview_graph(checkpointer=checkpointer)
        _checkpointer_stack = stack
        logger.info("LangGraph AsyncPostgresSaver initialized")
    except Exception:
        await stack.aclose()
        logger.exception("Failed to initialize LangGraph PostgreSQL checkpointer")
        raise


async def close_interview_graph() -> None:
    """Close the PostgreSQL checkpointer during application shutdown."""
    global _checkpointer_stack, interview_graph
    if _checkpointer_stack is not None:
        await _checkpointer_stack.aclose()
        _checkpointer_stack = None
    interview_graph = create_interview_graph()
