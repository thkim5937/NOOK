from datetime import UTC, datetime

import pytest

from app.domain.collab_request import (
    DuplicatePendingRequest,
    Forbidden,
    InvalidRequest,
    InvalidStateTransition,
    RequestSource,
    RequestStatus,
)
from app.domain.collab_request_service import CollabRequestService
from app.domain.repositories import NotFoundInRepository
from app.infra.memory.business_ownership import InMemoryBusinessOwnership
from app.infra.memory.collab_request_repository import InMemoryCollabRequestRepository

NOW = datetime(2026, 3, 4, 5, 6, 7, tzinfo=UTC)
# alice owns 1 and 3; bob owns 2; carol owns nothing
OWNED = {"alice": {1, 3}, "bob": {2}}


@pytest.fixture
def repo():
    return InMemoryCollabRequestRepository()


@pytest.fixture
def svc(repo):
    return CollabRequestService(repo, InMemoryBusinessOwnership(OWNED), clock=lambda: NOW)


def send(svc, owner="alice", sender=1, receiver=2):
    return svc.create(owner, sender, receiver, RequestSource.PROFILE)


def test_owner_of_sender_creates_pending_and_persists(svc, repo):
    r = send(svc)
    assert r.status == RequestStatus.PENDING
    assert r.responded_at is None
    assert repo.get(r.id) == r


def test_non_owner_forbidden_and_nothing_persisted(svc, repo):
    with pytest.raises(Forbidden):
        send(svc, owner="carol")
    with pytest.raises(Forbidden):
        send(svc, owner="bob")  # owns the receiver, not the sender
    assert repo.list_sent(1) == []


def test_self_request_rejected_before_ownership(svc, repo):
    with pytest.raises(InvalidRequest):
        svc.create("carol", 1, 1, RequestSource.PROFILE)
    assert repo.list_sent(1) == []


def test_duplicate_same_direction_rejected(svc):
    send(svc)
    with pytest.raises(DuplicatePendingRequest):
        send(svc)


def test_duplicate_reverse_direction_rejected(svc):
    send(svc)
    with pytest.raises(DuplicatePendingRequest):
        send(svc, owner="bob", sender=2, receiver=1)


@pytest.mark.parametrize("action", ["accept", "reject", "cancel"])
def test_new_pending_allowed_after_earlier_one_closed(svc, action):
    first = send(svc)
    owner = "alice" if action == "cancel" else "bob"
    getattr(svc, action)(owner, first.id)
    second = send(svc)
    assert second.id != first.id
    assert second.status == RequestStatus.PENDING


def test_multi_business_owner_sends_only_from_owned(svc):
    assert svc.create("alice", 3, 2, RequestSource.PROFILE).sender_business_id == 3
    with pytest.raises(Forbidden):
        svc.create("alice", 2, 1, RequestSource.PROFILE)


@pytest.mark.parametrize(
    "action, status",
    [("accept", RequestStatus.ACCEPTED), ("reject", RequestStatus.REJECTED)],
)
def test_receiver_owner_responds_and_responded_at_is_clock(svc, repo, action, status):
    r = send(svc)
    out = getattr(svc, action)("bob", r.id)
    assert out.status == status
    assert out.responded_at == NOW
    assert repo.get(r.id) == out


@pytest.mark.parametrize("action", ["accept", "reject"])
@pytest.mark.parametrize("owner", ["alice", "carol"])
def test_sender_or_stranger_cannot_respond(svc, repo, action, owner):
    r = send(svc)
    with pytest.raises(Forbidden):
        getattr(svc, action)(owner, r.id)
    assert repo.get(r.id) == r


def test_sender_owner_cancels_responded_at_stays_none(svc, repo):
    r = send(svc)
    out = svc.cancel("alice", r.id)
    assert out.status == RequestStatus.CANCELLED
    assert out.responded_at is None
    assert repo.get(r.id) == out


@pytest.mark.parametrize("owner", ["bob", "carol"])
def test_only_sender_owner_can_cancel(svc, owner):
    r = send(svc)
    with pytest.raises(Forbidden):
        svc.cancel(owner, r.id)


@pytest.mark.parametrize("action", ["accept", "reject", "cancel"])
def test_unknown_id_raises_not_found(svc, action):
    with pytest.raises(NotFoundInRepository):
        getattr(svc, action)("alice", 999)


def test_illegal_transitions_keep_entity_error(svc):
    r = send(svc)
    svc.cancel("alice", r.id)
    with pytest.raises(InvalidStateTransition):
        svc.accept("bob", r.id)
    with pytest.raises(InvalidStateTransition):
        svc.cancel("alice", r.id)


def test_permission_checked_before_state(svc):
    r = send(svc)
    svc.cancel("alice", r.id)  # now final
    with pytest.raises(Forbidden):  # not InvalidStateTransition
        svc.accept("carol", r.id)


def test_forbidden_message_reveals_no_request_state(svc):
    r = send(svc)
    svc.cancel("alice", r.id)
    with pytest.raises(Forbidden) as exc:
        svc.accept("carol", r.id)
    text = str(exc.value).lower()
    for word in ("pending", "accepted", "rejected", "cancelled", str(r.id)):
        assert word not in text
