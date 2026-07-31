"""Implement Memoria documents application behavior.

The module keeps orchestration policy explicit and delegates persistence and external effects through boundaries.
"""

from app.mneme.memoria.server.multi_agent.roles.base import SourceRetrievalAgent


class DocumentRetrievalAgent(SourceRetrievalAgent):
    pass
