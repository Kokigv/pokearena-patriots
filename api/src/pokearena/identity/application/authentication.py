"""Casos de uso de autenticación: emitir y validar credenciales propias de PokéArena.

La API solo confía en credenciales que ella misma emite (RNF-SEG-01). El token del proveedor
(Google) se valida una sola vez, al iniciar sesión; después todas las solicitudes se autorizan
con el JWT de PokéArena, sin importar con qué proveedor entró el jugador.
"""

from dataclasses import dataclass
from typing import Protocol

from pokearena.identity.domain.player import ExternalIdentity
from pokearena.identity.domain.principal import Principal, Role
from pokearena.shared.errors import Forbidden


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_in: int
    token_type: str = "Bearer"


@dataclass(frozen=True)
class TokenClaims:
    subject: str
    roles: frozenset[Role]


class TokenCodec(Protocol):
    def issue(self, subject: str, roles: frozenset[Role]) -> IssuedToken: ...

    def decode(self, token: str) -> TokenClaims:
        """Devuelve el sujeto y los roles del token o lanza NotAuthenticated / TokenExpired."""
        ...


class RoleResolver(Protocol):
    def roles_for(self, identity: ExternalIdentity) -> frozenset[Role]: ...


class AuthenticationService:
    """Valida las credenciales de PokéArena en cada solicitud (sin ir a la base de datos)."""

    def __init__(self, codec: TokenCodec) -> None:
        self._codec = codec

    def authenticate(self, token: str) -> Principal:
        claims = self._codec.decode(token)
        return Principal(subject=claims.subject, roles=claims.roles)


def ensure_admin(principal: Principal) -> Principal:
    if not principal.is_admin:
        raise Forbidden("Esta operación requiere el rol de administrador.")
    return principal
