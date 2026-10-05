from app.domain.collab_request import CollabRequest
from app.domain.repositories import AlreadyExists, NotFoundInRepository


class InMemoryCollabRequestRepository:
    def __init__(self) -> None:
        self._items: dict[str, CollabRequest] = {}  # dict keeps insertion order

    def add(self, request: CollabRequest) -> None:
        if request.id in self._items:
            raise AlreadyExists(request.id)
        self._items[request.id] = request

    def get(self, request_id: str) -> CollabRequest | None:
        return self._items.get(request_id)

    def update(self, request: CollabRequest) -> None:
        if request.id not in self._items:
            raise NotFoundInRepository(request.id)
        self._items[request.id] = request  # same key: position preserved

    def list_sent(self, business_id: str) -> list[CollabRequest]:
        return [r for r in self._items.values() if r.sender_business_id == business_id]

    def list_received(self, business_id: str) -> list[CollabRequest]:
        return [r for r in self._items.values() if r.recipient_business_id == business_id]
