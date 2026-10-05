"""Authentication boundary. Pure logic: no web or database imports."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.collab_request import DomainError


class AuthenticationFailed(DomainError):
    """Credentials are missing or invalid."""


@dataclass(frozen=True)
class AuthenticatedOwner:
    owner_id: str
    business_id: str | None


class Authenticator(Protocol):
    def authenticate(self, credentials: str | None) -> AuthenticatedOwner:
        """Return the caller. Raises AuthenticationFailed if credentials are missing/invalid."""
        ...
