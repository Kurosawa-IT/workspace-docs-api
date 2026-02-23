from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_id import request_id_var


def _rid() -> str:
    return request_id_var.get() or "-"


def _code(status_code: int) -> str:
    return {
        401: "unauthorized",
        403: "forbidden",
        404: "not_found",
        409: "conflict",
        422: "validation_error",
    }.get(status_code, "error")


def _message(status_code: int, detail: Any | None = None) -> str:
    if isinstance(detail, str) and detail:
        return detail
    return {
        401: "Not authenticated",
        403: "Forbidden",
        404: "Not found",
        409: "Conflict",
        422: "Validation error",
    }.get(status_code, "Error")


def install_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        detail = getattr(exc, "detail", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": _code(exc.status_code),
                    "message": _message(exc.status_code, detail),
                    "details": detail if detail is not None else {},
                },
                "request_id": _rid(),
            },
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "code": _code(422),
                    "message": _message(422),
                    "details": {"errors": exc.errors()},
                },
                "request_id": _rid(),
            },
        )
