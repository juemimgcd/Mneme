"""Retrieve document chunks by pgvector cosine distance inside an authorized scope.

Owner, knowledge-base, projection, and active-state filters are applied before ranking and limiting.
"""

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.models.document_chunk import DocumentChunk
from app.mneme.memoria.server.models.document_projection import DocumentProjection
from app.mneme.memoria.server.retrieval.contracts import DocumentSearchHit, RetrievalScope
from app.mneme.memoria.server.retrieval.fusion import FUSION_CANDIDATE_K
from app.mneme.memoria.server.services.embeddings import embed_texts


async def search_vector(
    db: AsyncSession,
    *,
    scope: RetrievalScope,
    query: str,
    limit: int,
) -> list[DocumentSearchHit]:
    """Return the nearest active document chunks in the authorized scope.

    The backend keeps a wider candidate pool for final fusion. Query embeddings
    are normalized by the embedding service. Owner,
    knowledge-base, and projection filters are part of the SQL statement so
    unauthorized candidates never participate in nearest-neighbor ranking.
    """
    if limit <= 0:
        return []

    query_embedding = (await embed_texts([query]))[0]
    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
    await db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    similarity = (1 - distance).label("score")
    statement = (
        select(
            DocumentChunk.chunk_id,
            DocumentChunk.document_id,
            DocumentChunk.document_version,
            DocumentChunk.chunk_index,
            DocumentChunk.content,
            DocumentChunk.page_no,
            DocumentChunk.section_path,
            DocumentProjection.file_name,
            similarity,
        )
        .join(
            DocumentProjection,
            DocumentProjection.projection_id == DocumentChunk.projection_id,
        )
        .where(
            DocumentChunk.owner_id == scope.owner_id,
            DocumentChunk.knowledge_base_id == scope.knowledge_base_id,
            DocumentChunk.is_active.is_(True),
            DocumentProjection.owner_id == scope.owner_id,
            DocumentProjection.knowledge_base_id == scope.knowledge_base_id,
            DocumentProjection.status == "active",
        )
        .order_by(distance.asc(), DocumentChunk.chunk_id.asc())
        .limit(max(limit, FUSION_CANDIDATE_K))
    )
    rows = (await db.execute(statement)).mappings().all()
    return [
        DocumentSearchHit(
            chunk_id=row["chunk_id"],
            document_id=row["document_id"],
            content=row["content"],
            score=float(row["score"]),
            metadata={
                "document_version": row["document_version"],
                "file_name": row["file_name"],
                "chunk_index": row["chunk_index"],
                "page_no": row["page_no"],
                "section_path": row["section_path"],
            },
        )
        for row in rows
    ]
