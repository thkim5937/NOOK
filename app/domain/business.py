"""Business profile as seen by the domain. Pure logic: no web or database imports."""

from dataclasses import dataclass


# Field names follow the business_profiles columns. Option values: app/domain/catalog.py
# (not validated here; the database does not enforce them).
@dataclass(frozen=True)
class Business:
    id: int
    business_name: str
    category: str
    target_customers: frozenset[str]
    slow_times: frozenset[str]
    mood_tags: frozenset[str]
