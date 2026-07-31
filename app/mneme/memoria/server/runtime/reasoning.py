"""Implement the bounded model-review loop used before an answer is finalized.

Only outcome-level progress crosses steps; hidden chain-of-thought is neither requested nor stored.
"""

from dataclasses import dataclass
from typing import Literal

ReasoningDecision = Literal["continue", "final"]
ReasoningStopReason = Literal["model_final", "max_steps", "token_budget"]


@dataclass(frozen=True)
class ReasoningTransition:
    should_continue: bool
    next_step_index: int
    summary: str
    stop_reason: ReasoningStopReason | None


def transition_reasoning_step(
    *,
    step_index: int,
    max_steps: int,
    decision: ReasoningDecision,
    summary: str,
    max_summary_chars: int,
    budget_exhausted: bool,
) -> ReasoningTransition:
    """Decide whether a bounded reasoning loop should continue or terminate.

    The transition considers the model decision, configured step limit, and
    aggregate completion-token budget. Only a short outcome-level note may
    be carried forward; hidden reasoning is never persisted.
    """
    if not 1 <= step_index <= max_steps:
        raise ValueError("step_index must be within max_steps")
    normalized = " ".join(summary.split())[: max(0, max_summary_chars)]
    if decision == "final":
        return ReasoningTransition(False, step_index, normalized, "model_final")
    if budget_exhausted:
        return ReasoningTransition(False, step_index, normalized, "token_budget")
    if step_index == max_steps:
        return ReasoningTransition(False, step_index, normalized, "max_steps")
    return ReasoningTransition(True, step_index + 1, normalized, None)
