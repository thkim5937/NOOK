"""Collaboration request state machine. Pure logic: no web or database imports."""

from dataclasses import dataclass, replace
from datetime import datetime
from enum import StrEnum


class DomainError(Exception):
    """Base class for all domain rule violations."""


class InvalidStateTransition(DomainError):
    pass


class NotRecipient(DomainError):
    pass


class NotSender(DomainError):
    pass


class InvalidRequest(DomainError):
    pass


class RequestStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"


class RequestSource(StrEnum):
    AI_RECOMMENDATION = "ai_recommendation"
    COLLAB_POST = "collab_post"
    PROFILE = "profile"


# PROVISIONAL: these values are not final until the data teammate fixes the DB catalog.
class CollabType(StrEnum):
    LIMITED_PRODUCT = "limited_product"
    POPUP = "popup"
    JOINT_EVENT = "joint_event"
    SNS_COLLAB = "sns_collab"


# Single source of truth: current status -> statuses it may move to.
ALLOWED_TRANSITIONS: dict[RequestStatus, frozenset[RequestStatus]] = {
    RequestStatus.PENDING: frozenset(
        {RequestStatus.ACCEPTED, RequestStatus.REJECTED, RequestStatus.CANCELLED}
    ),
    RequestStatus.ACCEPTED: frozenset(),
    RequestStatus.REJECTED: frozenset(),
    RequestStatus.CANCELLED: frozenset(),
}


@dataclass(frozen=True)
class CollabRequest:
    id: str
    sender_business_id: int
    receiver_business_id: int
    source: RequestSource
    status: RequestStatus
    post_id: int | None = None
    message: str | None = None
    match_id: int | None = None
    collab_type: CollabType | None = None
    desired_timing: str | None = None
    responded_at: datetime | None = None


def create_request(
    id: str,
    sender_business_id: int,
    receiver_business_id: int,
    source: RequestSource,
    post_id: int | None = None,
    message: str | None = None,
    match_id: int | None = None,
    collab_type: CollabType | None = None,
    desired_timing: str | None = None,
) -> CollabRequest:
    if sender_business_id == receiver_business_id:
        raise InvalidRequest("A business cannot send a request to itself")
    if source == RequestSource.COLLAB_POST and post_id is None:
        raise InvalidRequest("COLLAB_POST requests require post_id")
    if source != RequestSource.COLLAB_POST and post_id is not None:
        raise InvalidRequest(f"{source} requests must not have post_id")
    return CollabRequest(
        id=id,
        sender_business_id=sender_business_id,
        receiver_business_id=receiver_business_id,
        source=source,
        status=RequestStatus.PENDING,
        post_id=post_id,
        message=message,
        match_id=match_id,
        collab_type=collab_type,
        desired_timing=desired_timing,
    )


def _transition(
    request: CollabRequest, new_status: RequestStatus, now: datetime
) -> CollabRequest:
    if new_status not in ALLOWED_TRANSITIONS[request.status]:
        raise InvalidStateTransition(f"{request.status} -> {new_status} is not allowed")
    return replace(request, status=new_status, responded_at=now)


def _respond(
    request: CollabRequest,
    actor_business_id: int,
    new_status: RequestStatus,
    now: datetime,
) -> CollabRequest:
    if actor_business_id != request.receiver_business_id:
        raise NotRecipient("Only the receiver may respond to a request")
    return _transition(request, new_status, now)


def accept(request: CollabRequest, actor_business_id: int, now: datetime) -> CollabRequest:
    return _respond(request, actor_business_id, RequestStatus.ACCEPTED, now)


def reject(request: CollabRequest, actor_business_id: int, now: datetime) -> CollabRequest:
    return _respond(request, actor_business_id, RequestStatus.REJECTED, now)


def cancel(request: CollabRequest, actor_business_id: int, now: datetime) -> CollabRequest:
    if actor_business_id != request.sender_business_id:
        raise NotSender("Only the sender may cancel a request")
    return _transition(request, RequestStatus.CANCELLED, now)
