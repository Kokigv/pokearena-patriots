"""Casos de uso de autenticación: emitir y validar credenciales propias de PokéArena.

La API solo confía en credenciales que ella misma emite (RNF-SEG-01). En el Sprint 1 la
única forma de obtener una es el emisor de desarrollo; en el Sprint 2 el inicio de sesión
con Google usará el mismo ``TokenCodec`` sin cambiar cómo se autorizan las solicitudes.
"""

from dataclasses import dataclass
from typing import Protocol

from pokearena.identity.domain.principal import Principal, Role
from pokearena.shared.errors import Forbidden


@dataclass(frozen=True)
class IssuedToken:
    access_token: str
    expires_in: int
    token_type: str = "Bearer"


class TokenCodec(Protocol):
    def issue(self, subject: str) -> IssuedToken: ...

    def subject_of(self, token: str) -> str:
        """Devuelve el sujeto del token o lanza NotAuthenticated / TokenExpired."""
        ...


class RoleResolver(Protocol):
    def roles_for(self, subject: str) -> frozenset[Role]: ...


class AuthenticationService:
    def __init__(self, codec: TokenCodec, roles: RoleResolver) -> None:
        self._codec = codec
        self._roles = roles

    def authenticate(self, token: str) -> Principal:
        subject = self._codec.subject_of(token)
        return Principal(subject=subject, roles=self._roles.roles_for(subject))

    def issue_test_token(self, subject: str) -> IssuedToken:
        return self._codec.issue(subject)


def ensure_admin(principal: Principal) -> Principal:
    if not principal.is_admin:
        raise Forbidden("Esta operación requiere el rol de administrador.")
    return principal
