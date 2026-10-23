"""Identidad de quien hace una solicitud."""

from dataclasses import dataclass
from enum import StrEnum


class Role(StrEnum):
    PLAYER = "player"
    ADMIN = "admin"


@dataclass(frozen=True)
class Principal:
    subject: str
    roles: frozenset[Role]

    @property
    def is_admin(self) -> bool:
        return Role.ADMIN in self.roles
