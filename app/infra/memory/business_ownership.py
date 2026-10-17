class InMemoryBusinessOwnership:
    def __init__(self, owned: dict[str, set[int]] | None = None) -> None:
        self._owned = {owner: set(ids) for owner, ids in (owned or {}).items()}

    def grant(self, owner_id: str, business_id: int) -> None:
        self._owned.setdefault(owner_id, set()).add(business_id)

    def owns(self, owner_id: str, business_id: int) -> bool:
        return business_id in self._owned.get(owner_id, ())
