"""Business profile as seen by the domain. Pure logic: no web or database imports."""

from dataclasses import dataclass


# PROVISIONAL: option values are plain strings until the data teammate fixes the DB catalog.
@dataclass(frozen=True)
class Business:
    id: int
    name: str
    industry: str
    main_customers: frozenset[str]
    quiet_hours: frozenset[str]
    mood_tags: frozenset[str]
