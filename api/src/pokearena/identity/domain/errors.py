"""Errores del inicio de sesión con proveedor (US 116)."""

from pokearena.shared.errors import AppError


class InvalidProviderToken(AppError):
    """El token no lo emitió el proveedor, expiró, tiene firma inválida o es de otra app."""

    def __init__(self, reason: str) -> None:
        super().__init__(
            detail=f"El token del proveedor de identidad no es válido: {reason}.",
            type="invalid-provider-token",
            title="Token del proveedor inválido",
            status=401,
        )


class ProviderUnavailable(AppError):
    def __init__(self, provider: str, detail: str | None = None) -> None:
        super().__init__(
            detail=detail
            or (
                f"El proveedor de identidad ({provider}) no está disponible en este momento. "
                "Intente iniciar sesión de nuevo en unos minutos."
            ),
            type="identity-provider-unavailable",
            title="Proveedor de identidad no disponible",
            status=503,
        )
