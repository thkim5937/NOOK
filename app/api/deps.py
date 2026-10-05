"""Auth plug-in points. Routers get the caller ONLY via `current_owner`."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.errors import AppError, ErrorCode
from app.domain.auth import AuthenticatedOwner, AuthenticationFailed, Authenticator
from app.infra.auth.not_configured import NotConfiguredAuthenticator


def extract_credentials(request: Request) -> str | None:
    """The single place that knows where credentials come from.

    A cookie-based variant (e.g. request.cookies.get("session")) would only change this function.
    """
    scheme, _, token = request.headers.get("Authorization", "").partition(" ")
    token = token.strip()
    return token if scheme.lower() == "bearer" and token else None


def get_authenticator() -> Authenticator:
    return NotConfiguredAuthenticator()


def current_owner(
    credentials: Annotated[str | None, Depends(extract_credentials)],
    authenticator: Annotated[Authenticator, Depends(get_authenticator)],
) -> AuthenticatedOwner:
    try:
        return authenticator.authenticate(credentials)
    except AuthenticationFailed:
        raise AppError(ErrorCode.AUTH_REQUIRED, "Authentication required.") from None
