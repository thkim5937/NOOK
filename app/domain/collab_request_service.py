"""Collaboration request use cases. Pure logic over ports: no web or database imports."""

from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from itertools import count

from app.domain import collab_request as cr
from app.domain.collab_request import (
    CollabRequest,
    CollabType,
    DuplicatePendingRequest,
    Forbidden,
    InvalidRequest,
    RequestSource,
)
from app.domain.repositories import (
    BusinessOwnership,
    CollabRequestRepository,
    NotFoundInRepository,
)

Clock = Callable[[], datetime]  # must return an aware UTC datetime


def utc_now() -> datetime:
    return datetime.now(UTC)


class CollabRequestService:
    def __init__(
        self,
        repo: CollabRequestRepository,
        ownership: BusinessOwnership,
        clock: Clock = utc_now,
        next_id: Callable[[], int] | None = None,
    ) -> None:
        self._repo = repo
        self._ownership = ownership
        self._clock = clock
        # ponytail: in-process counter; a database repository assigns ids itself
        self._next_id = next_id or count(1).__next__

    def create(
        self,
        owner_id: str,
        sender_business_id: int,
        receiver_business_id: int,
        source: RequestSource,
        match_id: int | None = None,
        post_id: int | None = None,
        message: str | None = None,
        collab_type: CollabType | None = None,
        desired_timing: str | None = None,
    ) -> CollabRequest:
        if sender_business_id == receiver_business_id:
            raise InvalidRequest("A business cannot send a request to itself")
        self._require_owner(owner_id, sender_business_id)
        if self._repo.get_pending_between(sender_business_id, receiver_business_id):
            raise DuplicatePendingRequest("A pending request already exists between these businesses")
        request = cr.create_request(
            self._next_id(),
            sender_business_id,
            receiver_business_id,
            source,
            post_id=post_id,
            message=message,
            match_id=match_id,
            collab_type=collab_type,
            desired_timing=desired_timing,
        )
        self._repo.add(request)
        return request

    def accept(self, owner_id: str, request_id: int) -> CollabRequest:
        return self._respond(owner_id, request_id, cr.accept)

    def reject(self, owner_id: str, request_id: int) -> CollabRequest:
        return self._respond(owner_id, request_id, cr.reject)

    def cancel(self, owner_id: str, request_id: int) -> CollabRequest:
        request = self._load(request_id)
        self._require_owner(owner_id, request.sender_business_id)
        cancelled = cr.cancel(request, request.sender_business_id, self._clock())
        # assumption: only accept/reject are "responses"; cancel leaves responded_at empty
        return self._save(replace(cancelled, responded_at=None))

    def _respond(self, owner_id: str, request_id: int, action) -> CollabRequest:
        request = self._load(request_id)
        self._require_owner(owner_id, request.receiver_business_id)
        return self._save(action(request, request.receiver_business_id, self._clock()))

    def _load(self, request_id: int) -> CollabRequest:
        request = self._repo.get(request_id)
        if request is None:
            raise NotFoundInRepository(request_id)
        return request

    def _require_owner(self, owner_id: str, business_id: int) -> None:
        if not self._ownership.owns(owner_id, business_id):
            raise Forbidden("You do not own the business for this action")

    def _save(self, request: CollabRequest) -> CollabRequest:
        self._repo.update(request)
        return request
