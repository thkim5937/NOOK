from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import current_owner, get_authenticator
from app.core.errors import register_exception_handlers
from app.domain.auth import AuthenticatedOwner, AuthenticationFailed


class FakeAuthenticator:
    def __init__(self, token: str, owner_id: str):
        self.token, self.owner_id = token, owner_id

    def authenticate(self, credentials: str | None) -> AuthenticatedOwner:
        if credentials != self.token:
            raise AuthenticationFailed("bad token")
        return AuthenticatedOwner(owner_id=self.owner_id, business_id=None)


def make_app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/protected")
    def protected(owner: Annotated[AuthenticatedOwner, Depends(current_owner)]):
        return {"owner_id": owner.owner_id}

    return app


def assert_auth_required(res):
    assert res.status_code == 401
    err = res.json()["error"]
    assert err["code"] == "AUTH_REQUIRED"
    assert set(err) == {"code", "message", "details"}


def test_default_denies_without_header():
    assert_auth_required(TestClient(make_app()).get("/protected"))


def test_malformed_header_is_401():
    client = TestClient(make_app())
    for value in ("Bearer", "Bearer ", "Basic abc", "abc"):
        assert_auth_required(client.get("/protected", headers={"Authorization": value}))


def test_malformed_header_is_401_even_with_real_authenticator():
    app = make_app()
    app.dependency_overrides[get_authenticator] = lambda: FakeAuthenticator("t", "o1")
    assert_auth_required(TestClient(app).get("/protected", headers={"Authorization": "Basic t"}))


def test_fake_authenticator_grants_access():
    app = make_app()
    app.dependency_overrides[get_authenticator] = lambda: FakeAuthenticator("tok-1", "owner-1")
    client = TestClient(app)
    res = client.get("/protected", headers={"Authorization": "Bearer tok-1"})
    assert res.status_code == 200
    assert res.json() == {"owner_id": "owner-1"}
    assert_auth_required(client.get("/protected", headers={"Authorization": "Bearer nope"}))


def test_swapping_authenticator_needs_no_route_change():
    app = make_app()  # same route code as above
    app.dependency_overrides[get_authenticator] = lambda: FakeAuthenticator("other", "owner-2")
    res = TestClient(app).get("/protected", headers={"Authorization": "Bearer other"})
    assert res.json() == {"owner_id": "owner-2"}
