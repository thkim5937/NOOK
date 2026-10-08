import dataclasses
import re
from pathlib import Path

import yaml
from openapi_spec_validator import validate

from app.core.errors import ErrorCode
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
