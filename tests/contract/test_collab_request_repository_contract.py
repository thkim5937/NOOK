"""Contract tests: every CollabRequestRepository implementation must pass these.

To cover a new implementation (e.g. database-backed), add its factory to FACTORIES.
"""

from datetime import UTC, datetime

import pytest

from app.domain.collab_request import RequestSource, RequestStatus, accept, cancel, create_request
from app.domain.repositories import AlreadyExists, NotFoundInRepository
from app.infra.memory.collab_request_repository import InMemoryCollabRequestRepository

FACTORIES = [InMemoryCollabRequestRepository]


@pytest.fixture(params=FACTORIES, ids=lambda f: f.__name__)
def repo(request):
    return request.param()


def req(id, sender=1, receiver=2, source=RequestSource.PROFILE, post_id=None):
    return create_request(id, sender, receiver, source, post_id=post_id)


def test_add_then_get(repo):
    r = req("r1")
    repo.add(r)
    assert repo.get("r1") == r


def test_get_unknown_returns_none(repo):
    assert repo.get("nope") is None


def test_add_duplicate_id_raises(repo):
    repo.add(req("r1"))
    with pytest.raises(AlreadyExists):
        repo.add(req("r1", sender=3))


def test_update_replaces_stored_request(repo):
    r = req("r1")
    repo.add(r)
    accepted = accept(r, 2, datetime(2026, 1, 1, tzinfo=UTC))
    repo.update(accepted)
    assert repo.get("r1") == accepted
    assert repo.get("r1").status == RequestStatus.ACCEPTED


def test_update_persists_cancelled_with_responded_at(repo):
    r = req("r1")
    repo.add(r)
    now = datetime(2026, 1, 1, tzinfo=UTC)
    repo.update(cancel(r, 1, now))
    stored = repo.get("r1")
    assert stored.status == RequestStatus.CANCELLED
    assert stored.responded_at == now


def test_update_unknown_raises(repo):
    with pytest.raises(NotFoundInRepository):
        repo.update(req("ghost"))


def test_list_sent_and_received_filter_in_insertion_order(repo):
    a_to_b = req("r1", 1, 2)
    c_to_a = req("r2", 3, 1)
    a_to_c = req("r3", 1, 3)
    b_to_c = req("r4", 2, 3)
    for r in (a_to_b, c_to_a, a_to_c, b_to_c):
        repo.add(r)
    assert repo.list_sent(1) == [a_to_b, a_to_c]
    assert repo.list_received(3) == [a_to_c, b_to_c]
    assert repo.list_sent(99) == []
    assert repo.list_received(99) == []


@pytest.mark.parametrize("source", list(RequestSource))
def test_all_sources_round_trip(repo, source):
    r = req("r1", source=source, post_id=10 if source == RequestSource.COLLAB_POST else None)
    repo.add(r)
    assert repo.get("r1") == r
