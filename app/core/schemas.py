from pydantic import BaseModel

from app.core.constants import AI_DISCLOSURE_TEXT


class DataResponse[T](BaseModel):
    """Success wrapper: {"data": ...}."""

    data: T


class AIGeneratedMeta(BaseModel):
    ai_generated: bool = True
    disclosure: str = AI_DISCLOSURE_TEXT
