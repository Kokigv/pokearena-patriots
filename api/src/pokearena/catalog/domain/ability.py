"""Habilidades de las cartas.

En el Sprint 1 solo se consultan (la US Crear habilidad es del Sprint 2), pero las reglas que
afectan a Crear carta viven aquí: la habilidad es obligatoria y una evolución no puede apuntar
a la misma carta ni formar ciclos.
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any

from pokearena.catalog.domain.enums import CardType, EffectKind, Trigger

NO_ABILITY_CODE = "HAB-000"


@dataclass(frozen=True)
class Ability:
    code: str
    name: str
    trigger: Trigger
    effect: EffectKind
    target: str | None = None
    affected_type: CardType | None = None  # None = Todos
    condition: Mapping[str, Any] = field(default_factory=dict)
    params: Mapping[str, Any] = field(default_factory=dict)
    evolution_target: str | None = None

    @property
    def is_evolution(self) -> bool:
        return self.effect is EffectKind.EVOLUCIONAR


def evolution_problem(
    card_code: str | None,
    ability: Ability,
    ability_of_card: Callable[[str], Ability | None],
) -> str | None:
    """Devuelve el motivo si asignar ``ability`` a ``card_code`` rompe las reglas de evolución.

    Sigue la cadena de evoluciones desde la carta destino. ``card_code`` es None cuando la
    carta aún no tiene código (se está creando); entonces solo se detectan ciclos previos.
    """
    if not ability.is_evolution or ability.evolution_target is None:
        return None
    if card_code is not None and ability.evolution_target == card_code:
        return "una carta no puede evolucionar en sí misma"
    seen: set[str] = set() if card_code is None else {card_code}
    current: str | None = ability.evolution_target
    while current is not None:
        if current in seen:
            return "las evoluciones forman un ciclo entre cartas"
        seen.add(current)
        next_ability = ability_of_card(current)
        current = (
            next_ability.evolution_target
            if next_ability is not None and next_ability.is_evolution
            else None
        )
    return None
