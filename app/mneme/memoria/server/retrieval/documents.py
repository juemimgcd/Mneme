"""Combine dense-vector and lexical document retrieval into one document evidence source.

The component owns document-level fusion but not cross-source answer planning.
"""

from app.mneme.memoria.server.database import open_read_session
from app.mneme.memoria.server.retrieval.contracts import RetrievalScope, RetrievedEvidence
from app.mneme.memoria.server.retrieval.fusion import (
    BGE_M3_DENSE_SCORE_WEIGHT,
    BGE_M3_KEYWORD_SCORE_WEIGHT,
    BGE_M3_SPARSE_SCORE_WEIGHT,
    DENSE_SCORE_WEIGHT,
    normalized_score_fusion,
)
from app.mneme.memoria.server.retrieval.keyword import search_keyword
from app.mneme.memoria.server.retrieval.sparse import search_sparse, sparse_scope_ready
from app.mneme.memoria.server.retrieval.vector import search_vector
from app.mneme.memoria.server.services.embeddings import (
    embed_texts_with_sparse,
    sparse_embeddings_enabled,
)


class DocumentRetriever:
    """Retrieve document evidence by combining dense and lexical rankings.

    The retriever opens one scoped read session and returns normalized
    document evidence; cross-source fusion remains a runtime responsibility.
    """
    async def search(
        self,
        scope: RetrievalScope,
        query: str,
        top_k: int,
    ) -> list[RetrievedEvidence]:
        """Search vector and keyword indexes and combine normalized raw scores.

        Both queries apply the same scope and active-projection constraints.
        Empty or non-positive limits return no evidence without touching storage.
        """
        if top_k <= 0:
            return []

        sparse_embedding = None
        if sparse_embeddings_enabled():
            dense_embeddings, sparse_embeddings = await embed_texts_with_sparse([query])
            dense_embedding = dense_embeddings[0]
            sparse_embedding = sparse_embeddings[0]

        async with open_read_session() as db:
            vector_hits = (
                await search_vector(
                    db,
                    scope=scope,
                    query=query,
                    limit=top_k,
                    query_embedding=dense_embedding,
                )
                if sparse_embedding is not None
                else await search_vector(db, scope=scope, query=query, limit=top_k)
            )
            keyword_hits = await search_keyword(db, scope=scope, query=query, limit=top_k)
            sparse_hits = (
                await search_sparse(
                    db,
                    scope=scope,
                    query_embedding=sparse_embedding,
                    limit=top_k,
                )
                if sparse_embedding is not None and await sparse_scope_ready(db, scope=scope)
                else []
            )
        if sparse_hits:
            return normalized_score_fusion(
                (vector_hits, sparse_hits, keyword_hits),
                top_k=top_k,
                weights=(
                    BGE_M3_DENSE_SCORE_WEIGHT,
                    BGE_M3_SPARSE_SCORE_WEIGHT,
                    BGE_M3_KEYWORD_SCORE_WEIGHT,
                ),
            )
        return normalized_score_fusion(
            (vector_hits, keyword_hits),
            top_k=top_k,
            weights=(DENSE_SCORE_WEIGHT, 1.0 - DENSE_SCORE_WEIGHT),
        )
