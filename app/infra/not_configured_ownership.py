class NotConfiguredBusinessOwnership:
    """Deny everything until a database ownership adapter exists."""

    def owns(self, owner_id: str, business_id: int) -> bool:
        return False
