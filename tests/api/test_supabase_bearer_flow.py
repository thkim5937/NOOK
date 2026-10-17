import time
from typing import Annotated

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.api.deps import current_owner, get_authenticator
from app.core.errors import register_exception_handlers
from app.domain.auth import AuthenticatedOwner, TokenError
from app.infra.auth.supabase_authenticator import SupabaseAuthenticator
from app.infra.auth.supabase_jwt import SupabaseJwtVerifier

ISSUER = "https://example.test/auth/v1"
AUDIENCE = "authenticated"
KID = "test-kid"
USER_ID = "11111111-2222-4333-8444-555555555555"


class FakeKeyProvider:
    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key(self, token):
        if jwt.get_unverified_header(token).get("kid") != KID:
            raise TokenError("unknown kid")
        return self.public_key


@pytest.fixture(scope="module")
def private_key():
    return ec.generate_private_key(ec.SECP256R1())


@pytest.fixture
def client(private_key):
    app = FastAPI()
    register_exception_handlers(app)

    @app.get("/protected")  # test-only route
    def protected(owner: Annotated[AuthenticatedOwner, Depends(current_owner)]):
        return {"owner_id": owner.owner_id, "business_id": owner.business_id}

    verifier = SupabaseJwtVerifier(ISSUER, AUDIENCE, FakeKeyProvider(private_key.public_key()))
    app.dependency_overrides[get_authenticator] = lambda: SupabaseAuthenticator(verifier)
    return TestClient(app)


def make_token(key, **overrides):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": USER_ID,
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    claims.update(overrides)
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": KID})


def assert_auth_required(res):
    assert res.status_code == 401
    assert res.json()["error"]["code"] == "AUTH_REQUIRED"


def test_missing_header(client):
    assert_auth_required(client.get("/protected"))


@pytest.mark.parametrize("value", ["Bearer", "Bearer ", "Basic xyz", "xyz"])
def test_malformed_header(client, value):
    assert_auth_required(client.get("/protected", headers={"Authorization": value}))


def test_invalid_token(client, private_key):
    other = ec.generate_private_key(ec.SECP256R1())
    for token in ("not-a-jwt", make_token(other), make_token(private_key, exp=1)):
        assert_auth_required(client.get("/protected", headers={"Authorization": f"Bearer {token}"}))


@pytest.mark.parametrize("scheme", ["Bearer", "bearer"])
def test_valid_token(client, private_key, scheme):
    res = client.get("/protected", headers={"Authorization": f"{scheme} {make_token(private_key)}"})
    assert res.status_code == 200
    assert res.json() == {"owner_id": USER_ID, "business_id": None}
