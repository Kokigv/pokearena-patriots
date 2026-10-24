"""Caso de uso: listar las habilidades disponibles para el formulario de carta."""

from pokearena.catalog.application.ports import AbilityRepository
from pokearena.catalog.domain.ability import Ability


class ListAbilities:
    def __init__(self, abilities: AbilityRepository) -> None:
        self._abilities = abilities

    def execute(self) -> list[Ability]:
        return self._abilities.list_all()
