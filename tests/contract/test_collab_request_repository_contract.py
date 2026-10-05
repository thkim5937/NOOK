"""Contract tests: every CollabRequestRepository implementation must pass these.

To cover a new implementation (e.g. database-backed), add its factory to FACTORIES.
"""

import pytest

from app.domain.collab_request import RequestSource, RequestStatus, accept, create_request
from app.domain.repositories import AlreadyExists, NotFoundInRepository
from app.infra.memory.collab_request_repository import InMemoryCollabRequestRepository

FACTORIES = [InMemoryCollabRequestRepository]


@pytest.fixture(params=FACTORIES, ids=lambda f: f.__name__)
def repo(request):
    return request.param()


def req(id, sender="A", recipient="B", source=RequestSource.PROFILE):
    return create_request(id, sender, recipient, source)


def test_add_then_get(repo):
    r = req("r1")
    repo.add(r)
    assert repo.get("r1") == r


def test_get_unknown_returns_none(repo):
    assert repo.get("nope") is None


def test_add_duplicate_id_raises(repo):
    repo.add(req("r1"))
    with pytest.raises(AlreadyExists):
        repo.add(req("r1", sender="C"))


def test_update_replaces_stored_request(repo):
    r = req("r1")
    repo.add(r)
    accepted = accept(r, "B")
    repo.update(accepted)
    assert repo.get("r1") == accepted
    assert repo.get("r1").status == RequestStatus.ACCEPTED


def test_update_unknown_raises(repo):
    with pytest.raises(NotFoundInRepository):
        repo.update(req("ghost"))


def test_list_sent_and_received_filter_in_insertion_order(repo):
    a_to_b = req("r1", "A", "B")
    c_to_a = req("r2", "C", "A")
    a_to_c = req("r3", "A", "C")
    b_to_c = req("r4", "B", "C")
    for r in (a_to_b, c_to_a, a_to_c, b_to_c):
        repo.add(r)
    assert repo.list_sent("A") == [a_to_b, a_to_c]
    assert repo.list_received("C") == [a_to_c, b_to_c]
    assert repo.list_sent("Z") == []
    assert repo.list_received("Z") == []


@pytest.mark.parametrize("source", list(RequestSource))
def test_all_sources_round_trip(repo, source):
    r = req("r1", source=source)
    repo.add(r)
    assert repo.get("r1") == r
