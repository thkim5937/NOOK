from app.domain.auth import AuthenticatedOwner, AuthenticationFailed


class NotConfiguredAuthenticator:
    """Deny everything until a real authenticator is plugged in."""

    def authenticate(self, credentials: str | None) -> AuthenticatedOwner:
        raise AuthenticationFailed("Authentication is not configured.")
