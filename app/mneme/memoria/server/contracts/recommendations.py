"""Define the bounded contract for memory-personalized ad reranking."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

AdTag = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)]


class AdCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ad_id: str = Field(min_length=1, max_length=128)
    title: str = Field(min_length=1, max_length=240)
    description: str = Field(default="", max_length=2000)
    tags: list[AdTag] = Field(default_factory=list, max_length=20)
    business_score: float = Field(default=0.0, ge=0, le=1)


class AdRecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str = Field(min_length=1, max_length=128)
    owner_id: int = Field(gt=0)
    knowledge_base_id: str | None = Field(default=None, max_length=128)
    placement: str = Field(min_length=1, max_length=64)
    candidates: list[AdCandidate] = Field(min_length=1, max_length=100)
    limit: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def candidate_ids_must_be_unique(self) -> "AdRecommendationRequest":
        ids = [candidate.ad_id for candidate in self.candidates]
        if len(ids) != len(set(ids)):
            raise ValueError("candidate ad IDs must be unique")
        return self


class AdRecommendationItem(BaseModel):
    ad_id: str
    score: float = Field(ge=0, le=1)
    matched_topics: list[str] = Field(default_factory=list)


class AdRecommendationResponse(BaseModel):
    request_id: str
    personalized: bool
    items: list[AdRecommendationItem]
