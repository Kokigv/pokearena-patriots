"""Cuenta del jugador y la identidad externa con la que inicia sesión (US 116)."""

from dataclasses import dataclass
from datetime import datetime

from pokearena.identity.domain.principal import Role

INITIAL_ELO = 0


@dataclass(frozen=True)
class ExternalIdentity:
    """Identidad ya verificada por un proveedor (Google, o el emisor de prueba).

    La cuenta se asocia a ``(provider, subject)``, nunca al correo: si el jugador cambia su
    correo en el proveedor conserva la misma cuenta en PokéArena.
    """

    provider: str
    subject: str
    email: str | None
    display_name: str | None
    is_test: bool = False


@dataclass(frozen=True)
class Player:
    id: str
    display_name: str
    email: str | None
    role: Role
    elo: int
    is_test: bool
    created_at: datetime


def display_name_for(identity: ExternalIdentity) -> str:
    """Nombre visible inicial: el del proveedor, o la parte local del correo, o el sujeto."""
    if identity.display_name and identity.display_name.strip():
        return identity.display_name.strip()[:60]
    if identity.email:
        return identity.email.split("@", 1)[0][:60]
    return identity.subject[:60]
