"""Expose profile evidence as a constrained view over governed long-term memories.

Only profile facts, preferences, goals, and constraints are eligible for this source.
"""

from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence
from app.mneme.memoria.server.retrieval.memories import MemoryRetriever

PROFILE_MEMORY_TYPES = ("profile_fact", "preference", "goal", "constraint")


class ProfileRetriever:
    """Present profile-related memories as a distinct evidence source.

    The wrapper intentionally reuses MemoryRetriever so profile queries keep
    identical revision, validity, and authorization behavior.
    """
    def __init__(self, memories: MemoryRetriever | None = None) -> None:
        self._memories = memories or MemoryRetriever()

    async def search(
        self,
        *,
        owner_id: int,
        knowledge_base_id: str | None,
        query: str,
        top_k: int,
    ) -> list[RetrievedEvidence]:
        """Retrieve current profile facts, preferences, goals, and constraints.

        Results are labeled as profile evidence even though canonical memory is
        the underlying governed storage.
        """
        return await self._memories.search(
            owner_id=owner_id,
            knowledge_base_id=knowledge_base_id,
            query=query,
            top_k=top_k,
            temporal_scope="current",
            memory_types=PROFILE_MEMORY_TYPES,
            evidence_type="profile",
        )
