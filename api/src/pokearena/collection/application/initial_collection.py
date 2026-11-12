"""Caso de uso: Recibir colección inicial (US 123).

Se ejecuta en cada ingreso del jugador. Si ya la recibió no hace nada; si todavía no hay
suficientes cartas Comunes o la entrega falla, el jugador ingresa igual y se reintenta en el
siguiente ingreso.
"""

import logging
from enum import StrEnum

from pokearena.collection.application.ports import CatalogReader, CollectionRepository
from pokearena.collection.domain.initial_collection import (
    INITIAL_CARD_COUNT,
    NotEnoughCommonCards,
    RandomSource,
    choose_initial_grant,
)

log = logging.getLogger(__name__)


class GrantOutcome(StrEnum):
    GRANTED = "GRANTED"  # se entregó en esta llamada
    ALREADY_GRANTED = "ALREADY_GRANTED"
    NOT_ENOUGH_CARDS = "NOT_ENOUGH_CARDS"
    FAILED = "FAILED"


NOT_AVAILABLE_MESSAGE = (
    "El juego aún no está disponible: el catálogo todavía no tiene las "
    f"{INITIAL_CARD_COUNT} cartas Comunes necesarias para tu colección inicial. "
    "La recibirás automáticamente en un próximo ingreso."
)
FAILED_MESSAGE = (
    "No pudimos entregar tu colección inicial en este momento. No se entregó nada a medias; "
    "la recibirás completa en tu próximo ingreso."
)


class GrantInitialCollection:
    def __init__(
        self, catalog: CatalogReader, collection: CollectionRepository, random: RandomSource
    ) -> None:
        self._catalog = catalog
        self._collection = collection
        self._random = random

    def execute(self, player_id: str) -> GrantOutcome:
        if self._collection.has_initial_grant(player_id):
            return GrantOutcome.ALREADY_GRANTED
        try:
            grant = choose_initial_grant(self._catalog.playable_common_codes(), self._random)
        except NotEnoughCommonCards as exc:
            log.info("Colección inicial pendiente para %s: %s", player_id, exc)
            return GrantOutcome.NOT_ENOUGH_CARDS
        try:
            granted = self._collection.grant_initial(player_id, grant)
        except Exception:
            # La transacción ya se deshizo: ni cartas ni cubos. Se reintenta al volver a entrar.
            log.exception("Falló la entrega de la colección inicial de %s", player_id)
            return GrantOutcome.FAILED
        return GrantOutcome.GRANTED if granted else GrantOutcome.ALREADY_GRANTED
