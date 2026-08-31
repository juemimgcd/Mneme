"""Retrieve governed memory revisions for the requested owner and temporal scope.

Only active revisions are returned for current queries; history queries retain version visibility.
"""

from datetime import datetime
from typing import Literal

from sqlalchemy import and_, func, or_, select, text

from app.mneme.memoria.server.database import open_read_session
from app.mneme.memoria.server.models.canonical_memory import CanonicalMemory
from app.mneme.memoria.server.models.memory_revision import MemoryRevision
from app.mneme.memoria.server.retrieval.contracts import RetrievedEvidence

TemporalScope = Literal["current", "history"]


def _knowledge_base_clause(knowledge_base_id: str | None):
    if knowledge_base_id is None:
        return CanonicalMemory.knowledge_base_id.is_(None)
    return CanonicalMemory.knowledge_base_id == knowledge_base_id


class MemoryRetriever:
    """Read governed canonical-memory revisions as answer evidence.

    The retriever can select current or historical revisions and constrain
    memory types while preserving owner and optional knowledge-base scope.
    """

    async def search(
        self,
        *,
        owner_id: int,
        knowledge_base_id: str | None,
        query: str,
        top_k: int,
        temporal_scope: TemporalScope = "current",
        memory_types: tuple[str, ...] | None = None,
        excluded_memory_types: tuple[str, ...] | None = None,
        evidence_type: Literal["memory", "profile"] = "memory",
        query_embedding: list[float] | None = None,
    ) -> list[RetrievedEvidence]:
        """Search scoped memory revisions and return normalized evidence records.

        Current queries require the canonical memory's active revision and
        validity window. Text matching influences order but never expands scope.
        """
        if top_k <= 0:
            return []

        now = func.now()
        text_value = func.concat_ws(
            " ",
            MemoryRevision.subject,
            MemoryRevision.predicate,
            MemoryRevision.value,
        )
        filters = [
            CanonicalMemory.owner_id == owner_id,
            _knowledge_base_clause(knowledge_base_id),
            MemoryRevision.owner_id == owner_id,
            (
                MemoryRevision.knowledge_base_id.is_(None)
                if knowledge_base_id is None
                else MemoryRevision.knowledge_base_id == knowledge_base_id
            ),
            MemoryRevision.valid_from <= now,
        ]
        if temporal_scope == "current":
            filters.extend(
                [
                    CanonicalMemory.status == "active",
                    CanonicalMemory.active_revision_id == MemoryRevision.revision_id,
                    or_(MemoryRevision.valid_to.is_(None), MemoryRevision.valid_to > now),
                ]
            )
        if memory_types:
            filters.append(CanonicalMemory.memory_type.in_(memory_types))
        if excluded_memory_types:
            filters.append(CanonicalMemory.memory_type.not_in(excluded_memory_types))

        pattern = f"%{query.strip()}%"
        relevance = text_value.ilike(pattern)
        async with open_read_session() as db:
            use_semantic = query_embedding is not None
            if use_semantic:
                missing_embedding = (
                    select(MemoryRevision.revision_id)
                    .join(CanonicalMemory, MemoryRevision.memory_id == CanonicalMemory.memory_id)
                    .where(and_(*filters), MemoryRevision.embedding.is_(None))
                    .limit(1)
                )
                use_semantic = not bool(await db.scalar(select(missing_embedding.exists())))

            semantic_distance = (
                MemoryRevision.embedding.cosine_distance(query_embedding).label("semantic_distance")
                if use_semantic
                else None
            )
            columns = [
                CanonicalMemory.memory_id,
                CanonicalMemory.memory_type,
                CanonicalMemory.confidence,
                CanonicalMemory.retrieval_weight,
                MemoryRevision.revision_id,
                MemoryRevision.subject,
                MemoryRevision.predicate,
                MemoryRevision.value,
                MemoryRevision.valid_from,
                MemoryRevision.valid_to,
            ]
            if semantic_distance is not None:
                await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
                await db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
                columns.append(semantic_distance)
            ordering = [semantic_distance.asc()] if semantic_distance is not None else [relevance.desc()]
            statement = (
                select(*columns)
                .join(MemoryRevision, MemoryRevision.memory_id == CanonicalMemory.memory_id)
                .where(and_(*filters))
                .order_by(
                    *ordering,
                    CanonicalMemory.retrieval_weight.desc(),
                    CanonicalMemory.confidence.desc(),
                    MemoryRevision.valid_from.desc(),
                )
                .limit(top_k)
            )
            rows = (await db.execute(statement)).mappings().all()

        return [
            RetrievedEvidence(
                evidence_id=f"{evidence_type}:{row['revision_id']}",
                source_type=evidence_type,
                source_id=row["memory_id"],
                content=f"{row['subject']} {row['predicate']} {row['value']}",
                score=(
                    1.0 - float(row["semantic_distance"])
                    if row.get("semantic_distance") is not None
                    else float(row["confidence"])
                ),
                metadata={
                    "memory_type": row["memory_type"],
                    "confidence": float(row["confidence"]),
                    "retrieval_weight": float(row.get("retrieval_weight", 1.0)),
                    "semantic_score": (
                        1.0 - float(row["semantic_distance"]) if row.get("semantic_distance") is not None else None
                    ),
                    "valid_from": _isoformat(row["valid_from"]),
                    "valid_to": _isoformat(row["valid_to"]),
                },
            )
            for row in rows
        ]


def _isoformat(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
