from datetime import UTC, datetime

import pytest

from app.domain.collab_request import (
    CollabRequest,
    CollabType,
    InvalidRequest,
    InvalidStateTransition,
    NotRecipient,
    NotSender,
    RequestSource,
    RequestStatus,
    accept,
    cancel,
    create_request,
    reject,
)

NOW = datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)
SENDER, RECEIVER = 1, 2


def make(source=RequestSource.PROFILE, **kw):
    return create_request("r1", SENDER, RECEIVER, source, **kw)


def make_for(source):
    return make(source, post_id=10) if source == RequestSource.COLLAB_POST else make(source)


@pytest.mark.parametrize("source", list(RequestSource))
def test_all_sources_same_type_and_pending(source):
    r = make_for(source)
    assert type(r) is CollabRequest
    assert r.status == RequestStatus.PENDING
    assert r.source == source
    assert r.responded_at is None


def test_source_values():
    assert {s.name: s.value for s in RequestSource} == {
        "AI_RECOMMENDATION": "ai_recommendation",
        "COLLAB_POST": "collab_post",
        "PROFILE": "profile",
    }


def test_collab_post_keeps_post_id():
    assert make(RequestSource.COLLAB_POST, post_id=10).post_id == 10


def test_collab_post_without_post_id_rejected():
    with pytest.raises(InvalidRequest):
        make(RequestSource.COLLAB_POST)


@pytest.mark.parametrize("source", [RequestSource.AI_RECOMMENDATION, RequestSource.PROFILE])
def test_other_sources_reject_post_id(source):
    with pytest.raises(InvalidRequest):
        make(source, post_id=10)


def test_optional_fields_stored():
    r = make(
        message="hi",
        match_id=5,
        collab_type=CollabType.POPUP,
        desired_timing="next month",
    )
    assert (r.message, r.match_id, r.collab_type, r.desired_timing) == (
        "hi",
        5,
        CollabType.POPUP,
        "next month",
    )


def test_pending_to_accepted_and_rejected_set_responded_at():
    a = accept(make(), RECEIVER, NOW)
    assert a.status == RequestStatus.ACCEPTED
    assert a.responded_at == NOW
    r = reject(make(), RECEIVER, NOW)
    assert r.status == RequestStatus.REJECTED
    assert r.responded_at == NOW


def test_cancel_by_sender_from_pending():
    c = cancel(make(), SENDER, NOW)
    assert c.status == RequestStatus.CANCELLED
    assert c.responded_at == NOW


@pytest.mark.parametrize("actor", [RECEIVER, 3])
def test_cancel_by_non_sender_rejected(actor):
    with pytest.raises(NotSender):
        cancel(make(), actor, NOW)


@pytest.mark.parametrize(
    "prepare",
    [
        lambda r: accept(r, RECEIVER, NOW),
        lambda r: reject(r, RECEIVER, NOW),
        lambda r: cancel(r, SENDER, NOW),
    ],
)
def test_cancel_from_non_pending_rejected(prepare):
    with pytest.raises(InvalidStateTransition):
        cancel(prepare(make()), SENDER, NOW)


@pytest.mark.parametrize(
    "first,second",
    [(accept, reject), (reject, accept), (accept, accept), (reject, reject)],
)
def test_final_states_cannot_change(first, second):
    with pytest.raises(InvalidStateTransition):
        second(first(make(), RECEIVER, NOW), RECEIVER, NOW)


@pytest.mark.parametrize("final", [accept, reject])
def test_respond_after_cancel_rejected(final):
    with pytest.raises(InvalidStateTransition):
        final(cancel(make(), SENDER, NOW), RECEIVER, NOW)


@pytest.mark.parametrize("action", [accept, reject])
@pytest.mark.parametrize("actor", [SENDER, 3])
def test_non_receiver_rejected(action, actor):
    with pytest.raises(NotRecipient):
        action(make(), actor, NOW)


def test_cannot_request_self():
    with pytest.raises(InvalidRequest):
        create_request("r1", 1, 1, RequestSource.PROFILE)


def test_original_unchanged():
    r = make()
    accept(r, RECEIVER, NOW)
    reject(r, RECEIVER, NOW)
    cancel(r, SENDER, NOW)
    assert r.status == RequestStatus.PENDING
    assert r.responded_at is None
