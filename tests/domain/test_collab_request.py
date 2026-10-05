import pytest

from app.domain.collab_request import (
    CollabRequest,
    InvalidRequest,
    InvalidStateTransition,
    NotRecipient,
    RequestSource,
    RequestStatus,
    accept,
    create_request,
    reject,
)


def make(source=RequestSource.PROFILE, **kw):
    return create_request("r1", "A", "B", source, **kw)


@pytest.mark.parametrize("source", list(RequestSource))
def test_all_sources_same_type_and_pending(source):
    r = make(source)
    assert type(r) is CollabRequest
    assert r.status == RequestStatus.PENDING
    assert r.source == source


def test_love_call_keeps_post_id():
    assert make(RequestSource.LOVE_CALL, post_id="p1").post_id == "p1"


def test_pending_to_accepted_and_rejected():
    assert accept(make(), "B").status == RequestStatus.ACCEPTED
    assert reject(make(), "B").status == RequestStatus.REJECTED


@pytest.mark.parametrize(
    "first,second",
    [(accept, reject), (reject, accept), (accept, accept), (reject, reject)],
)
def test_final_states_cannot_change(first, second):
    with pytest.raises(InvalidStateTransition):
        second(first(make(), "B"), "B")


@pytest.mark.parametrize("action", [accept, reject])
@pytest.mark.parametrize("actor", ["A", "C"])
def test_non_recipient_rejected(action, actor):
    with pytest.raises(NotRecipient):
        action(make(), actor)


def test_cannot_request_self():
    with pytest.raises(InvalidRequest):
        create_request("r1", "A", "A", RequestSource.PROFILE)


def test_original_unchanged():
    r = make()
    accept(r, "B")
    reject(r, "B")
    assert r.status == RequestStatus.PENDING
