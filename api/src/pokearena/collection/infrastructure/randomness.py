"""Generador aleatorio del servidor (adaptador del puerto ``RandomSource``)."""

import secrets
from collections.abc import Sequence


class SystemRandomSource:
    """Usa el generador criptográfico del sistema: el cliente no puede predecir ni influir en
    las cartas que recibe."""

    def __init__(self) -> None:
        self._rng = secrets.SystemRandom()

    def sample(self, population: Sequence[str], k: int) -> list[str]:
        return self._rng.sample(list(population), k)
