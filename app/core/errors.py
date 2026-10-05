import logging
from enum import StrEnum
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)


class ErrorCode(StrEnum):
    AUTH_REQUIRED = "AUTH_REQUIRED"
    AUTH_FORBIDDEN = "AUTH_FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    REQUEST_INVALID_STATE = "REQUEST_INVALID_STATE"
    REQUEST_VALIDATION_FAILED = "REQUEST_VALIDATION_FAILED"
    INTERNAL_ERROR = "INTERNAL_ERROR"
    HTTP_ERROR = "HTTP_ERROR"  # other framework HTTP errors; keeps original status


# Single source of truth for code -> HTTP status. HTTP_ERROR has no fixed status.
STATUS: dict[ErrorCode, int] = {
    ErrorCode.AUTH_REQUIRED: 401,
    ErrorCode.AUTH_FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.REQUEST_INVALID_STATE: 409,
    ErrorCode.REQUEST_VALIDATION_FAILED: 422,
    ErrorCode.INTERNAL_ERROR: 500,
}

_FROM_STATUS = {401: ErrorCode.AUTH_REQUIRED, 403: ErrorCode.AUTH_FORBIDDEN, 404: ErrorCode.NOT_FOUND}


class AppError(Exception):
    def __init__(self, code: ErrorCode, message: str, details: list[Any] | None = None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


def _response(status: int, code: ErrorCode, message: str, details: list[Any] | None = None):
    body = {"error": {"code": code.value, "message": message, "details": details or []}}
    return JSONResponse(status_code=status, content=body)


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def _app_error(_: Request, exc: AppError):
        return _response(STATUS[exc.code], exc.code, exc.message, exc.details)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        details = [
            {"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"], "type": e["type"]}
            for e in exc.errors()
        ]
        code = ErrorCode.REQUEST_VALIDATION_FAILED
        return _response(STATUS[code], code, "Request validation failed.", details)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        code = _FROM_STATUS.get(exc.status_code, ErrorCode.HTTP_ERROR)
        return _response(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        logger.exception("Unhandled exception", exc_info=exc)
        code = ErrorCode.INTERNAL_ERROR
        return _response(STATUS[code], code, "Internal server error.")
