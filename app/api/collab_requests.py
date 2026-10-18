from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Path
from pydantic import BaseModel, ConfigDict, Field, StrictInt

from app.api.deps import current_owner, get_collab_service
from app.core.schemas import DataResponse
from app.domain.auth import AuthenticatedOwner
from app.domain.collab_request import CollabRequest, CollabType, RequestSource, RequestStatus
from app.domain.collab_request_service import CollabRequestService

router = APIRouter(prefix="/v1/collab-requests", tags=["collab-requests"])

Owner = Annotated[AuthenticatedOwner, Depends(current_owner)]
Service = Annotated[CollabRequestService, Depends(get_collab_service)]
RequestId = Annotated[int, Path(ge=1)]


class CollabRequestCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sender_business_id: Annotated[int, Field(strict=True, ge=1)]
    receiver_business_id: StrictInt
    source: RequestSource
    post_id: StrictInt | None = None
    match_id: StrictInt | None = None
    message: str | None = None
    collab_type: CollabType | None = None
    desired_timing: str | None = None


class CollabRequestOut(BaseModel):
    id: int
    sender_business_id: int
    receiver_business_id: int
    source: RequestSource
    status: RequestStatus
    post_id: int | None
    match_id: int | None
    message: str | None
    collab_type: CollabType | None
    desired_timing: str | None
    responded_at: datetime | None

    @classmethod
    def of(cls, r: CollabRequest) -> "DataResponse[CollabRequestOut]":
        return DataResponse(data=cls(**r.__dict__))


@router.post("", status_code=201, response_model=DataResponse[CollabRequestOut])
def create(body: CollabRequestCreate, owner: Owner, service: Service):
    return CollabRequestOut.of(service.create(owner.owner_id, **body.model_dump()))


@router.post("/{id}/accept", response_model=DataResponse[CollabRequestOut])
def accept(id: RequestId, owner: Owner, service: Service):
    return CollabRequestOut.of(service.accept(owner.owner_id, id))


@router.post("/{id}/reject", response_model=DataResponse[CollabRequestOut])
def reject(id: RequestId, owner: Owner, service: Service):
    return CollabRequestOut.of(service.reject(owner.owner_id, id))


@router.post("/{id}/cancel", response_model=DataResponse[CollabRequestOut])
def cancel(id: RequestId, owner: Owner, service: Service):
    return CollabRequestOut.of(service.cancel(owner.owner_id, id))
