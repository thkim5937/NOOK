from app.domain.auth import (
    AuthenticatedOwner,
    AuthenticationFailed,
    TokenError,
    TokenVerifier,
)


class SupabaseAuthenticator:
    """Authenticator backed by a TokenVerifier.

    `credentials` is the bare token: `extract_credentials` in app/api/deps.py already stripped
    the "Bearer " scheme. business_id stays None; ownership is checked later in the service layer.
    """

    def __init__(self, verifier: TokenVerifier):
        self._verifier = verifier

    def authenticate(self, credentials: str | None) -> AuthenticatedOwner:
        if not credentials or len(credentials.split()) != 1:
            raise AuthenticationFailed("Authentication required.")
        try:
            user = self._verifier.verify(credentials)
        except TokenError:
            raise AuthenticationFailed("Authentication required.") from None
        return AuthenticatedOwner(owner_id=str(user.user_id), business_id=None)
