"""Timing and precision contracts for the live interview critical path."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable


# Budgets are intentionally conservative: a candidate should receive visible
# progress feedback quickly while slower optional work falls back safely.
DEFAULT_BUDGETS_MS: dict[str, int] = {
    "response_validation": 50,
    "state_read": 250,
    "rag_context": 800,
    "code_execution": 15_000,
    "evaluation": 12_000,
    "question_generation": 10_000,
    "question_audio": 3_000,
    "state_write": 500,
    "turn_total": 20_000,
}


@dataclass
class TimingProbe:
    """Monotonic timing accumulator for one candidate turn."""

    started_at: float = field(default_factory=time.perf_counter)
    stages: Dict[str, float] = field(default_factory=dict)

    def mark(self, name: str, started_at: float) -> float:
        elapsed_ms = round((time.perf_counter() - started_at) * 1000, 2)
        self.stages[name] = elapsed_ms
        return elapsed_ms

    @property
    def total_ms(self) -> float:
        return round((time.perf_counter() - self.started_at) * 1000, 2)

    def snapshot(self) -> dict[str, Any]:
        return {"stages": dict(self.stages), "total_ms": self.total_ms}


def elapsed_ms(started_at: float) -> float:
    return round((time.perf_counter() - started_at) * 1000, 2)


def bounded_context(items: Iterable[Any], limit: int, chars: int) -> list[str]:
    """Keep model context bounded for predictable latency and precision."""
    output: list[str] = []
    remaining = max(0, chars)
    for item in list(items)[-max(0, limit):]:
        text = str(item or "")
        if remaining <= 0:
            break
        clipped = text[:remaining]
        output.append(clipped)
        remaining -= len(clipped)
    return output


def precision_contract(value: dict[str, Any], *, required: Iterable[str], defaults: dict[str, Any]) -> dict[str, Any]:
    """Normalize structured model output without silently accepting malformed fields."""
    normalized = dict(defaults)
    normalized.update(value or {})
    for key in required:
        if normalized.get(key) in (None, ""):
            raise ValueError(f"Missing required structured field: {key}")
    return normalized
