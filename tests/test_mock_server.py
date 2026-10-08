import pytest
import yaml
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from tools.mock_server import METHODS, SPEC, SPEC_PATH, app, resolve

client = TestClient(app)
AUTH = {"Authorization": "Bearer test"}
OPS = [
    (method, path, op)
    for path, item in SPEC["paths"].items()
    for method, op in item.items()
    if method in METHODS
]


def validate(schema, instance):
    Draft202012Validator({**schema, "components": SPEC["components"]}).validate(instance)


def url(path):
    return path.replace("{id}", "req_001").replace("{business_id}", "1").replace("{code}", "C-1")


def request_body(op):
    media = resolve(op.get("requestBody", {})).get("content", {}).get("application/json")
    return media.get("example") if media else None


def query(op):
    return {
        p["name"]: resolve(p)["schema"].get("enum", ["1"])[0]
        for p in map(resolve, op.get("parameters", []))
        if p["in"] == "query" and p.get("required")
    }


def call(method, path, op, headers):
    return client.request(
        method.upper(), url(path), headers=headers, json=request_body(op), params=query(op)
    )


def find(operation_id):
    return next((m, p, o) for m, p, o in OPS if o["operationId"] == operation_id)


def test_spec_path_is_repo_relative():
    assert yaml.safe_load(SPEC_PATH.read_text(encoding="utf-8")) == SPEC


@pytest.mark.parametrize("method,path,op", OPS, ids=[o["operationId"] for _, _, o in OPS])
def test_every_operation_returns_documented_success(method, path, op):
    protected = bool(op.get("security"))
    res = call(method, path, op, AUTH if protected else {})
    success = next(c for c in sorted(op["responses"]) if c.startswith("2"))
    assert res.status_code == int(success)
    media = resolve(op["responses"][success]).get("content", {}).get("application/json")
    if media:
        assert "data" in res.json()
        validate(media["schema"], res.json())


@pytest.mark.parametrize(
    "method,path,op",
    [t for t in OPS if t[2].get("security")],
    ids=[o["operationId"] for _, _, o in OPS if o.get("security")],
)
def test_protected_operation_requires_bearer(method, path, op):
    res = call(method, path, op, {})
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"


def test_open_coupon_scan_works_without_auth():
    method, path, op = find("post_v1_public_coupons_code_scan")
    assert call(method, path, op, {}).status_code == 200


def test_mock_status_returns_documented_failure():
    method, path, op = find("post_v1_collab_requests_id_cancel")
    res = call(method, path, op, {**AUTH, "X-Mock-Status": "409"})
    assert res.status_code == 409
    assert res.json()["error"]["code"] == "REQUEST_INVALID_STATE"


def test_mock_status_undocumented_is_422():
    method, path, op = find("post_v1_collab_requests_id_cancel")
    res = call(method, path, op, {**AUTH, "X-Mock-Status": "418"})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert "409" in res.json()["error"]["message"]


def test_invalid_body_is_422():
    res = client.post("/v1/collab-requests", headers=AUTH, json={"message": 5})
    assert res.status_code == 422
    body = res.json()
    assert body["error"]["code"] == "REQUEST_VALIDATION_FAILED"
    assert body["error"]["details"]
