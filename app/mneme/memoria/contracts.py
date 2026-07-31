"""Define Mneme-side contracts shared by Agent orchestration ports and adapters.

These models keep transport, persistence, and runtime implementations replaceable.
"""

import uuid
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from app.mneme.memoria.context_governance import ContextAssemblyReport

AnswerMode = Literal["kb_qa", "memory_query", "profile_query", "analysis_query", "general_chat"]
RetrievalScope = Literal["hybrid", "memory_only"]


class AgentHistoryMessage(BaseModel):
    message_id: str | None = None
    role: Literal["user", "assistant"]
    content: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)


class AgentRequest(BaseModel):
    """Validated input accepted by the Mneme-side Agent orchestration layer.

    The request carries explicit user, session, answer-mode, and bounded
    context data. Transport adapters must not infer missing permissions.
    """
    question: str
    knowledge_base_id: str | None = Field(default=None, min_length=1)
    user_id: int
    session_id: str | None = None
    run_id: str | None = None
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid.uuid4().hex}")
    top_k: int = Field(default=4, ge=1, le=10)
    answer_mode: AnswerMode = "kb_qa"
    llm_config: dict[str, Any] | None = None
    history: list[AgentHistoryMessage] = Field(default_factory=list)
    history_summary: str = ""
    history_compaction: dict[str, Any] | None = None
    history_prepared: bool = False

    @field_validator("history_compaction", mode="before")
    @classmethod
    def serialize_context_assembly_report(cls, value: Any) -> Any:
        if isinstance(value, ContextAssemblyReport):
            return value.model_dump(mode="json")
        return value


class AgentResponse(BaseModel):
    """Stable Agent result returned to chat, automation, and API callers.

    The contract separates answer text, citations, uncertainty, runtime
    metadata, and proposed actions so callers can persist them safely.
    """
    answer: str
    sources: list[dict[str, Any]] = Field(default_factory=list)
    citations: list[dict[str, Any]] = Field(default_factory=list)
    confidence: str
    uncertainty: str | None = None
    route: dict[str, Any] | None = None
    debug: dict[str, Any] | None = None
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)

    def to_legacy_result(self) -> dict[str, Any]:
        return self.model_dump()
