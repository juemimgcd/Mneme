"""Track shared time, retrieval, and supplemental-round budgets for Multi-Agent execution.

Reservations occur before work starts so concurrent roles cannot collectively exceed configured limits.
"""

from time import perf_counter

from app.mneme.memoria.server.multi_agent.contracts import (
    BudgetUsage,
    MultiAgentBudgetLimits,
)


class MultiAgentBudgetExceeded(RuntimeError):
    def __init__(self, reason_code: str) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code


class SharedMultiAgentBudget:
    """Mutable request-local ledger for time and retrieval reservations.

    The object is shared by coordinator-owned role execution. Reservations
    happen before tasks launch, preventing concurrent oversubscription.
    """
    def __init__(self, limits: MultiAgentBudgetLimits) -> None:
        self.limits = limits
        self._started = perf_counter()
        self._retrieval_top_k = 0
        self._supplemental_rounds = 0

    @property
    def remaining_seconds(self) -> float:
        return max(0.0, self.limits.deadline_seconds - (perf_counter() - self._started))

    def require_time(self) -> None:
        if self.remaining_seconds <= 0:
            raise MultiAgentBudgetExceeded("MULTI_AGENT_DEADLINE_EXCEEDED")

    def reserve_retrieval(self, top_k: int) -> None:
        """Reserve candidate capacity before starting a source retrieval.

        Raises:
            MultiAgentBudgetExceeded: If time or total retrieval capacity is exhausted.
        """
        self.require_time()
        if self._retrieval_top_k + top_k > self.limits.max_retrieval_top_k:
            raise MultiAgentBudgetExceeded("MULTI_AGENT_RETRIEVAL_BUDGET_EXCEEDED")
        self._retrieval_top_k += top_k

    def reserve_supplemental_round(self) -> None:
        """Reserve the single optional supplemental retrieval round.

        Raises:
            MultiAgentBudgetExceeded: If the deadline or round limit is exhausted.
        """
        self.require_time()
        if self._supplemental_rounds >= self.limits.max_supplemental_rounds:
            raise MultiAgentBudgetExceeded("MULTI_AGENT_SUPPLEMENTAL_BUDGET_EXCEEDED")
        self._supplemental_rounds += 1

    def snapshot(
        self,
        *,
        model_calls: int = 0,
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        estimated_cost: float = 0,
    ) -> BudgetUsage:
        """Return an immutable usage view for persistence and telemetry.

        Model usage is supplied by the caller because generation occurs outside
        the retrieval-role executor.
        """
        return BudgetUsage(
            model_calls=model_calls,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            retrieval_top_k=self._retrieval_top_k,
            estimated_cost=estimated_cost,
            supplemental_rounds=self._supplemental_rounds,
            elapsed_ms=max(0, round((perf_counter() - self._started) * 1000)),
        )
