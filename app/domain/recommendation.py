"""Rule-based collaboration recommendations. Pure logic: no web or database imports."""

from collections.abc import Collection, Iterable
from dataclasses import dataclass
from enum import StrEnum

from app.domain.business import Business

# PROVISIONAL product decisions: the weights below are not final.
WEIGHT_CUSTOMERS = 0.35
WEIGHT_MOOD = 0.25
WEIGHT_QUIET_HOURS = 0.25
BONUS_OPEN_TO_COLLAB = 0.15


class ReasonCode(StrEnum):
    # No "different industry" reason: same-industry candidates are always excluded,
    # so it would always be true.
    CUSTOMER_OVERLAP = "customer_overlap"
    MOOD_SIMILAR = "mood_similar"
    QUIET_HOURS_OVERLAP = "quiet_hours_overlap"
    OPEN_TO_COLLAB = "open_to_collab"


@dataclass(frozen=True)
class Recommendation:
    business_id: int
    score: float
    reasons: tuple[ReasonCode, ...]


def _overlap(a: frozenset[str], b: frozenset[str]) -> float:
    """Jaccard similarity; 0.0 when both sets are empty."""
    union = a | b
    return len(a & b) / len(union) if union else 0.0


def _quiet_hours_overlap(target: Business, candidate: Business) -> float:
    # Open product question: compare quiet hours or opening hours? Swap only this helper.
    return _overlap(target.quiet_hours, candidate.quiet_hours)


def recommend(
    target: Business,
    candidates: Iterable[Business],
    *,
    limit: int = 5,
    exclude_ids: Collection[int] = (),
    open_post_ids: Collection[int] = (),
) -> list[Recommendation]:
    if limit < 1:
        raise ValueError("limit must be >= 1")
    results: list[Recommendation] = []
    for c in candidates:
        # Hard rules, never overridden. Same-industry matching is avoided for
        # fair-trade law reasons.
        if c.id == target.id or c.industry == target.industry or c.id in exclude_ids:
            continue
        base = (
            WEIGHT_CUSTOMERS * _overlap(target.main_customers, c.main_customers)
            + WEIGHT_MOOD * _overlap(target.mood_tags, c.mood_tags)
            + WEIGHT_QUIET_HOURS * _quiet_hours_overlap(target, c)
        )
        if base == 0:  # the open-to-collab bonus must not rescue a zero-overlap candidate
            continue
        is_open = c.id in open_post_ids
        reasons = tuple(
            code
            for code, hit in (
                (ReasonCode.CUSTOMER_OVERLAP, target.main_customers & c.main_customers),
                (ReasonCode.MOOD_SIMILAR, target.mood_tags & c.mood_tags),
                (ReasonCode.QUIET_HOURS_OVERLAP, target.quiet_hours & c.quiet_hours),
                (ReasonCode.OPEN_TO_COLLAB, is_open),
            )
            if hit
        )
        score = base + (BONUS_OPEN_TO_COLLAB if is_open else 0.0)
        results.append(Recommendation(c.id, score, reasons))
    results.sort(key=lambda r: (-r.score, r.business_id))
    return results[:limit]
