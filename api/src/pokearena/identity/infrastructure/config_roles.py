"""Roles asignados por configuración: no existe una pantalla para otorgar el rol de admin."""

from pokearena.identity.domain.principal import Role


class ConfigRoleResolver:
    def __init__(self, admin_subjects: frozenset[str]) -> None:
        self._admins = admin_subjects

    def roles_for(self, subject: str) -> frozenset[Role]:
        if subject in self._admins:
            return frozenset({Role.PLAYER, Role.ADMIN})
        return frozenset({Role.PLAYER})
