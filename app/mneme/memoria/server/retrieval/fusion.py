"""Fuse document rankings with deterministic reciprocal-rank fusion.

Fusion uses rank positions instead of incomparable raw vector and lexical score scales.
"""

from collections.abc import Sequence

from app.mneme.memoria.server.retrieval.contracts import DocumentSearchHit, RetrievedEvidence

RRF_CONSTANT = 60
FUSION_CANDIDATE_K = 100
LEXICAL_RRF_WEIGHT = 0.55


def reciprocal_rank_fusion(
    rankings: Sequence[Sequence[DocumentSearchHit]],
    *,
    top_k: int,
    weights: Sequence[float] | None = None,
) -> list[RetrievedEvidence]:
    """Fuse backend rankings without comparing their incompatible raw scores.

    Each unique chunk contributes ``weight / (60 + rank)`` once per ranking.
    Omitted weights preserve equal fusion for existing callers.
    Deterministic chunk-ID tie breaking keeps replayed evaluations stable.
    """
    if top_k <= 0:
        return []
    if weights is not None and len(weights) != len(rankings):
        raise ValueError("weights must match the number of rankings")

    hits_by_chunk_id: dict[str, DocumentSearchHit] = {}
    scores_by_chunk_id: dict[str, float] = {}
    for ranking_index, ranking in enumerate(rankings):
        weight = weights[ranking_index] if weights is not None else 1.0
        seen_chunk_ids: set[str] = set()
        for rank, hit in enumerate(ranking, start=1):
            if hit.chunk_id in seen_chunk_ids:
                continue
            seen_chunk_ids.add(hit.chunk_id)
            hits_by_chunk_id.setdefault(hit.chunk_id, hit)
            scores_by_chunk_id[hit.chunk_id] = (
                scores_by_chunk_id.get(hit.chunk_id, 0.0)
                + weight / (RRF_CONSTANT + rank)
            )

    ranked_chunk_ids = sorted(
        scores_by_chunk_id,
        key=lambda chunk_id: (-scores_by_chunk_id[chunk_id], chunk_id),
    )[:top_k]
    return [
        RetrievedEvidence(
            evidence_id=chunk_id,
            source_type="document",
            source_id=hits_by_chunk_id[chunk_id].document_id,
            content=hits_by_chunk_id[chunk_id].content,
            score=scores_by_chunk_id[chunk_id],
            metadata=hits_by_chunk_id[chunk_id].metadata,
        )
        for chunk_id in ranked_chunk_ids
    ]
