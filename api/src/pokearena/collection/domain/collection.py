"""Colección de un jugador: cartas que posee, copias y saldo de cubos."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True)
class OwnedCard:
    card_code: str
    copies: int


@dataclass(frozen=True)
class CubeMovement:
    amount: int
    reason: str
    balance_after: int
    created_at: datetime


@dataclass(frozen=True)
class CollectionSummary:
    player_id: str
    initial_granted: bool
    cubes: int
    cards: list[OwnedCard] = field(default_factory=list)
    movements: list[CubeMovement] = field(default_factory=list)

    @property
    def distinct_cards(self) -> int:
        return len(self.cards)
