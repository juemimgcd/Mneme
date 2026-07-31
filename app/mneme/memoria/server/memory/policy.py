"""Decide whether a memory candidate is promoted, held for review, or rejected.

Secret sensitivity has absolute precedence; confidence, explicit intent, and conflicts govern other outcomes.
"""

from typing import Literal

from app.mneme.memoria.server.models.memory_candidate import Sensitivity

AUTO_PROMOTION_CONFIDENCE = 0.85
PolicyDecision = Literal["promote", "pending", "reject"]


def classify_candidate(
    *,
    sensitivity: Sensitivity,
    confidence: float,
    explicit_request: bool = False,
    has_conflict: bool = False,
) -> PolicyDecision:
    """Apply the persistence policy to a validated memory candidate.

    Secret candidates are always rejected. Explicit user intent can promote
    non-secret data; conflicts, sensitivity, and low confidence require review.
    """
    if sensitivity not in {"low", "sensitive", "secret"}:
        raise ValueError("unsupported sensitivity")
    if sensitivity == "secret":
        return "reject"
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between 0 and 1")
    if explicit_request:
        return "promote"
    if has_conflict or sensitivity == "sensitive" or confidence < AUTO_PROMOTION_CONFIDENCE:
        return "pending"
    return "promote"
