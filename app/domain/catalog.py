"""Canonical option values (database handoff v1, section 5). The database does not enforce them."""

from collections.abc import Collection, Iterable

TARGET_CUSTOMERS = (
    "teens",
    "20s",
    "30s",
    "40s_plus",
    "students",
    "office_workers",
    "couples",
    "families",
    "tourists",
)
SLOW_TIMES = (
    "weekday_morning",
    "weekday_afternoon",
    "weekday_evening",
    "weekend_morning",
    "weekend_afternoon",
    "weekend_evening",
)
MOOD_TAGS = (
    "quiet",
    "warm",
    "cozy",
    "minimal",
    "trendy",
    "lively",
    "premium",
    "casual",
    "artistic",
)


def unknown_values(allowed: Collection[str], values: Iterable[str]) -> list[str]:
    """Sorted values that are not in allowed (duplicates reported once)."""
    return sorted(set(values) - set(allowed))
