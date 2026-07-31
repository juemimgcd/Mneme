"""Expose the Mneme-side application service for submitting and controlling Agent work.

Durable run creation and queue delivery stay separate so API retries cannot duplicate execution.
"""

import asyncio
from collections.abc import AsyncIterator

from app.mneme.memoria.contracts import AgentRequest, AgentResponse
from app.mneme.memoria.events import AgentEvent
from app.mneme.memoria.ports import AgentAnswerEngine


class MemoriaAgent:
    """Mneme-side facade for synchronous and streaming Memoria execution.

    The facade keeps callers independent from the concrete orchestrator and
    guarantees both delivery styles use the same validated request path.
    """
    def __init__(self, answer_engine: AgentAnswerEngine):
        self.answer_engine = answer_engine

    async def run(self, request: AgentRequest) -> AgentResponse:
        """Execute one Agent request and return its validated terminal response.

        The method delegates all routing and side effects to the orchestrator;
        it does not introduce a second retrieval or prompting implementation.
        """
        return await self.answer_engine.generate(request)

    async def stream(
        self,
        request: AgentRequest,
        *,
        abort_signal: asyncio.Event | None = None,
    ) -> AsyncIterator[AgentEvent]:
        """Stream sanitized lifecycle events emitted by the shared execution path.

        Streaming changes delivery only. It must preserve the same budgets,
        persistence ordering, and terminal response semantics as ``run``.
        """
        stream_method = getattr(self.answer_engine, "stream", None)
        if stream_method is not None:
            async for event in stream_method(request, abort_signal=abort_signal):
                yield event
            return

        yield AgentEvent.lifecycle("start", loop_index=0)
        response = await self.run(request)
        yield AgentEvent.assistant_delta(response.answer, loop_index=0)
        yield AgentEvent.lifecycle("end", loop_index=0, response=response.model_dump())
