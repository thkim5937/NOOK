import json
from pathlib import Path

import jsonschema

DIR = Path(__file__).resolve().parent.parent / "data" / "samples"
DATA = json.loads((DIR / "businesses.sample.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((DIR / "business.schema.json").read_text(encoding="utf-8"))
BUSINESSES = DATA["businesses"]


def test_validates_against_schema():
    jsonschema.validate(DATA, SCHEMA)


def test_schema_enums_match_meta_options():
    props = SCHEMA["properties"]["businesses"]["items"]["properties"]
    opts = DATA["meta"]["provisional_options"]
    assert props["industry"]["enum"] == opts["industry"]
    for key in ("main_customers", "quiet_hours", "mood_tags"):
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
    ids = {n["id"] for n in DATA["neighborhoods"]}
    assert len(ids) >= 2
    assert all(b["neighborhood_id"] in ids for b in BUSINESSES)
    for nid in ids:
        assert sum(b["neighborhood_id"] == nid for b in BUSINESSES) >= 8


def test_at_least_5_industries():
    assert len({b["industry"] for b in BUSINESSES}) >= 5
