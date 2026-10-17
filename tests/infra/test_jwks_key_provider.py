import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app.domain.auth import TokenError
from app.infra.auth.supabase_jwt import JwksKeyProvider, SupabaseJwtVerifier

ISSUER = "https://example.test/auth/v1"
AUDIENCE = "authenticated"
KID = "test-kid"
USER_ID = "11111111-2222-4333-8444-555555555555"


@pytest.fixture(scope="module")
def private_key():
    return ec.generate_private_key(ec.SECP256R1())


def make_token(key, kid=KID):
    now = int(time.time())
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": USER_ID,
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": kid})


@pytest.fixture
def fetches(monkeypatch, private_key):
    jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
    jwk.update(kid=KID, alg="ES256", use="sig")
    calls = []

    def fake_fetch(self):
        calls.append(1)
        return {"keys": [jwk]}

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", fake_fetch)
    return calls


def test_known_kid_yields_verifying_key(fetches, private_key):
    provider = JwksKeyProvider("https://example.test/jwks.json")
    verifier = SupabaseJwtVerifier(ISSUER, AUDIENCE, provider)
    assert str(verifier.verify(make_token(private_key)).user_id) == USER_ID


def test_unknown_kid_raises_token_error(fetches, private_key):
    provider = JwksKeyProvider("https://example.test/jwks.json")
    with pytest.raises(TokenError):
        provider.get_signing_key(make_token(private_key, kid="other"))


@pytest.mark.parametrize(
    "exc",
    [jwt.PyJWKClientConnectionError("down"), ConnectionError("down"), json.JSONDecodeError("x", "", 0)],
)
def test_fetch_failure_raises_token_error(monkeypatch, private_key, exc):
    def failing(self):
        raise exc

    monkeypatch.setattr(jwt.PyJWKClient, "fetch_data", failing)
    provider = JwksKeyProvider("https://example.test/jwks.json")
    with pytest.raises(TokenError):
        provider.get_signing_key(make_token(private_key))


def test_keys_fetched_once_within_lifespan(fetches, private_key):
    provider = JwksKeyProvider("https://example.test/jwks.json")
    token = make_token(private_key)
    provider.get_signing_key(token)
    provider.get_signing_key(token)
    assert len(fetches) == 1
