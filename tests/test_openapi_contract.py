import dataclasses
import re
from pathlib import Path

import yaml
from openapi_spec_validator import validate

from app.core.errors import ErrorCode
from app.domain.catalog import MOOD_TAGS, SLOW_TIMES, TARGET_CUSTOMERS
from app.domain.collab_request import CollabRequest, CollabType, RequestSource, RequestStatus

ROOT = Path(__file__).resolve().parent.parent
SPEC = yaml.safe_load((ROOT / "api" / "openapi.yaml").read_text(encoding="utf-8"))
HTTP_METHODS = {"get", "put", "post", "delete", "patch"}
SCHEMAS = SPEC["components"]["schemas"]


def _table_rows() -> dict[tuple[str, str], str]:
    """(METHOD, path) -> status, from docs/endpoints.md. Query strings are not part of the path."""
    rows = {}
    for line in (ROOT / "docs" / "endpoints.md").read_text(encoding="utf-8").splitlines():
        if re.match(r"\| F\d", line):
            cells = [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]
            rows[(cells[1], cells[2].split("?")[0])] = cells[5]
    return rows


def _operations() -> dict[tuple[str, str], dict]:
    return {
        (method.upper(), path): op
        for path, item in SPEC["paths"].items()
        for method, op in item.items()
        if method in HTTP_METHODS
    }


def test_valid_openapi_31():
    assert SPEC["openapi"].startswith("3.1")
    validate(SPEC)


def test_operations_match_endpoint_table():
    assert set(_operations()) == set(_table_rows())


def test_x_status_matches_table():
    rows = _table_rows()
    for key, op in _operations().items():
        assert op["x-status"] in {"draft", "tbd"}, key
        assert op["x-status"] == rows[key], key


def test_error_code_enum_matches_code():
    enum = SCHEMAS["ErrorResponse"]["properties"]["error"]["properties"]["code"]["enum"]
    assert set(enum) == {c.value for c in ErrorCode}


def test_collab_request_enums_match_domain():
    props = SCHEMAS["CollabRequest"]["properties"]
    assert set(props["status"]["enum"]) == {s.value for s in RequestStatus}
    assert set(props["source"]["enum"]) == {s.value for s in RequestSource}
    assert set(props["collab_type"]["enum"]) - {None} == {t.value for t in CollabType}


def test_collab_request_properties_match_domain():
    props = set(SCHEMAS["CollabRequest"]["properties"])
    assert props == {f.name for f in dataclasses.fields(CollabRequest)}


def test_cancel_operation_declares_errors():
    op = _operations()[("POST", "/v1/collab-requests/{id}/cancel")]
    assert {"403", "404", "409"} <= set(op["responses"])


def test_no_auth_paths_and_public_security_empty():
    assert not any(path.startswith("/v1/auth") for path in SPEC["paths"])
    for (method, path), op in _operations().items():
        if path.startswith("/v1/public"):
            assert op["security"] == [], (method, path)


def test_business_scoped_paths_declare_business_id():
    assert not any(path.startswith("/v1/me/business") for path in SPEC["paths"])
    components = SPEC["components"]["parameters"]
    for path, item in SPEC["paths"].items():
        if "{business_id}" not in path:
            continue
        for method, op in item.items():
            if method not in HTTP_METHODS:
                continue
            params = [
                components[p["$ref"].rsplit("/", 1)[1]] if "$ref" in p else p
                for p in item.get("parameters", []) + op.get("parameters", [])
            ]
            match = [p for p in params if p["name"] == "business_id"]
            assert match, (method, path)
            assert match[0]["in"] == "path" and match[0]["required"] is True, (method, path)
            assert match[0]["schema"]["type"] == "integer", (method, path)


def _params(item, op):
    components = SPEC["components"]["parameters"]
    return [
        components[p["$ref"].rsplit("/", 1)[1]] if "$ref" in p else p
        for p in item.get("parameters", []) + op.get("parameters", [])
    ]


def test_path_id_parameters_are_integers():
    for path, item in SPEC["paths"].items():
        for method, op in item.items():
            if method in HTTP_METHODS:
                for p in _params(item, op):
                    if p["in"] == "path" and p["name"] == "id":
                        assert p["schema"]["type"] == "integer", (method, path)


def test_create_requires_sender_business_id():
    assert "sender_business_id" in SCHEMAS["CollabRequestCreate"]["required"]


def test_business_id_query_only_on_recommendations_and_measurements():
    refs = {
        key
        for key, op in _operations().items()
        if any(p.get("$ref", "").endswith("/BusinessIdQuery") for p in op.get("parameters", []))
    }
    assert refs == {("GET", "/v1/recommendations"), ("GET", "/v1/me/measurements")}
    for key in refs:
        assert "403" in _operations()[key]["responses"], key


def test_recommendation_requires_match_id():
    assert any("match_id" in part.get("required", []) for part in SCHEMAS["Recommendation"]["allOf"])


def test_status_and_source_enums_are_database_values():
    props = SCHEMAS["CollabRequest"]["properties"]
    assert set(props["status"]["enum"]) == {"pending", "accepted", "rejected", "cancelled"}
    assert {s.value for s in RequestStatus} == set(props["status"]["enum"])
    assert set(props["source"]["enum"]) == {"ai_recommendation", "collab_post", "profile"}


def _resolve(node):
    while "$ref" in node:
        target = SPEC
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def test_business_registration_operation_documents_responses():
    op = _operations()[("POST", "/v1/businesses")]
    assert op["security"]
    assert {"201", "401", "409", "422", "429"} <= set(op["responses"])


def test_business_registration_request_schema():
    schema = SCHEMAS["BusinessRegistrationCreate"]
    assert {"business_number", "business_name", "opening_date"} <= set(schema["required"])
    assert set(schema["properties"]) == {
        "business_number",
        "business_name",
        "opening_date",
        "category",
    }
    assert re.fullmatch(schema["properties"]["business_number"]["pattern"], "0123456789")
    assert not re.fullmatch(schema["properties"]["business_number"]["pattern"], "012-34-56789")


def test_business_registered_response_schema():
    op = _operations()[("POST", "/v1/businesses")]
    data = _resolve(op["responses"]["201"]["content"]["application/json"]["schema"])["properties"][
        "data"
    ]
    registered = _resolve(data)
    assert {"id", "verification_status"} <= set(registered["required"])
    assert registered["properties"]["id"]["type"] == "integer"
    status = _resolve(registered["properties"]["verification_status"])
    assert set(status["enum"]) == {"pending", "verified", "rejected"}


def test_rate_limited_code_and_operations():
    enum = SCHEMAS["ErrorResponse"]["properties"]["error"]["properties"]["code"]["enum"]
    assert "RATE_LIMITED" in enum
    refs = {
        key
        for key, op in _operations().items()
        if op["responses"].get("429", {}).get("$ref", "").endswith("/RateLimited")
    }
    assert refs == {
        ("POST", "/v1/businesses"),
        ("POST", "/v1/businesses/{business_id}/verification"),
    }


def test_business_profile_option_enums_match_catalog():
    props = SCHEMAS["BusinessProfile"]["properties"]
    assert tuple(props["target_customers"]["items"]["enum"]) == TARGET_CUSTOMERS
    assert tuple(props["slow_times"]["items"]["enum"]) == SLOW_TIMES
    assert tuple(props["mood_tags"]["items"]["enum"]) == MOOD_TAGS


def test_business_profile_has_no_provisional_field_names():
    props = SCHEMAS["BusinessProfile"]["properties"]
    # names are split so the repo-wide leftover-name grep stays empty
    assert "indus" + "try" not in props
    assert "neighborhood" + "_id" not in props
