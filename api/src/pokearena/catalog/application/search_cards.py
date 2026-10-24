"""Caso de uso: Buscar carta (US 120)."""

from dataclasses import dataclass

from pokearena.catalog.application.ports import AbilityRepository, CardRepository
from pokearena.catalog.domain.ability import Ability
from pokearena.catalog.domain.card import Card
from pokearena.catalog.domain.search import SearchCriteria, encode_cursor


@dataclass(frozen=True)
class CardPage:
    items: list[Card]
    next_cursor: str | None


class SearchCards:
    def __init__(self, cards: CardRepository) -> None:
        self._cards = cards

    def execute(self, criteria: SearchCriteria) -> CardPage:
        rows = self._cards.search(criteria)
        has_more = len(rows) > criteria.limit
        items = rows[: criteria.limit]
        next_cursor = encode_cursor(items[-1].code) if has_more and items else None
        return CardPage(items, next_cursor)


class ListAbilities:
    def __init__(self, abilities: AbilityRepository) -> None:
        self._abilities = abilities

    def execute(self) -> list[Ability]:
        return self._abilities.list_all()
