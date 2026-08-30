"""Rerank caller-supplied eligible ads using consented low-sensitivity preferences."""

import logging

from sqlalchemy import select

from app.mneme.memoria.server.contracts.recommendations import (
    AdCandidate,
    AdRecommendationItem,
    AdRecommendationRequest,
    AdRecommendationResponse,
)
from app.mneme.memoria.server.database import open_read_session
from app.mneme.memoria.server.models.canonical_memory import CanonicalMemory
from app.mneme.memoria.server.models.memory_settings import MemorySettings
from app.mneme.memoria.server.observability.context import safe_log
from app.mneme.memoria.server.services.embeddings import embed_texts

PROFILE_MEMORY_LIMIT = 8
SEMANTIC_WEIGHT = 0.75
logger = logging.getLogger(__name__)


async def recommend_ads(request: AdRecommendationRequest) -> AdRecommendationResponse:
    preferences = await _load_preferences(request)
    if not preferences:
        return _fallback(request)

    profile_text = " ".join(
        f"{memory.subject} {memory.predicate} {memory.value}"
        for memory in preferences
    )
    candidate_texts = [
        " ".join((candidate.title, candidate.description, *candidate.tags)).strip()
        for candidate in request.candidates
    ]
    try:
        profile_vector, *candidate_vectors = await embed_texts([profile_text, *candidate_texts])
    except Exception:
        safe_log(
            logger,
            logging.WARNING,
            "ad_recommendation",
            status="degraded",
            error_code="AD_EMBEDDING_FAILED",
        )
        return _fallback(request)

    profile_folded = profile_text.casefold()
    scored = [
        (
            _score(profile_vector, vector, candidate.business_score),
            index,
            candidate,
            [tag for tag in candidate.tags if tag.casefold() in profile_folded],
        )
        for index, (candidate, vector) in enumerate(zip(request.candidates, candidate_vectors, strict=True))
    ]
    scored.sort(key=lambda item: (-item[0], item[1]))
    return AdRecommendationResponse(
        request_id=request.request_id,
        personalized=True,
        items=[
            AdRecommendationItem(
                ad_id=candidate.ad_id,
                score=round(score, 6),
                matched_topics=matched_topics,
            )
            for score, _, candidate, matched_topics in scored[: request.limit]
        ],
    )


async def _load_preferences(request: AdRecommendationRequest) -> list[CanonicalMemory]:
    scope = (
        CanonicalMemory.knowledge_base_id.is_(None)
        if request.knowledge_base_id is None
        else CanonicalMemory.knowledge_base_id == request.knowledge_base_id
    )
    async with open_read_session() as db:
        settings = await db.get(MemorySettings, request.owner_id)
        if settings is None or not settings.ad_personalization_enabled:
            return []
        return list(
            await db.scalars(
                select(CanonicalMemory)
                .where(
                    CanonicalMemory.owner_id == request.owner_id,
                    scope,
                    CanonicalMemory.status == "active",
                    CanonicalMemory.sensitivity == "low",
                    CanonicalMemory.memory_type == "preference",
                )
                .order_by(
                    CanonicalMemory.confidence.desc(),
                    CanonicalMemory.retrieval_weight.desc(),
                    CanonicalMemory.updated_at.desc(),
                )
                .limit(PROFILE_MEMORY_LIMIT)
            )
        )


def _score(profile: list[float], candidate: list[float], business_score: float) -> float:
    semantic = (sum(left * right for left, right in zip(profile, candidate, strict=True)) + 1.0) / 2.0
    return max(0.0, min(1.0, SEMANTIC_WEIGHT * semantic + (1.0 - SEMANTIC_WEIGHT) * business_score))


def _fallback(request: AdRecommendationRequest) -> AdRecommendationResponse:
    ranked: list[tuple[int, AdCandidate]] = sorted(
        enumerate(request.candidates),
        key=lambda item: (-item[1].business_score, item[0]),
    )
    return AdRecommendationResponse(
        request_id=request.request_id,
        personalized=False,
        items=[
            AdRecommendationItem(ad_id=candidate.ad_id, score=candidate.business_score)
            for _, candidate in ranked[: request.limit]
        ],
    )
