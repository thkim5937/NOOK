import json
import re
from pathlib import Path

import jsonschema

from app.domain.catalog import MOOD_TAGS, SLOW_TIMES, TARGET_CUSTOMERS, unknown_values

DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
DATA = json.loads((DIR / "businesses.sample.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((DIR / "business.schema.json").read_text(encoding="utf-8"))
BUSINESSES = DATA["businesses"]


def test_validates_against_schema():
    jsonschema.validate(DATA, SCHEMA)


def test_schema_enums_match_meta_options():
    props = SCHEMA["properties"]["businesses"]["items"]["properties"]
    opts = DATA["meta"]["provisional_options"]
    assert props["category"]["enum"] == opts["category"]
    for key in ("target_customers", "slow_times", "mood_tags"):
        assert props[key]["items"]["enum"] == opts[key]


def test_at_least_20_businesses():
    assert len(BUSINESSES) >= 20


def test_ids_unique():
    ids = [b["id"] for b in BUSINESSES]
    assert len(ids) == len(set(ids))


def test_ids_are_positive_integers():
    assert len(BUSINESSES) == 22
    for b in BUSINESSES:
        assert isinstance(b["id"], int) and not isinstance(b["id"], bool)
        assert b["id"] >= 1


def test_neighborhoods():
    districts = {b["district"] for b in BUSINESSES}
    assert len(districts) >= 2
    for district in districts:
        assert sum(b["district"] == district for b in BUSINESSES) >= 8


def test_at_least_5_industries():
    assert len({b["category"] for b in BUSINESSES}) >= 5


def test_array_values_are_in_catalog():
    for key, allowed in (
        ("target_customers", TARGET_CUSTOMERS),
        ("slow_times", SLOW_TIMES),
        ("mood_tags", MOOD_TAGS),
    ):
        for b in BUSINESSES:
            assert unknown_values(allowed, b[key]) == [], (b["id"], key)


def test_category_and_district_fit_database_columns():
    for b in BUSINESSES:
        assert re.fullmatch(r"[a-z][a-z0-9_]*", b["category"])
        assert len(b["category"]) <= 50
        assert len(b["district"]) <= 50
