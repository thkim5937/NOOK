"""Auth plug-in points. Routers get the caller ONLY via `current_owner`."""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends, Request

from app.core.config import settings
from app.core.errors import AppError, ErrorCode
from app.domain.auth import AuthenticatedOwner, AuthenticationFailed, Authenticator
from app.infra.auth.not_configured import NotConfiguredAuthenticator
from app.infra.auth.supabase_authenticator import SupabaseAuthenticator
from app.infra.auth.supabase_jwt import JwksKeyProvider, SupabaseJwtVerifier


def extract_credentials(request: Request) -> str | None:
    """The single place that knows where credentials come from.

    A cookie-based variant (e.g. request.cookies.get("session")) would only change this function.
    """
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    token = token.strip()
    return token if scheme.lower() == "bearer" and token else None


@lru_cache
def _supabase_authenticator(jwks_url: str, issuer: str, audience: str) -> Authenticator:
    # Cached so the JwksKeyProvider (and its key cache) lives once per process.
    verifier = SupabaseJwtVerifier(issuer, audience, JwksKeyProvider(jwks_url))
    return SupabaseAuthenticator(verifier)


def get_authenticator() -> Authenticator:
    jwks_url, issuer = settings.supabase_jwks_url, settings.supabase_issuer
    if jwks_url and issuer:
        return _supabase_authenticator(jwks_url, issuer, settings.SUPABASE_JWT_AUDIENCE)
    return NotConfiguredAuthenticator()


def current_owner(
    credentials: Annotated[str | None, Depends(extract_credentials)],
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> AuthenticatedOwner:
    try:
        return authenticator.authenticate(credentials)
    except AuthenticationFailed:
        raise AppError(ErrorCode.AUTH_REQUIRED, "Authentication required.") from None
