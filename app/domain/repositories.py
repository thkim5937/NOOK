"""Repository interfaces for the domain layer. No infra, web or DB imports."""

from typing import Protocol

from app.domain.collab_request import CollabRequest, DomainError


class AlreadyExists(DomainError):
    pass


class NotFoundInRepository(DomainError):
    pass


class CollabRequestRepository(Protocol):
    def add(self, request: CollabRequest) -> None:
        """Store a new request. Raises AlreadyExists if the id is taken."""
        ...

    def get(self, request_id: str) -> CollabRequest | None: ...

    def update(self, request: CollabRequest) -> None:
        """Replace an existing request. Raises NotFoundInRepository if unknown."""
        ...

    def list_sent(self, business_id: int) -> list[CollabRequest]:
        """Requests sent by business_id, in insertion order."""
        ...

    def list_received(self, business_id: int) -> list[CollabRequest]:
        """Requests received by business_id, in insertion order."""
        ...
