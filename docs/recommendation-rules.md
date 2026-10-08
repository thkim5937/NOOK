# Recommendation rules (DRAFT)

Rule-based baseline in `app/domain/recommendation.py`. Pure domain logic: not wired to any
endpoint yet and it does not change the API contract.

## Hard rules (never overridden)

1. The target shop itself is never recommended.
2. A candidate in the **same industry** as the target is never recommended (legal rule:
   same-industry matching is avoided for fair-trade law reasons).
3. Candidates whose id is in `exclude_ids` are skipped.

## Scoring

```
base  = 0.35 * jaccard(main_customers)
      + 0.25 * jaccard(mood_tags)
      + 0.25 * jaccard(quiet_hours)
score = base + 0.15   if candidate id is in open_post_ids, else base
```

- `jaccard(a, b) = |a ∩ b| / |a ∪ b|`, and 0.0 when both sets are empty.
- Candidates with `base == 0` (no overlap at all) are dropped. The recruiting bonus is applied
  only afterwards, so it can never rescue them.
- Sort by score descending, then business id ascending (deterministic); return at most `limit`
  (default 5). `limit < 1` raises `ValueError`.

## Reason codes

Reasons are listed in this fixed order. Every returned recommendation has at least one.

| Code | Added when | UI wording |
|------|------------|------------|
| `customer_overlap` | `main_customers` intersect | Customers overlap |
| `mood_similar` | `mood_tags` intersect | Mood is similar |
| `quiet_hours_overlap` | `quiet_hours` intersect | Quiet hours overlap |
| `open_to_collab` | candidate id is in `open_post_ids` | Currently recruiting collaborators |

"Different industry" was deliberately removed as a reason: the hard rule makes it true for
every result, so it carries no information.

## Provisional and assumed

Provisional (product decisions, may change):
- Option values (industry, customers, quiet hours, mood). The code only compares sets and never
  depends on specific values; the catalog is fixed later by the data teammate.
- The weights 0.35 / 0.25 / 0.25 and the 0.15 bonus.
- Using quiet hours rather than opening hours (`_quiet_hours_overlap` is isolated to be swapped).

Assumed:
- `open_post_ids` is computed by the caller. The definition of "recruiting" is not verified
  against the database.

## Open questions

- Quiet hours vs opening hours for the time-overlap signal.
- Should zero-overlap candidates ever be shown (e.g. to fill up to the limit)?
- How strongly should recruiting shops be boosted?

## Planned signals (direction only, not implemented)

| # | Signal | Prerequisite | Status |
|---|--------|--------------|--------|
| 1 | Distance between shops | Shop latitude/longitude, which the database does not have yet | not started |
| 2 | Matching collaboration type preferences | A per-shop preferred collaboration type field, which does not exist yet | not started |
| 3 | Semantic similarity of shop introductions and natural-language reason sentences | The LLM stage, with an API key and a cost cap | not started |
| 4 | Nearby local events | The `external_events` collection (who runs it is undecided) | not started |
| 5 | Photo analysis tags | First item in the scope-cut order | not started |
| 6 | Responsive-shop signal | Accumulated collaboration request history; a hidden ranking signal only, never shown to other owners | not started |

## Considered but not adopted

- A customer-complement reason: the UI uses overlap.
- Marketing data as a displayed reason: it may only be used as AI input and never shown to
  other owners.
- Price level and opening date.

## Sample dataset results

Generated once by running `recommend` on `data/samples/businesses.sample.json` with an empty
`open_post_ids` and the default limit (5). Each shop is the target, all 22 shops are candidates.

| id | Shop | Industry | Recommendations |
|----|------|----------|-----------------|
| 1 | 달빛다방 | cafe | 5 |
| 2 | 오후세시 커피 | cafe | 5 |
| 3 | 밀밭제빵소 | bakery | 5 |
| 4 | 버터와 소금 | bakery | 5 |
| 5 | 나물한상 | restaurant | 5 |
| 6 | 느린책방 | bookstore | 5 |
| 7 | 꽃잎상점 | flower_shop | 5 |
| 8 | 빈칸갤러리 | gallery | 5 |
| 9 | 다락방 옷가게 | vintage_shop | 5 |
| 10 | 골목 끝 술집 | bar | 5 |
| 11 | 숨쉬는 필라테스 | fitness_studio | 5 |
| 12 | 햇살머금은 카페 | cafe | 5 |
| 13 | 소란스런 다락 | cafe | 5 |
| 14 | 참나무 빵공방 | bakery | 5 |
| 15 | 여우골 식당 | restaurant | 5 |
| 16 | 엄마손 밥상 | restaurant | 5 |
| 17 | 한뼘서재 | bookstore | 5 |
| 18 | 초록손 화원 | flower_shop | 5 |
| 19 | 물결 아틀리에 | gallery | 5 |
| 20 | 흙내음 공방 | pottery_workshop | 5 |
| 21 | 낡은 서랍 | vintage_shop | 5 |
| 22 | 별헤는 밤 바 | bar | 5 |

All 22 shops get 5 results; none get fewer.
