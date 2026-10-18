"""The one place where domain errors become contract error codes. Messages are generic on purpose."""

from fastapi import FastAPI, Request

from app.core.errors import STATUS, ErrorCode, _response
from app.domain.collab_request import (
    DuplicatePendingRequest,
    Forbidden,
    InvalidRequest,
    InvalidStateTransition,
)
from app.domain.repositories import NotFoundInRepository

_MAPPING: dict[type[Exception], tuple[ErrorCode, str]] = {
    Forbidden: (ErrorCode.AUTH_FORBIDDEN, "Not allowed."),
    DuplicatePendingRequest: (
        ErrorCode.REQUEST_INVALID_STATE,
        "Request is not in a state that allows this action.",
    ),
    InvalidStateTransition: (
        ErrorCode.REQUEST_INVALID_STATE,
        "Request is not in a state that allows this action.",
    ),
    InvalidRequest: (ErrorCode.REQUEST_VALIDATION_FAILED, "Request validation failed."),
    NotFoundInRepository: (ErrorCode.NOT_FOUND, "Not found."),
}


def register_domain_error_handlers(app: FastAPI) -> None:
    for exc_type, (code, message) in _MAPPING.items():

        async def handler(_: Request, __: Exception, code=code, message=message):
            return _response(STATUS[code], code, message)

        app.add_exception_handler(exc_type, handler)
