"""Expose scoped memory-personalized ad reranking."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.mneme.memoria.server.api.dependencies import require_claimed_scope, require_service_scope
from app.mneme.memoria.server.contracts.recommendations import AdRecommendationRequest, AdRecommendationResponse
from app.mneme.memoria.server.security.service_tokens import AD_RECOMMENDATIONS_SCOPE
from app.mneme.memoria.server.services.ad_recommendations import recommend_ads

router = APIRouter()


@router.post("/ad-recommendations", response_model=AdRecommendationResponse)
async def create_ad_recommendation(
    request: AdRecommendationRequest,
    claims: Annotated[dict[str, Any], Depends(require_service_scope(AD_RECOMMENDATIONS_SCOPE))],
) -> AdRecommendationResponse:
    require_claimed_scope(
        claims,
        owner_id=request.owner_id,
        knowledge_base_id=request.knowledge_base_id,
    )
    return await recommend_ads(request)
