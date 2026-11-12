"""Roles asignados por configuración: no existe una pantalla para otorgar el rol de admin."""

from pokearena.identity.domain.player import ExternalIdentity
from pokearena.identity.domain.principal import Role


class ConfigRoleResolver:
    """Todo jugador tiene el rol de jugador. Es administrador si su sujeto del proveedor o su
    correo aparece en ``ADMIN_SUBJECTS``."""

    def __init__(self, admin_subjects: frozenset[str]) -> None:
        self._admins = frozenset(s.lower() for s in admin_subjects)

    def roles_for(self, identity: ExternalIdentity) -> frozenset[Role]:
        keys = {identity.subject.lower()}
        if identity.email:
            keys.add(identity.email.lower())
        if keys & self._admins:
            return frozenset({Role.PLAYER, Role.ADMIN})
        return frozenset({Role.PLAYER})
