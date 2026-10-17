import base64
import json
import time
import uuid

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app.domain.auth import AuthenticatedUser, TokenError
from app.infra.auth.supabase_jwt import SupabaseJwtVerifier

ISSUER = "https://example.test/auth/v1"
AUDIENCE = "authenticated"
KID = "test-kid"
USER_ID = "11111111-2222-4333-8444-555555555555"


@pytest.fixture(scope="module")
def private_key():
    return ec.generate_private_key(ec.SECP256R1())


class FakeKeyProvider:
    def __init__(self, public_key):
        self.public_key = public_key

    def get_signing_key(self, token):
        if jwt.get_unverified_header(token).get("kid") != KID:
            raise TokenError("unknown kid")
        return self.public_key


@pytest.fixture(scope="module")
def verifier(private_key):
    return SupabaseJwtVerifier(ISSUER, AUDIENCE, FakeKeyProvider(private_key.public_key()))


def make_token(key, kid=KID, drop=(), **overrides):
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
    for name in drop:
        claims.pop(name)
    return jwt.encode(claims, key, algorithm="ES256", headers={"kid": kid})


def test_valid_token(verifier, private_key):
    assert verifier.verify(make_token(private_key)) == AuthenticatedUser(uuid.UUID(USER_ID))


def test_expired_within_leeway_accepted(verifier, private_key):
    assert verifier.verify(make_token(private_key, exp=int(time.time()) - 5))


def test_expired_beyond_leeway_rejected(verifier, private_key):
    with pytest.raises(TokenError):
        verifier.verify(make_token(private_key, exp=int(time.time()) - 60))


@pytest.mark.parametrize(
    "overrides",
    [
        {"iss": "https://other.test/auth/v1"},
        {"aud": "anon"},
        {"role": "anon"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"sub": "not-a-uuid"},
    ],
)
def test_bad_claims_rejected(verifier, private_key, overrides):
    with pytest.raises(TokenError):
        verifier.verify(make_token(private_key, **overrides))


@pytest.mark.parametrize("claim", ["exp", "iat", "sub"])
def test_missing_claim_rejected(verifier, private_key, claim):
    with pytest.raises(TokenError):
        verifier.verify(make_token(private_key, drop=(claim,)))


def test_other_signing_key_rejected(verifier):
    other = ec.generate_private_key(ec.SECP256R1())
    with pytest.raises(TokenError):
        verifier.verify(make_token(other))


def test_hs256_with_public_key_pem_rejected(verifier, private_key):
    pem = private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )
    now = int(time.time())
    claims = {"iss": ISSUER, "aud": AUDIENCE, "sub": USER_ID, "role": "authenticated",
              "iat": now, "exp": now + 3600}
    # PyJWT refuses PEM secrets for HMAC, so build the token by hand.
    import hashlib
    import hmac

    def b64(data: bytes) -> bytes:
        return base64.urlsafe_b64encode(data).rstrip(b"=")

    head = b64(json.dumps({"alg": "HS256", "typ": "JWT", "kid": KID}).encode())
    body = b64(json.dumps(claims).encode())
    sig = b64(hmac.new(pem, head + b"." + body, hashlib.sha256).digest())
    with pytest.raises(TokenError):
        verifier.verify((head + b"." + body + b"." + sig).decode())


def test_alg_none_rejected(verifier):
    def b64(data: dict) -> str:
        return base64.urlsafe_b64encode(json.dumps(data).encode()).rstrip(b"=").decode()

    now = int(time.time())
    token = (
        b64({"alg": "none", "typ": "JWT", "kid": KID})
        + "."
        + b64({"iss": ISSUER, "aud": AUDIENCE, "sub": USER_ID, "role": "authenticated",
               "iat": now, "exp": now + 3600})
        + "."
    )
    with pytest.raises(TokenError):
        verifier.verify(token)


def test_unknown_kid_rejected(verifier, private_key):
    with pytest.raises(TokenError):
        verifier.verify(make_token(private_key, kid="other"))


@pytest.mark.parametrize("token", ["garbage", "a.b.c", "", None, 123, b"bytes"])
def test_bad_tokens_rejected(verifier, token):
    with pytest.raises(TokenError):
        verifier.verify(token)


def test_error_message_never_contains_token(verifier, private_key):
    token = make_token(private_key, role="anon")
    with pytest.raises(TokenError) as info:
        verifier.verify(token)
    assert token not in str(info.value)
    assert token not in repr(info.value)
