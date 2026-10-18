from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from jsonschema import Draft202012Validator

from app.api.deps import (
    get_authenticator,
    get_business_ownership,
    get_clock,
    get_collab_repository,
)
from app.domain.auth import AuthenticatedOwner, AuthenticationFailed
from app.infra.memory.business_ownership import InMemoryBusinessOwnership
from app.infra.memory.collab_request_repository import InMemoryCollabRequestRepository
from app.main import app
from tools.mock_server import SPEC

NOW = datetime(2026, 10, 8, 9, 0, tzinfo=UTC)
SENDER, RECEIVER = 1, 3  # business ids
ALICE, BOB = "owner-alice", "owner-bob"
HDR = {"Authorization": "Bearer tok"}
BASE = "/v1/collab-requests"
OPS = {
    "create": ("POST", BASE),
    "accept": ("POST", BASE + "/{id}/accept"),
    "reject": ("POST", BASE + "/{id}/reject"),
    "cancel": ("POST", BASE + "/{id}/cancel"),
}
# documented in the contract but impossible to produce: create has no business lookup (404)
UNPRODUCIBLE = {("create", "404")}


class FakeAuthenticator:
    def __init__(self, owner_id):
        self.owner_id = owner_id

    def authenticate(self, credentials):
        if credentials != "tok":
            raise AuthenticationFailed("bad")
        return AuthenticatedOwner(owner_id=self.owner_id, business_id=None)


class Api:
    def __init__(self):
        self.client = TestClient(app, raise_server_exceptions=False)
        self.statuses: set[tuple[str, str]] = set()
        self.as_owner(ALICE)

    def as_owner(self, owner_id):
        app.dependency_overrides[get_authenticator] = lambda: FakeAuthenticator(owner_id)
        return self

    def call(self, op, id=1, body=None, headers=HDR):
        path = OPS[op][1].replace("{id}", str(id))
        res = self.client.post(path, json=body, headers=headers)
        self.statuses.add((op, str(res.status_code)))
        return res

    def create(self, **over):
        body = {"sender_business_id": SENDER, "receiver_business_id": RECEIVER, "source": "profile"}
        res = self.call("create", body={**body, **over})
        assert res.status_code == 201, res.text
        return res.json()["data"]["id"]


_seen: set[tuple[str, str]] = set()


@pytest.fixture
def api():
    owned = InMemoryBusinessOwnership({ALICE: {SENDER}, BOB: {RECEIVER}})
    app.dependency_overrides[get_business_ownership] = lambda: owned
    app.dependency_overrides[get_clock] = lambda: lambda: NOW
    # one repository instance per test (a factory override would build one per request)
    repo = InMemoryCollabRequestRepository()
    app.dependency_overrides[get_collab_repository] = lambda: repo
    a = Api()
    yield a
    _seen.update(a.statuses)
    app.dependency_overrides.clear()


def validate_response(op, res):
    method, path = OPS[op]
    schema = SPEC["paths"][path][method.lower()]["responses"][str(res.status_code)]["content"][
        "application/json"
    ]["schema"]
    Draft202012Validator({**schema, "components": SPEC["components"]}).validate(res.json())


def assert_error(res, status, code):
    assert res.status_code == status
    err = res.json()["error"]
    assert err["code"] == code
    assert set(err) == {"code", "message", "details"}
    assert "owner" not in res.text.lower()


def test_create_success_matches_contract(api):
    res = api.call(
        "create",
        body={
            "sender_business_id": SENDER,
            "receiver_business_id": RECEIVER,
            "source": "ai_recommendation",
            "message": "hi",
            "collab_type": "joint_event",
            "desired_timing": "next month",
        },
    )
    assert res.status_code == 201
    validate_response("create", res)
    data = res.json()["data"]
    assert data["status"] == "pending" and data["source"] == "ai_recommendation"
    assert data["responded_at"] is None


def test_accept_success_matches_contract(api):
    rid = api.create()
    res = api.as_owner(BOB).call("accept", rid)
    assert res.status_code == 200
    validate_response("accept", res)
    assert res.json()["data"]["status"] == "accepted"
    assert res.json()["data"]["responded_at"] == "2026-10-08T09:00:00Z"


def test_reject_success_matches_contract(api):
    rid = api.create()
    res = api.as_owner(BOB).call("reject", rid)
    assert res.status_code == 200
    validate_response("reject", res)
    assert res.json()["data"]["status"] == "rejected"


def test_cancel_success_matches_contract(api):
    rid = api.create()
    res = api.call("cancel", rid)
    assert res.status_code == 200
    validate_response("cancel", res)
    assert res.json()["data"]["status"] == "cancelled"
    assert res.json()["data"]["responded_at"] is None


@pytest.mark.parametrize("op", OPS)
@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer bad"}, {"Authorization": "Basic tok"}]
)
def test_missing_or_invalid_authorization_is_401(api, op, headers):
    body = {"sender_business_id": SENDER, "receiver_business_id": RECEIVER, "source": "profile"}
    res = api.call(op, 1, body if op == "create" else None, headers)
    assert_error(res, 401, "AUTH_REQUIRED")


def test_create_by_non_owner_is_403(api):
    body = {"sender_business_id": SENDER, "receiver_business_id": RECEIVER, "source": "profile"}
    res = api.as_owner(BOB).call("create", body=body)
    assert_error(res, 403, "AUTH_FORBIDDEN")


@pytest.mark.parametrize(
    "op,actor",
    [("accept", ALICE), ("reject", ALICE), ("cancel", BOB)],  # wrong side each time
)
def test_respond_by_non_owner_is_403(api, op, actor):
    rid = api.create()
    assert_error(api.as_owner(actor).call(op, rid), 403, "AUTH_FORBIDDEN")


def test_duplicate_pending_in_both_directions_is_409(api):
    api.create()
    same = api.call(
        "create",
        body={"sender_business_id": SENDER, "receiver_business_id": RECEIVER, "source": "profile"},
    )
    assert_error(same, 409, "REQUEST_INVALID_STATE")
    reverse = api.as_owner(BOB).call(
        "create",
        body={"sender_business_id": RECEIVER, "receiver_business_id": SENDER, "source": "profile"},
    )
    assert_error(reverse, 409, "REQUEST_INVALID_STATE")


@pytest.mark.parametrize("op", ["accept", "reject"])
def test_respond_after_cancel_is_409(api, op):
    rid = api.create()
    assert api.call("cancel", rid).status_code == 200
    assert_error(api.as_owner(BOB).call(op, rid), 409, "REQUEST_INVALID_STATE")


def test_cancel_twice_is_409(api):
    rid = api.create()
    api.call("cancel", rid)
    assert_error(api.call("cancel", rid), 409, "REQUEST_INVALID_STATE")


@pytest.mark.parametrize("op", ["accept", "reject", "cancel"])
def test_unknown_id_is_404_before_ownership(api, op):
    assert_error(api.call(op, 999), 404, "NOT_FOUND")


@pytest.mark.parametrize(
    "over",
    [
        {"sender_business_id": "1"},
        {"receiver_business_id": "3"},
        {"sender_business_id": 0},
        {"source": "newsletter"},
        {"collab_type": "barbecue"},
        {"extra_field": 1},
    ],
)
def test_invalid_body_is_422(api, over):
    body = {"sender_business_id": SENDER, "receiver_business_id": RECEIVER, "source": "profile"}
    res = api.call("create", body={**body, **over})
    assert_error(res, 422, "REQUEST_VALIDATION_FAILED")
    assert res.json()["error"]["details"]


def test_missing_sender_is_422(api):
    res = api.call("create", body={"receiver_business_id": RECEIVER, "source": "profile"})
    assert_error(res, 422, "REQUEST_VALIDATION_FAILED")
    assert res.json()["error"]["details"][0]["field"] == "body.sender_business_id"


def test_domain_invalid_request_is_422(api):
    res = api.call(
        "create",
        body={"sender_business_id": SENDER, "receiver_business_id": SENDER, "source": "profile"},
    )
    assert_error(res, 422, "REQUEST_VALIDATION_FAILED")
    res = api.call(  # collab_post without post_id
        "create",
        body={
            "sender_business_id": SENDER,
            "receiver_business_id": RECEIVER,
            "source": "collab_post",
        },
    )
    assert_error(res, 422, "REQUEST_VALIDATION_FAILED")


def test_non_positive_path_id_is_422(api):
    assert_error(api.call("accept", 0), 422, "REQUEST_VALIDATION_FAILED")


def test_default_wiring_denies_create_without_leaking():
    # no dependency overrides except authentication
    app.dependency_overrides[get_authenticator] = lambda: FakeAuthenticator(ALICE)
    try:
        res = TestClient(app).post(
            BASE,
            json={"sender_business_id": 1, "receiver_business_id": 2, "source": "profile"},
            headers=HDR,
        )
    finally:
        app.dependency_overrides.clear()
    assert_error(res, 403, "AUTH_FORBIDDEN")
    assert ALICE not in res.text and "tok" not in res.text


def test_implemented_routes_exist_in_contract():
    implemented = {
        (m.upper(), path)
        for path, item in app.openapi()["paths"].items()
        if path.startswith(BASE)
        for m in item
    }
    assert implemented == set(OPS.values())
    for method, path in implemented:
        assert method.lower() in SPEC["paths"][path]


def test_every_documented_error_status_is_produced():
    # runs last in this module: _seen is filled by the tests above
    produced = set(_seen)
    for op, (method, path) in OPS.items():
        documented = {
            c for c in SPEC["paths"][path][method.lower()]["responses"] if not c.startswith("2")
        }
        missing = {c for c in documented if (op, c) not in produced} - {
            c for o, c in UNPRODUCIBLE if o == op
        }
        assert not missing, (op, missing)
