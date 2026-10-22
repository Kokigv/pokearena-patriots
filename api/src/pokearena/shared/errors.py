"""Errores de la aplicación y su traducción a application/problem+json (RNF-API-03).

Los módulos lanzan subclases de ``AppError`` desde el dominio o los casos de uso; solo la
capa HTTP decide cómo se serializan.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class FieldError:
    field: str
    reason: str


class AppError(Exception):
    """Error con tipo propio del dominio. ``type`` es el identificador estable del error."""

    def __init__(
        self,
        detail: str,
        errors: list[FieldError] | None = None,
        type: str = "about:blank",
        title: str = "Error",
        status: int = 400,
    ) -> None:
        super().__init__(detail)
        self.detail = detail
        self.errors = errors or []
        self.type = type
        self.title = title
        self.status = status


class ValidationFailed(AppError):
    def __init__(self, errors: list[FieldError], detail: str | None = None) -> None:
        super().__init__(
            detail=detail or "; ".join(f"{e.field}: {e.reason}" for e in errors),
            errors=errors,
            type="validation-error",
            title="Datos inválidos",
            status=422,
        )


class NotAuthenticated(AppError):
    def __init__(self, detail: str = "Debe autenticarse para usar este recurso.") -> None:
        super().__init__(detail=detail, type="unauthenticated", title="No autenticado", status=401)


class TokenExpired(AppError):
    def __init__(self) -> None:
        super().__init__(
            detail="La credencial de acceso expiró; renueve la sesión.",
            type="token-expired",
            title="Credencial expirada",
            status=401,
        )


class Forbidden(AppError):
    def __init__(self, detail: str = "No tiene permiso para realizar esta operación.") -> None:
        super().__init__(detail=detail, type="forbidden", title="Sin permiso", status=403)


class NotFound(AppError):
    def __init__(self, detail: str) -> None:
        super().__init__(detail=detail, type="not-found", title="No encontrado", status=404)


class Conflict(AppError):
    def __init__(self, detail: str, type_: str = "conflict") -> None:
        super().__init__(detail=detail, type=type_, title="Conflicto", status=409)
