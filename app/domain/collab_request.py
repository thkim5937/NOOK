"""Collaboration request state machine. Pure logic: no web or database imports."""

from dataclasses import dataclass, replace
from enum import StrEnum


class DomainError(Exception):
    """Base class for all domain rule violations."""


class InvalidStateTransition(DomainError):
    pass


class NotRecipient(DomainError):
    pass


class InvalidRequest(DomainError):
    pass


class RequestStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class RequestSource(StrEnum):
    RECOMMENDATION = "RECOMMENDATION"
    LOVE_CALL = "LOVE_CALL"
    PROFILE = "PROFILE"


# Single source of truth: current status -> statuses it may move to.
ALLOWED_TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.PENDING: frozenset({RequestStatus.ACCEPTED, RequestStatus.REJECTED}),
    RequestStatus.ACCEPTED: frozenset(),
    RequestStatus.REJECTED: frozenset(),
}


@dataclass(frozen=True)
class CollabRequest:
    id: str
    sender_business_id: str
    recipient_business_id: str
    source: RequestSource
    status: RequestStatus
    post_id: str | None = None


def create_request(
    id: str,
    sender_business_id: str,
    recipient_business_id: str,
    source: RequestSource,
    post_id: str | None = None,
) -> CollabRequest:
    if sender_business_id == recipient_business_id:
        raise InvalidRequest("A business cannot send a request to itself")
    return CollabRequest(
        id=id,
        sender_business_id=sender_business_id,
        recipient_business_id=recipient_business_id,
        source=source,
        status=RequestStatus.PENDING,
        post_id=post_id,
    )


def _transition(
    request: CollabRequest, actor_business_id: str, new_status: RequestStatus
) -> CollabRequest:
    if actor_business_id != request.recipient_business_id:
        raise NotRecipient("Only the recipient may respond to a request")
    if new_status not in ALLOWED_TRANSITIONS[request.status]:
        raise InvalidStateTransition(f"{request.status} -> {new_status} is not allowed")
    return replace(request, status=new_status)


def accept(request: CollabRequest, actor_business_id: str) -> CollabRequest:
    return _transition(request, actor_business_id, RequestStatus.ACCEPTED)


def reject(request: CollabRequest, actor_business_id: str) -> CollabRequest:
    return _transition(request, actor_business_id, RequestStatus.REJECTED)
