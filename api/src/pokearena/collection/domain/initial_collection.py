"""Reglas de la colección inicial (US 123). Dominio puro: no conoce la base de datos ni el azar
real; el generador aleatorio llega como puerto (D-05)."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol

INITIAL_CARD_COUNT = 15
INITIAL_CUBES = 1_000
DECK_SIZE = 12
INITIAL_GRANT_REASON = "INITIAL_GRANT"


class RandomSource(Protocol):
    def sample(self, population: Sequence[str], k: int) -> list[str]:
        """``k`` elementos distintos de ``population`` elegidos al azar."""
        ...


class NotEnoughCommonCards(Exception):
    def __init__(self, available: int) -> None:
        super().__init__(f"hay {available} cartas Comunes y se necesitan {INITIAL_CARD_COUNT}")
        self.available = available


@dataclass(frozen=True)
class InitialGrant:
    """Lo que recibe un jugador nuevo: 15 cartas Comunes distintas y 1,000 cubos."""

    card_codes: tuple[str, ...]
    cubes: int = INITIAL_CUBES


def choose_initial_grant(common_codes: Sequence[str], random: RandomSource) -> InitialGrant:
    """Elige en el servidor 15 cartas Comunes distintas. Ningún dato del cliente interviene.

    Con 15 cartas distintas siempre es posible armar un deck válido de 12 (US 125).
    """
    distinct = sorted(set(common_codes))
    if len(distinct) < INITIAL_CARD_COUNT:
        raise NotEnoughCommonCards(len(distinct))
    chosen = random.sample(distinct, INITIAL_CARD_COUNT)
    assert len(set(chosen)) == INITIAL_CARD_COUNT >= DECK_SIZE
    return InitialGrant(card_codes=tuple(chosen))
