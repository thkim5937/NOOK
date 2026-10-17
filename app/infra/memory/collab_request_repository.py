from app.domain.collab_request import CollabRequest, RequestStatus
from app.domain.repositories import AlreadyExists, NotFoundInRepository


class InMemoryCollabRequestRepository:
    def __init__(self) -> None:
        self._items: dict[int, CollabRequest] = {}  # dict keeps insertion order

    def add(self, request: CollabRequest) -> None:
        if request.id in self._items:
            raise AlreadyExists(request.id)
        self._items[request.id] = request

    def get(self, request_id: int) -> CollabRequest | None:
        return self._items.get(request_id)

    def update(self, request: CollabRequest) -> None:
        if request.id not in self._items:
            raise NotFoundInRepository(request.id)
        self._items[request.id] = request  # same key: position preserved

    def list_sent(self, business_id: int) -> list[CollabRequest]:
        return [r for r in self._items.values() if r.sender_business_id == business_id]

    def list_received(self, business_id: int) -> list[CollabRequest]:
        return [r for r in self._items.values() if r.receiver_business_id == business_id]

    def get_pending_between(
        self, business_a_id: int, business_b_id: int
    ) -> CollabRequest | None:
        pair = {business_a_id, business_b_id}
        for r in self._items.values():
            if r.status == RequestStatus.PENDING and {
                r.sender_business_id,
                r.receiver_business_id,
            } == pair:
                return r
        return None
