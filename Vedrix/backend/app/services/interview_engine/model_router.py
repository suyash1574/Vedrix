"""
Task-Aware Model Router for Vedrix AI Interview System.

Routes different interview tasks to optimized models based on:
- Task requirements (speed, reasoning, code understanding, creativity)
- Cost optimization (free tier prioritization)
- Provider fallback chains for reliability

Task-to-Model Mapping:
┌─────────────────────┬───────────────────────────┬────────────────────────────┐
│ Task                │ Primary Model             │ Rationale                  │
├─────────────────────┼───────────────────────────┼────────────────────────────┤
│ Question Generation │ Qwen 2.5 7B (Groq)        │ Fast, creative, good at    │
│                     │                           │ conversational questions   │
├─────────────────────┼───────────────────────────┼────────────────────────────┤
│ Deep Follow-up      │ Llama 3.1 70B (NVIDIA)    │ Strong reasoning for       │
│                     │                           │ adaptive difficulty        │
├─────────────────────┼───────────────────────────┼────────────────────────────┤
│ Answer Evaluation   │ Llama 3.3 70B (Groq)      │ Best free reasoning model  │
│                     │                           │ for scoring & feedback     │
├─────────────────────┼───────────────────────────┼────────────────────────────┤
│ Code Evaluation     │ DeepSeek Coder (OpenRouter│ Code-specialized model for │
│                     │ or Qwen 2.5 Coder)        │ logic & complexity analysis│
├─────────────────────┼───────────────────────────┼────────────────────────────┤
│ Report Generation   │ Llama 3.1 70B (NVIDIA)    │ Analytical, structured     │
│                     │                           │ output for final reports   │
├─────────────────────┼───────────────────────────┼────────────────────────────┤
│ Resume Parsing      │ Qwen 2.5 7B (Groq)        │ Fast extraction, good at   │
│                     │                           │ structured data parsing    │
├─────────────────────┼───────────────────────────┼────────────────────────────┤
│ Universal Fallback  │ Llama 3.1 8B (Groq)       │ Most reliable free model   │
└─────────────────────┴───────────────────────────┴────────────────────────────┘
"""
import logging
from enum import Enum
from typing import Any, List, Optional
from dataclasses import dataclass, field

from langchain_openai import ChatOpenAI
from langchain_core.runnables import RunnableLambda
from langchain_core.language_models import BaseChatModel

from app.core.config import settings

logger = logging.getLogger(__name__)


PROVIDER_CONFIG = {
    "groq": {
        "base_url_attr": "GROQ_BASE_URL",
        "api_key_attr": "GROQ_API_KEY",
        "capabilities": ["chat", "stt", "tts"],
    },
    "nvidia": {
        "base_url_attr": "NVIDIA_BASE_URL",
        "api_key_attr": "NVIDIA_API_KEY",
        "capabilities": ["chat"],
    },
    "openrouter": {
        "base_url_attr": "OPENROUTER_BASE_URL",
        "api_key_attr": "OPENROUTER_API_KEY",
        "capabilities": ["chat"],
    },
}


def _setting_has_value(attr: str | None) -> bool:
    if not attr:
        return True
    return bool(str(getattr(settings, attr, "") or "").strip())


def is_provider_configured(provider: str) -> bool:
    """Return whether a provider has the config needed for its configured role."""
    config = PROVIDER_CONFIG.get(provider)
    if not config:
        return False

    has_key = _setting_has_value(config["api_key_attr"])
    has_url = _setting_has_value(config["base_url_attr"])
    if not (has_key and has_url):
        return False

    # Check if the key is a placeholder
    key_val = str(getattr(settings, config["api_key_attr"], "") or "").strip()
    placeholders = ["your-", "your_", "change-me", "change_me", "placeholder", "sk-or-your", "nvapi-your"]
    if any(p in key_val.lower() for p in placeholders):
        return False

    return True


def get_provider_statuses() -> dict[str, dict[str, Any]]:
    """Expose non-secret AI provider configuration status for health endpoints."""
    statuses = {}
    for provider, config in PROVIDER_CONFIG.items():
        statuses[provider] = {
            "configured": is_provider_configured(provider),
            "capabilities": config["capabilities"],
            "has_api_key": _setting_has_value(config["api_key_attr"]),
            "has_base_url": _setting_has_value(config["base_url_attr"]),
        }
    return statuses


class TaskType(str, Enum):
    """Interview task types requiring different model capabilities."""
    QUESTION_GEN = "question_generation"       # Fast, creative question generation
    DEEP_FOLLOWUP = "deep_followup"            # Strong reasoning for adaptive questions
    ANSWER_EVAL = "answer_evaluation"          # Structured scoring & feedback
    CODE_EVAL = "code_evaluation"              # Code-specific analysis
    REPORT_GEN = "report_generation"           # Analytical report creation
    RESUME_PARSE = "resume_parsing"            # Fast structured extraction
    CHAT = "chat"                              # General conversation


@dataclass
class ModelSpec:
    """Specification for a single model in a fallback chain."""
    provider: str
    model_id: str
    temperature: float = 0.7
    max_tokens: Optional[int] = None
    timeout: int = 30


@dataclass
class TaskRoute:
    """Complete routing config for a task type."""
    task: TaskType
    chain: List[ModelSpec] = field(default_factory=list)
    description: str = ""


# ── Model Registry ──────────────────────────────────────────────────────────────

def _make_llm(spec: ModelSpec) -> BaseChatModel:
    """Create a ChatOpenAI instance from a ModelSpec."""
    provider_urls = {
        "groq": settings.GROQ_BASE_URL,
        "nvidia": settings.NVIDIA_BASE_URL,
        "openrouter": settings.OPENROUTER_BASE_URL,
    }
    provider_keys = {
        "groq": settings.GROQ_API_KEY,
        "nvidia": settings.NVIDIA_API_KEY,
        "openrouter": settings.OPENROUTER_API_KEY,
    }

    base_url = provider_urls.get(spec.provider)
    api_key = provider_keys.get(spec.provider, "")

    if not base_url:
        raise ValueError(f"Unknown provider: {spec.provider}")
    if not api_key:
        raise ValueError(f"Provider is not configured: {spec.provider}")

    kwargs = {
        "api_key": api_key,
        "base_url": base_url,
        "model": spec.model_id,
        "temperature": spec.temperature,
        "max_retries": 0,
        "request_timeout": spec.timeout,
    }
    if spec.max_tokens:
        kwargs["max_tokens"] = spec.max_tokens

    return ChatOpenAI(**kwargs)


def _build_chain(route: TaskRoute):
    """Build a fallback chain for a task route with logging."""
    if not route.chain:
        raise ValueError(f"No models configured for task: {route.task}")

    llms = []
    for spec in route.chain:
        if not is_provider_configured(spec.provider):
            logger.info(
                "[%s] Skipping unconfigured provider: %s/%s",
                route.task.value,
                spec.provider,
                spec.model_id,
            )
            continue
        try:
            llm = _make_llm(spec)
            llms.append((spec, llm))
        except Exception as e:
            logger.warning(f"Failed to initialize {spec.provider}/{spec.model_id}: {e}")

    if not llms:
        configured = ", ".join(
            name for name, status in get_provider_statuses().items()
            if status["configured"] and "chat" in status["capabilities"]
        ) or "none"
        raise RuntimeError(
            f"No configured chat providers available for task: {route.task}. "
            f"Configured chat providers: {configured}"
        )

    primary_spec, primary_llm = llms[0]
    fallback_llms = [llm for _, llm in llms[1:]]

    async def primary_with_logging(input_data, config=None):
        try:
            return await primary_llm.ainvoke(input_data, config=config)
        except Exception as e:
            fallback_names = " -> ".join(
                f"{s.provider}/{s.model_id}" for s, _ in llms[1:]
            )
            logger.warning(
                f"[{route.task.value}] Primary failed: "
                f"{primary_spec.provider}/{primary_spec.model_id} ({e}). "
                f"Falling back: {fallback_names}"
            )
            raise

    primary_runnable = RunnableLambda(primary_with_logging)

    if fallback_llms:
        return primary_runnable.with_fallbacks(fallback_llms)
    return primary_runnable


# ── Task Route Definitions ──────────────────────────────────────────────────────

def _get_routes() -> dict[TaskType, TaskRoute]:
    """Define model routes for each task type."""
    return {
        TaskType.QUESTION_GEN: TaskRoute(
            task=TaskType.QUESTION_GEN,
            description="Fast question generation with conversational tone",
            chain=[
                ModelSpec("groq", "llama-3.1-8b-instant", temperature=0.4, max_tokens=420, timeout=10),
                ModelSpec("nvidia", "meta/llama-3.1-8b-instruct", temperature=0.4, max_tokens=420, timeout=10),
            ],
        ),
        TaskType.DEEP_FOLLOWUP: TaskRoute(
            task=TaskType.DEEP_FOLLOWUP,
            description="Deep reasoning for adaptive follow-up questions",
            chain=[
                ModelSpec("nvidia", "meta/llama-3.1-70b-instruct", temperature=0.3, max_tokens=520, timeout=15),
                ModelSpec("groq", "llama-3.3-70b-versatile", temperature=0.3, max_tokens=520, timeout=15),
            ],
        ),
        TaskType.ANSWER_EVAL: TaskRoute(
            task=TaskType.ANSWER_EVAL,
            description="Structured scoring and feedback generation",
            chain=[
                ModelSpec("groq", "llama-3.3-70b-versatile", temperature=0.1, max_tokens=650, timeout=12),
                ModelSpec("nvidia", "meta/llama-3.1-70b-instruct", temperature=0.1, max_tokens=650, timeout=12),
            ],
        ),
        TaskType.CODE_EVAL: TaskRoute(
            task=TaskType.CODE_EVAL,
            description="Code-specific evaluation with logic analysis",
            chain=[
                ModelSpec("openrouter", "qwen/qwen-2.5-coder-32b-instruct", temperature=0.0, max_tokens=800, timeout=18),
                ModelSpec("groq", "llama-3.3-70b-versatile", temperature=0.0, max_tokens=800, timeout=15),
                ModelSpec("groq", "llama-3.1-8b-instant", temperature=0.0, max_tokens=800, timeout=10),
            ],
        ),
        TaskType.REPORT_GEN: TaskRoute(
            task=TaskType.REPORT_GEN,
            description="Analytical report generation from interview transcript",
            chain=[
                ModelSpec("nvidia", "meta/llama-3.1-70b-instruct", temperature=0.2, max_tokens=1200, timeout=25),
                ModelSpec("groq", "llama-3.3-70b-versatile", temperature=0.2, max_tokens=1200, timeout=25),
            ],
        ),
        TaskType.RESUME_PARSE: TaskRoute(
            task=TaskType.RESUME_PARSE,
            description="Fast resume text parsing and skill extraction",
            chain=[
                ModelSpec("groq", "llama-3.1-8b-instant", temperature=0.1),
                ModelSpec("nvidia", "meta/llama-3.1-8b-instruct", temperature=0.1),
            ],
        ),
        TaskType.CHAT: TaskRoute(
            task=TaskType.CHAT,
            description="General conversation and fallback",
            chain=[
                ModelSpec("groq", "llama-3.1-8b-instant", temperature=0.7),
            ],
        ),
    }


def get_route_statuses() -> dict[str, dict[str, Any]]:
    """Return route provider availability without constructing LLM clients."""
    routes = _get_routes()
    route_statuses: dict[str, dict[str, Any]] = {}

    for task_type, route in routes.items():
        providers = []
        for spec in route.chain:
            providers.append({
                "provider": spec.provider,
                "model": spec.model_id,
                "configured": is_provider_configured(spec.provider),
            })

        route_statuses[task_type.value] = {
            "description": route.description,
            "available": any(provider["configured"] for provider in providers),
            "providers": providers,
        }

    return route_statuses


# ── Cached LLM Instances ────────────────────────────────────────────────────────

_llm_cache: dict[TaskType, BaseChatModel] = {}


def get_llm(task: TaskType) -> BaseChatModel:
    """
    Get a cached LLM instance optimized for the given task.

    Args:
        task: The task type (question_generation, answer_evaluation, etc.)

    Returns:
        A LangChain LLM with fallback chain configured.
    """
    if task in _llm_cache:
        return _llm_cache[task]

    routes = _get_routes()
    route = routes.get(task)
    if not route:
        raise ValueError(f"Unknown task type: {task}")

    try:
        llm = _build_chain(route)
        _llm_cache[task] = llm
        logger.info(
            f"[{task.value}] Initialized: "
            f"{' -> '.join(f'{s.provider}/{s.model_id}' for s in route.chain)}"
        )
        return llm
    except Exception as e:
        logger.error(f"Failed to build LLM chain for {task.value}: {e}")
        raise


def clear_llm_cache():
    """Clear the LLM cache (useful for testing or reconfiguration)."""
    _llm_cache.clear()


# ── Backward-Compatible API ─────────────────────────────────────────────────────
# These maintain compatibility with existing code while using the new router.

def get_fast_llm():
    """Question Generation — fast, creative model."""
    return get_llm(TaskType.QUESTION_GEN)


def get_adaptive_llm():
    """Adaptive Follow-ups — strong reasoning model."""
    return get_llm(TaskType.DEEP_FOLLOWUP)


def get_strong_llm():
    """Comprehensive Feedback Analysis — best reasoning model."""
    return get_llm(TaskType.ANSWER_EVAL)


def get_code_llm():
    """Code Evaluation — code-specialized model."""
    return get_llm(TaskType.CODE_EVAL)


def get_report_llm():
    """Report Generation — analytical model for final reports."""
    return get_llm(TaskType.REPORT_GEN)


def get_resume_llm():
    """Resume Parsing — fast extraction model."""
    return get_llm(TaskType.RESUME_PARSE)


def get_chat_llm():
    """General Chat — fallback model."""
    return get_llm(TaskType.CHAT)


def get_fallback_llm():
    """Universal fallback — most reliable free model."""
    if not is_provider_configured("groq"):
        raise RuntimeError("Groq is not configured for fallback LLM")

    return ChatOpenAI(
        api_key=settings.GROQ_API_KEY,
        base_url=settings.GROQ_BASE_URL,
        model="llama-3.1-8b-instant",
        temperature=0.7,
    )
