import uuid

import pytest

from app.domain.auth import AuthenticatedOwner, AuthenticatedUser, AuthenticationFailed, TokenError
from app.infra.auth.supabase_authenticator import SupabaseAuthenticator

USER_ID = uuid.UUID("11111111-2222-4333-8444-555555555555")
GOOD = "good.token.value"


class FakeVerifier:
    def __init__(self):
        self.seen = []

    def verify(self, token):
        self.seen.append(token)
        if token != GOOD:
            raise TokenError(f"bad {token}")
        return AuthenticatedUser(USER_ID)


@pytest.fixture
def verifier():
    return FakeVerifier()


@pytest.fixture
def auth(verifier):
    return SupabaseAuthenticator(verifier)


# `credentials` arrives already stripped of "Bearer " by extract_credentials, so the
# header-shape cases (Bearer alone, Basic, lowercase scheme) are covered in tests/api.
@pytest.mark.parametrize("creds", [None, "", "   ", "a b", "a\tb"])
def test_unusable_credentials_rejected_without_verifying(auth, verifier, creds):
    with pytest.raises(AuthenticationFailed):
        auth.authenticate(creds)
    assert verifier.seen == []


def test_token_error_becomes_authentication_failed_without_token(auth):
    secret = "secret.token.xyz"
    with pytest.raises(AuthenticationFailed) as info:
        auth.authenticate(secret)
    assert secret not in str(info.value)
    assert secret not in repr(info.value)
    assert info.value.__cause__ is None


def test_valid_token_returns_owner(auth):
    assert auth.authenticate(GOOD) == AuthenticatedOwner(owner_id=str(USER_ID), business_id=None)
