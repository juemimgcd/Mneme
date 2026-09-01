"""Retrieve document chunks by BGE-M3 sparse inner-product similarity."""

from pgvector import SparseVector
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.models.document_chunk import DocumentChunk
from app.mneme.memoria.server.models.document_projection import DocumentProjection
from app.mneme.memoria.server.retrieval.contracts import DocumentSearchHit, RetrievalScope
from app.mneme.memoria.server.retrieval.fusion import FUSION_CANDIDATE_K


async def sparse_scope_ready(db: AsyncSession, *, scope: RetrievalScope) -> bool:
    missing = (
        select(DocumentChunk.id)
        .join(DocumentProjection)
        .where(
            DocumentChunk.owner_id == scope.owner_id,
            DocumentChunk.knowledge_base_id == scope.knowledge_base_id,
            DocumentChunk.is_active.is_(True),
            DocumentChunk.sparse_embedding.is_(None),
            DocumentProjection.owner_id == scope.owner_id,
            DocumentProjection.knowledge_base_id == scope.knowledge_base_id,
            DocumentProjection.status == "active",
        )
        .limit(1)
    )
    return (await db.scalar(missing)) is None


async def search_sparse(
    db: AsyncSession,
    *,
    scope: RetrievalScope,
    query_embedding: SparseVector,
    limit: int,
) -> list[DocumentSearchHit]:
    if limit <= 0 or not query_embedding.indices():
        return []

    await db.execute(text("SET LOCAL hnsw.ef_search = 100"))
    await db.execute(text("SET LOCAL hnsw.iterative_scan = strict_order"))
    distance = DocumentChunk.sparse_embedding.max_inner_product(query_embedding)
    similarity = (-distance).label("score")
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
        .join(DocumentProjection)
        .where(
            DocumentChunk.owner_id == scope.owner_id,
            DocumentChunk.knowledge_base_id == scope.knowledge_base_id,
            DocumentChunk.is_active.is_(True),
            DocumentChunk.sparse_embedding.is_not(None),
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
