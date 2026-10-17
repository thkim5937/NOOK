import re

import pytest

from app.domain.catalog import MOOD_TAGS, SLOW_TIMES, TARGET_CUSTOMERS, unknown_values


@pytest.mark.parametrize(
    ("values", "count"), [(TARGET_CUSTOMERS, 9), (SLOW_TIMES, 6), (MOOD_TAGS, 9)]
)
def test_counts_unique_and_format(values, count):
    assert len(values) == count
    assert len(set(values)) == count
    assert all(re.fullmatch(r"[a-z0-9_]+", v) for v in values)


def test_unknown_values():
    assert unknown_values(MOOD_TAGS, ["quiet", "zzz", "aaa", "zzz"]) == ["aaa", "zzz"]
    assert unknown_values(MOOD_TAGS, []) == []
    assert unknown_values(MOOD_TAGS, MOOD_TAGS) == []
    assert unknown_values((), ["x"]) == ["x"]
