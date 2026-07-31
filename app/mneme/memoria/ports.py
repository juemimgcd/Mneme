"""Declare dependency-inversion ports used by the Mneme-side Agent orchestrator.

Concrete HTTP, persistence, queue, and notification adapters implement these protocols.
"""

from typing import Protocol

from app.mneme.memoria.contracts import AgentRequest, AgentResponse


class AgentAnswerEngine(Protocol):
    """Protocol implemented by the component that produces a grounded answer.

    Implementations receive an already validated Agent request and must
    return the stable response contract without persisting chat state.
    """

    async def generate(self, request: AgentRequest) -> AgentResponse: ...
