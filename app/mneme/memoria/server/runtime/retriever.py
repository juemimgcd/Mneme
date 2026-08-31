"""Retrieve scoped evidence from the sources selected by an answer-mode plan.

Independent sources may degrade separately; successful rankings are fused without crossing owner scope.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from app.mneme.memoria.server.observability.context import safe_log
from app.mneme.memoria.server.retrieval.contracts import RetrievalScope, RetrievedEvidence
from app.mneme.memoria.server.retrieval.documents import DocumentRetriever
from app.mneme.memoria.server.retrieval.memories import MemoryRetriever
from app.mneme.memoria.server.retrieval.profile import PROFILE_MEMORY_TYPES, ProfileRetriever
from app.mneme.memoria.server.retrieval.relations import RelationRetriever
from app.mneme.memoria.server.runtime.contracts import RetrievalRequest
from app.mneme.memoria.server.services.embeddings import embed_texts

RRF_CONSTANT = 60
logger = logging.getLogger(__name__)


class ScopedEvidenceRetriever:
    """Retrieve and fuse evidence allowed by a deterministic retrieval plan.

    Each source receives the same owner and knowledge-base scope. A source
    failure is logged and isolated; all-source failure remains terminal.
    """

    def __init__(
        self,
        *,
        documents_factory: Callable[[], DocumentRetriever] = DocumentRetriever,
        memories_factory: Callable[[], MemoryRetriever] = MemoryRetriever,
        profile_factory: Callable[[], ProfileRetriever] = ProfileRetriever,
        relations_factory: Callable[[], RelationRetriever] = RelationRetriever,
    ) -> None:
        self._documents_factory = documents_factory
        self._memories_factory = memories_factory
        self._profile_factory = profile_factory
        self._relations_factory = relations_factory
        self._embed_memory_queries = memories_factory is MemoryRetriever
        self._embed_profile_queries = profile_factory is ProfileRetriever

    async def retrieve(self, request: RetrievalRequest) -> list[RetrievedEvidence]:
        """Execute selected evidence-source searches concurrently and fuse results.

        Returns:
            At most ``request.top_k`` normalized evidence items ordered by RRF.

        Raises:
            ValueError: If document retrieval lacks a knowledge-base scope.
            Exception: The first source error when no source returns a ranking.
        """
        if not request.plan.uses_private_sources:
            return []
        if request.plan.document and request.knowledge_base_id is None:
            raise ValueError("document retrieval requires a knowledge base scope")

        searches: list[tuple[str, Awaitable[list[RetrievedEvidence]]]] = []

        async def embed_memory_query() -> list[float] | None:
            try:
                return (await embed_texts([request.question]))[0]
            except asyncio.CancelledError:
                raise
            except Exception:
                safe_log(
                    logger,
                    logging.WARNING,
                    "answer_phase",
                    phase="retrieve_memory_embedding",
                    status="failed",
                    error_code="AGENT_RETRIEVAL_EMBEDDING_FAILED",
                )
                return None

        memory_embedding_task = (
            asyncio.create_task(embed_memory_query())
            if (
                (request.plan.memory and self._embed_memory_queries)
                or (request.plan.profile and self._embed_profile_queries)
            )
            else None
        )
        if request.plan.document:
            searches.append(
                (
                    "document",
                    self._documents_factory().search(
                        RetrievalScope(
                            owner_id=request.owner_id,
                            knowledge_base_id=request.knowledge_base_id,
                        ),
                        request.question,
                        request.top_k,
                    ),
                )
            )
        if request.plan.memory:

            async def search_memories() -> list[RetrievedEvidence]:
                values = dict(
                    owner_id=request.owner_id,
                    knowledge_base_id=request.knowledge_base_id,
                    query=request.question,
                    top_k=request.top_k,
                    temporal_scope=request.temporal_scope,
                    excluded_memory_types=PROFILE_MEMORY_TYPES if request.plan.profile else None,
                )
                if self._embed_memory_queries:
                    assert memory_embedding_task is not None
                    query_embedding = await memory_embedding_task
                    if query_embedding is not None:
                        values["query_embedding"] = query_embedding
                return await self._memories_factory().search(**values)

            searches.append(
                (
                    "memory",
                    search_memories(),
                )
            )
        if request.plan.profile:

            async def search_profile() -> list[RetrievedEvidence]:
                values = dict(
                    owner_id=request.owner_id,
                    knowledge_base_id=request.knowledge_base_id,
                    query=request.question,
                    top_k=request.top_k,
                )
                if self._embed_profile_queries:
                    assert memory_embedding_task is not None
                    query_embedding = await memory_embedding_task
                    if query_embedding is not None:
                        values["query_embedding"] = query_embedding
                return await self._profile_factory().search(**values)

            searches.append(
                (
                    "profile",
                    search_profile(),
                )
            )
        if request.plan.relations:
            searches.append(
                (
                    "relation",
                    self._relations_factory().search(
                        owner_id=request.owner_id,
                        knowledge_base_id=request.knowledge_base_id,
                        query=request.question,
                        top_k=request.top_k,
                    ),
                )
            )

        results = await asyncio.gather(*(search for _, search in searches), return_exceptions=True)
        rankings: list[list[RetrievedEvidence]] = []
        first_error: Exception | None = None
        for (source, _), result in zip(searches, results, strict=True):
            if isinstance(result, BaseException):
                if isinstance(result, asyncio.CancelledError):
                    raise result
                if first_error is None and isinstance(result, Exception):
                    first_error = result
                safe_log(
                    logger,
                    logging.WARNING,
                    "answer_phase",
                    phase=f"retrieve_{source}",
                    status="failed",
                    error_code="AGENT_RETRIEVAL_SOURCE_FAILED",
                )
                continue
            rankings.append(result)

        if not rankings and first_error is not None:
            raise first_error
        return _reciprocal_rank_fusion(rankings, top_k=request.top_k)


def _reciprocal_rank_fusion(
    rankings: list[list[RetrievedEvidence]],
    *,
    top_k: int,
) -> list[RetrievedEvidence]:
    if top_k <= 0:
        return []
    items: dict[str, RetrievedEvidence] = {}
    scores: dict[str, float] = {}
    source_order: dict[str, int] = {}
    for ranking_index, ranking in enumerate(rankings):
        seen: set[str] = set()
        for rank, item in enumerate(ranking, start=1):
            if item.evidence_id in seen:
                continue
            seen.add(item.evidence_id)
            items.setdefault(item.evidence_id, item)
            source_order.setdefault(item.evidence_id, ranking_index)
            scores[item.evidence_id] = scores.get(item.evidence_id, 0.0) + 1.0 / (RRF_CONSTANT + rank)
    evidence_ids = sorted(
        scores,
        key=lambda evidence_id: (
            -scores[evidence_id],
            source_order[evidence_id],
            evidence_id,
        ),
    )[:top_k]
    return [
        items[evidence_id].model_copy(
            update={
                "score": scores[evidence_id],
                "metadata": {
                    **items[evidence_id].metadata,
                    "fusion": "rrf",
                },
            }
        )
        for evidence_id in evidence_ids
    ]
