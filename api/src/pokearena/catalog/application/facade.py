"""Fachada pública del catálogo para otros módulos (ADR-001, regla de dependencia 2).

El módulo Colección consulta cartas solo a través de esta clase: nunca lee las tablas del
catálogo ni importa sus adaptadores. Devuelve objetos propios de la fachada (``CatalogCard``)
para que los cambios internos del catálogo no se filtren a otros módulos.
"""

from dataclasses import dataclass, replace

from pokearena.catalog.application.ports import AbilityRepository, CardRepository
from pokearena.catalog.domain.ability import Ability
from pokearena.catalog.domain.card import Card
from pokearena.catalog.domain.enums import Rarity
from pokearena.catalog.domain.search import SearchCriteria, encode_cursor, parse_criteria


@dataclass(frozen=True)
class CatalogAbility:
    code: str
    name: str
    trigger: str
    effect: str


@dataclass(frozen=True)
class CatalogCard:
    code: str
    name: str
    cost: int
    power: int
    type: str
    rarity: str
    image_key: str
    ability: CatalogAbility | None


@dataclass(frozen=True)
class CatalogPage:
    items: list[CatalogCard]
    next_cursor: str | None


@dataclass(frozen=True)
class BrowseFilters:
    """Filtros que un jugador puede usar al explorar el catálogo (US 124), ya validados."""

    criteria: SearchCriteria

    @property
    def cache_key(self) -> str:
        return repr(self.criteria)


def parse_browse_filters(
    *,
    type: str | None = None,
    cost: int | None = None,
    cost_min: int | None = None,
    cost_max: int | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> BrowseFilters:
    """Valida los filtros del jugador. Lanza ``ValidationFailed`` indicando los valores
    permitidos (tipo inexistente, costo fuera de 0–10, paginación inválida)."""
    return BrowseFilters(
        parse_criteria(
            type=type, cost=cost, cost_min=cost_min, cost_max=cost_max, cursor=cursor, limit=limit
        )
    )


def _ability(ability: Ability | None) -> CatalogAbility | None:
    if ability is None:
        return None
    return CatalogAbility(ability.code, ability.name, ability.trigger.value, ability.effect.value)


class CatalogFacade:
    def __init__(self, cards: CardRepository, abilities: AbilityRepository) -> None:
        self._cards = cards
        self._abilities = abilities

    def playable_common_codes(self) -> list[str]:
        """Cartas Comunes que un jugador puede recibir (con imagen lista)."""
        return self._cards.playable_codes(Rarity.COMUN)

    def browse(self, filters: BrowseFilters, only_codes: frozenset[str] | None) -> CatalogPage:
        """Una página de cartas visibles para jugadores, opcionalmente limitada a ``only_codes``.

        Paginación por cursor (keyset) ordenada por (tipo, consecutivo): acotada aunque el
        catálogo tenga 10.000 cartas.
        """
        criteria = replace(filters.criteria, codes=only_codes, playable_only=True)
        rows = self._cards.search(criteria)
        has_more = len(rows) > criteria.limit
        page = rows[: criteria.limit]
        by_code = {a.code: a for a in self._abilities.list_all()}
        return CatalogPage(
            items=[self._view(card, by_code.get(card.ability_code)) for card in page],
            next_cursor=encode_cursor(page[-1].code) if has_more and page else None,
        )

    @staticmethod
    def _view(card: Card, ability: Ability | None) -> CatalogCard:
        return CatalogCard(
            code=card.code,
            name=card.name,
            cost=card.cost,
            power=card.power,
            type=card.type.value,
            rarity=card.rarity.value,
            image_key=card.image_key,
            ability=_ability(ability),
        )
