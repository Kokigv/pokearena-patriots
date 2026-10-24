"""Ejecución idempotente de operaciones de creación en la capa HTTP (RNF-INT-01)."""

import contextlib
import logging
from collections.abc import Callable
from typing import Any

from fastapi.responses import JSONResponse
from redis.exceptions import RedisError

from pokearena.shared.errors import FieldError, ValidationFailed
from pokearena.shared.idempotency import (
    IdempotencyStore,
    RequestInProgress,
    ReservationState,
)

log = logging.getLogger(__name__)
MAX_KEY_LENGTH = 100


def require_key(key: str | None) -> str:
    if key is None or not key.strip():
        raise ValidationFailed(
            [FieldError("Idempotency-Key", "el encabezado es obligatorio en esta operación")]
        )
    if len(key) > MAX_KEY_LENGTH:
        raise ValidationFailed(
            [FieldError("Idempotency-Key", f"máximo {MAX_KEY_LENGTH} caracteres")]
        )
    return key.strip()


def run_idempotent(
    store: IdempotencyStore,
    scope: str,
    key: str,
    fingerprint: str,
    action: Callable[[], tuple[int, dict[str, Any], dict[str, str]]],
) -> JSONResponse:
    """Ejecuta ``action`` una sola vez por llave y devuelve la misma respuesta a los reintentos.

    Si Redis no está disponible, la operación sigue: la restricción única de la llave en la
    base de datos impide duplicados (ADR-003).
    """
    redis_key = f"idem:{scope}:{key}"
    try:
        reservation = store.reserve(redis_key, fingerprint)
    except RedisError:
        log.warning("Redis no disponible; se confía en la restricción única de la base de datos")
        status, body, headers = action()
        return JSONResponse(body, status_code=status, headers=headers)

    if reservation.state is ReservationState.COMPLETED:
        assert reservation.status_code is not None and reservation.body is not None
        return JSONResponse(
            reservation.body,
            status_code=reservation.status_code,
            headers={**(reservation.headers or {}), "Idempotent-Replayed": "true"},
        )
    if reservation.state is ReservationState.IN_PROGRESS:
        raise RequestInProgress()

    try:
        status, body, headers = action()
    except Exception:
        with contextlib.suppress(RedisError):
            store.release(redis_key)
        raise
    try:
        store.complete(redis_key, fingerprint, status, body, headers)
    except RedisError:
        log.warning("No se pudo guardar la respuesta idempotente en Redis")
    return JSONResponse(body, status_code=status, headers=headers)
