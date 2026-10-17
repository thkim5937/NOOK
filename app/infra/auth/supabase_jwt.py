"""Offline verification of Supabase access tokens (ES256, public JWKS)."""

import uuid
from typing import Any, Protocol

import jwt

from app.domain.auth import AuthenticatedUser, TokenError

ALLOWED_ALGORITHMS = ("ES256",)
_REQUIRED_CLAIMS = ["exp", "iat", "sub", "iss", "aud"]
_GENERIC_MESSAGE = "Invalid access token"


class SigningKeyProvider(Protocol):
    def get_signing_key(self, token: str) -> Any:
        """Return a key usable by jwt.decode. Raises TokenError if none matches."""
        ...


class JwksKeyProvider:
    def __init__(self, jwks_url: str, lifespan: int = 300, cooldown: int = 30, timeout: int = 5):
        self._client = jwt.PyJWKClient(
            jwks_url,
            cache_jwk_set=True,
            lifespan=lifespan,
            cooldown_duration=cooldown,
            timeout=timeout,
        )

    def get_signing_key(self, token: str) -> Any:
        try:
            return self._client.get_signing_key_from_jwt(token).key
        except jwt.PyJWTError:  # PyJWKClientError, PyJWKError, DecodeError
            raise TokenError(_GENERIC_MESSAGE) from None


class SupabaseJwtVerifier:
    def __init__(
        self,
        issuer: str,
        audience: str,
        key_provider: SigningKeyProvider,
        leeway_seconds: int = 10,
    ):
        self._issuer = issuer
        self._audience = audience
        self._keys = key_provider
        self._leeway = leeway_seconds

    def verify(self, token: str) -> AuthenticatedUser:
        if not isinstance(token, str) or not token:
            raise TokenError(_GENERIC_MESSAGE)
        try:
            key = self._keys.get_signing_key(token)
            payload = jwt.decode(
                token,
                key,
                algorithms=list(ALLOWED_ALGORITHMS),
                audience=self._audience,
                issuer=self._issuer,
                leeway=self._leeway,
                options={"require": _REQUIRED_CLAIMS},
            )
            if payload.get("role") != "authenticated" or payload.get("is_anonymous") is True:
                raise TokenError(_GENERIC_MESSAGE)
            return AuthenticatedUser(user_id=uuid.UUID(str(payload["sub"])))
        except TokenError:
            raise
        except (jwt.PyJWTError, ValueError, TypeError):
            # Library detail may echo token content; never propagate it.
            raise TokenError(_GENERIC_MESSAGE) from None
