"""Llaves de idempotencia para operaciones que el cliente puede reintentar (RNF-INT-01).

El almacén en Redis evita que dos solicitudes con la misma llave se procesen a la vez y
devuelve la respuesta guardada a los reintentos. No es la única defensa: las tablas guardan
la llave con una restricción única, así que perder Redis nunca duplica un registro
(RNF-DIS-04, ADR-003).
"""

import hashlib
import json
from dataclasses import dataclass
from enum import Enum
from typing import Any, Protocol

from pokearena.shared.errors import AppError, Conflict

PROCESSING = "__processing__"


class ReservationState(Enum):
    NEW = "new"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


@dataclass(frozen=True)
class Reservation:
    state: ReservationState
    status_code: int | None = None
    body: dict[str, Any] | None = None
    headers: dict[str, str] | None = None


class IdempotencyStore(Protocol):
    def reserve(self, key: str, fingerprint: str) -> Reservation: ...

    def complete(
        self,
        key: str,
        fingerprint: str,
        status_code: int,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> None: ...

    def release(self, key: str) -> None: ...


class IdempotencyKeyReused(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="La llave de idempotencia ya se usó con una solicitud distinta.",
            type="idempotency-key-reused",
            title="Llave de idempotencia reutilizada",
            status=422,
        )


class RequestInProgress(Conflict):
    def __init__(self) -> None:
        super().__init__(
            "Una solicitud con la misma llave de idempotencia se está procesando; reintente.",
            type_="request-in-progress",
        )


def fingerprint(*parts: bytes | str | None) -> str:
    digest = hashlib.sha256()
    for part in parts:
        data = part.encode() if isinstance(part, str) else (part or b"")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


class RedisIdempotencyStore:
    def __init__(self, client: Any, ttl_seconds: int) -> None:
        self._redis = client
        self._ttl = ttl_seconds

    def reserve(self, key: str, fingerprint: str) -> Reservation:
        reserved = self._redis.set(
            key, json.dumps({"state": PROCESSING, "fp": fingerprint}), nx=True, ex=self._ttl
        )
        if reserved:
            return Reservation(ReservationState.NEW)
        raw = self._redis.get(key)
        if raw is None:  # expiró entre el SET y el GET: se vuelve a intentar
            return self.reserve(key, fingerprint)
        stored = json.loads(raw)
        if stored["fp"] != fingerprint:
            raise IdempotencyKeyReused()
        if stored["state"] == PROCESSING:
            return Reservation(ReservationState.IN_PROGRESS)
        return Reservation(
            ReservationState.COMPLETED, stored["status"], stored["body"], stored.get("headers", {})
        )

    def complete(
        self,
        key: str,
        fingerprint: str,
        status_code: int,
        body: dict[str, Any],
        headers: dict[str, str],
    ) -> None:
        value = {
            "state": "done",
            "fp": fingerprint,
            "status": status_code,
            "body": body,
            "headers": headers,
        }
        self._redis.set(key, json.dumps(value), ex=self._ttl)

    def release(self, key: str) -> None:
        self._redis.delete(key)
