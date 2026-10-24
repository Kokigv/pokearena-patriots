"""Traducción de errores a application/problem+json (RFC 9457) y middleware transversal."""

import logging
import uuid
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from pokearena.shared.errors import AppError

log = logging.getLogger("pokearena")
PROBLEM_JSON = "application/problem+json"
ERROR_BASE = "https://pokearena.dev/errors/"


def problem(
    status: int,
    type_: str,
    title: str,
    detail: str,
    instance: str,
    errors: list[dict[str, str]] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    body: dict[str, Any] = {
        "type": ERROR_BASE + type_ if type_ != "about:blank" else type_,
        "title": title,
        "status": status,
        "detail": detail,
        "instance": instance,
    }
    if errors:
        body["errors"] = errors
    return JSONResponse(body, status_code=status, media_type=PROBLEM_JSON, headers=headers)


def install(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = {"WWW-Authenticate": "Bearer"} if exc.status == 401 else None
        return problem(
            exc.status,
            exc.type,
            exc.title,
            exc.detail,
            request.url.path,
            [{"field": e.field, "reason": e.reason} for e in exc.errors],
            headers,
        )

    @app.exception_handler(RequestValidationError)
    async def request_validation(request: Request, exc: RequestValidationError) -> JSONResponse:
        errors = [
            {
                "field": ".".join(str(p) for p in e["loc"][1:]) or str(e["loc"][0]),
                "reason": e["msg"],
            }
            for e in exc.errors()
        ]
        return problem(
            422,
            "validation-error",
            "Datos inválidos",
            "La solicitud tiene campos inválidos.",
            request.url.path,
            errors,
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return problem(
            exc.status_code, "about:blank", str(exc.detail), str(exc.detail), request.url.path
        )

    @app.middleware("http")
    async def correlation_id(request: Request, call_next: Any) -> Any:
        cid = request.headers.get("X-Correlation-Id") or uuid.uuid4().hex
        try:
            response = await call_next(request)
        except Exception:
            log.exception("Error no controlado", extra={"correlation_id": cid})
            response = problem(
                500,
                "internal-error",
                "Error interno",
                "Ocurrió un error inesperado.",
                request.url.path,
            )
        response.headers["X-Correlation-Id"] = cid
        log.info(
            "%s %s -> %s",
            request.method,
            request.url.path,
            response.status_code,
            extra={"correlation_id": cid},
        )
        return response
