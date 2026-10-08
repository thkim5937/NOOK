import json
from pathlib import Path

import pytest

from app.domain.business import Business
from app.domain.recommendation import (
    BONUS_OPEN_TO_COLLAB,
    WEIGHT_CUSTOMERS,
    WEIGHT_MOOD,
    WEIGHT_QUIET_HOURS,
    ReasonCode,
    recommend,
)

R = ReasonCode
SAMPLE = Path(__file__).parents[2] / "data" / "samples" / "businesses.sample.json"


def biz(id, industry="b", customers=(), quiet=(), mood=()):
    return Business(
        id=id,
        name=f"shop{id}",
        industry=industry,
        main_customers=frozenset(customers),
        quiet_hours=frozenset(quiet),
        mood_tags=frozenset(mood),
    )


TARGET = biz(1, industry="a", customers="xy", quiet=["q1"], mood=["m1"])

FULL = biz(2, customers="xy", quiet=["q1"], mood=["m1"])  # 0.35 + 0.25 + 0.25
HALF_CUSTOMERS_3 = biz(3, "c", customers="x")  # 0.35 * 0.5
HALF_CUSTOMERS_4 = biz(4, "c", customers="x")  # tie with 3
MOOD_ONLY = biz(5, mood=["m1"])  # 0.25
QUIET_ONLY = biz(6, quiet=["q1"])  # 0.25
NO_OVERLAP = biz(7, customers="z", quiet=["q2"], mood=["m2"])
SAME_INDUSTRY = biz(8, "a", customers="xy", quiet=["q1"], mood=["m1"])
ALL = [FULL, HALF_CUSTOMERS_3, HALF_CUSTOMERS_4, MOOD_ONLY, QUIET_ONLY, NO_OVERLAP, SAME_INDUSTRY]


def test_ranking_scores_and_tie_by_id():
    recs = recommend(TARGET, ALL, limit=10)
    assert [r.business_id for r in recs] == [2, 5, 6, 3, 4]
    assert [r.score for r in recs] == pytest.approx([0.85, 0.25, 0.25, 0.175, 0.175])
    assert 0.85 == pytest.approx(WEIGHT_CUSTOMERS + WEIGHT_MOOD + WEIGHT_QUIET_HOURS)


def test_input_order_does_not_matter():
    assert recommend(TARGET, ALL, limit=10) == recommend(TARGET, reversed(ALL), limit=10)


def test_limit():
    assert [r.business_id for r in recommend(TARGET, ALL, limit=2)] == [2, 5]
    assert [r.business_id for r in recommend(TARGET, ALL)] == [2, 5, 6, 3, 4]  # default 5


@pytest.mark.parametrize("limit", [0, -1])
def test_limit_below_one_raises(limit):
    with pytest.raises(ValueError):
        recommend(TARGET, ALL, limit=limit)


def test_empty_candidates():
    assert recommend(TARGET, []) == []


def test_exclude_ids():
    recs = recommend(TARGET, ALL, limit=10, exclude_ids={2, 5})
    assert [r.business_id for r in recs] == [6, 3, 4]


def test_zero_score_dropped():
    assert recommend(TARGET, [NO_OVERLAP]) == []


def test_reasons_and_fixed_order():
    by_id = {r.business_id: r.reasons for r in recommend(TARGET, ALL, limit=10)}
    assert by_id[2] == (R.CUSTOMER_OVERLAP, R.MOOD_SIMILAR, R.QUIET_HOURS_OVERLAP)
    assert by_id[3] == (R.CUSTOMER_OVERLAP,)
    assert by_id[5] == (R.MOOD_SIMILAR,)
    assert by_id[6] == (R.QUIET_HOURS_OVERLAP,)
    two = biz(9, customers="x", quiet=["q1"])
    assert recommend(TARGET, [two])[0].reasons == (R.CUSTOMER_OVERLAP, R.QUIET_HOURS_OVERLAP)
    two = biz(9, customers="x", mood=["m1"])
    assert recommend(TARGET, [two])[0].reasons == (R.CUSTOMER_OVERLAP, R.MOOD_SIMILAR)


def test_every_recommendation_has_a_reason():
    assert all(r.reasons for r in recommend(TARGET, ALL, limit=10, open_post_ids={3, 7}))


def test_open_to_collab_bonus_changes_ranking_and_adds_reason():
    recs = recommend(TARGET, ALL, limit=10, open_post_ids={3})
    assert [r.business_id for r in recs] == [2, 3, 5, 6, 4]
    third = recs[1]
    assert third.score == pytest.approx(0.175 + BONUS_OPEN_TO_COLLAB)
    assert third.reasons == (R.CUSTOMER_OVERLAP, R.OPEN_TO_COLLAB)


def test_open_to_collab_cannot_rescue_zero_overlap():
    assert recommend(TARGET, [NO_OVERLAP], open_post_ids={7}) == []


def test_same_industry_never_appears_even_if_best():
    recs = recommend(TARGET, ALL, limit=10, open_post_ids={8})
    assert 8 not in [r.business_id for r in recs]


def test_target_itself_never_appears():
    twin = biz(1, "b", customers="xy", quiet=["q1"], mood=["m1"])  # same id, other industry
    assert recommend(TARGET, [twin, FULL]) == recommend(TARGET, [FULL])
    assert recommend(TARGET, [TARGET]) == []


def _load_sample():
    shops = json.loads(SAMPLE.read_text(encoding="utf-8"))["businesses"]
    return [
        Business(
            id=s["id"],
            name=s["name"],
            industry=s["industry"],
            main_customers=frozenset(s["main_customers"]),
            quiet_hours=frozenset(s["quiet_hours"]),
            mood_tags=frozenset(s["mood_tags"]),
        )
        for s in shops
    ]


def test_sample_dataset_all_targets():
    shops = _load_sample()
    assert len(shops) == 22
    industry = {s.id: s.industry for s in shops}
    for target in shops:
        recs = recommend(target, shops)
        assert len(recs) <= 5
        ids = [r.business_id for r in recs]
        assert target.id not in ids
        assert all(industry[i] != target.industry for i in ids)
        assert recs == sorted(recs, key=lambda r: (-r.score, r.business_id))
        assert all(r.reasons for r in recs)
        assert recs == recommend(target, shops)
