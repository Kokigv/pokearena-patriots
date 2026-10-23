"""Caso de uso: Crear carta (US 119)."""

from dataclasses import dataclass

from pokearena.catalog.application.images import ImageService
from pokearena.catalog.application.ports import (
    AbilityRepository,
    CardRepository,
    DuplicateRequest,
)
from pokearena.catalog.domain.ability import evolution_problem
from pokearena.catalog.domain.card import Card, CardDraft
from pokearena.catalog.domain.enums import ImageStatus
from pokearena.catalog.domain.images import CARD_IMAGE
from pokearena.shared.errors import AppError, FieldError, NotFound, ValidationFailed


class AbilityNotFound(AppError):
    def __init__(self, code: str) -> None:
        super().__init__(
            detail=f"La habilidad {code} no existe.",
            errors=[FieldError("ability_code", "la habilidad no existe")],
            type="ability-not-found",
            title="Habilidad inexistente",
            status=422,
        )


@dataclass(frozen=True)
class CreateCardCommand:
    draft: CardDraft
    image: bytes
    idempotency_key: str


class CreateCard:
    def __init__(
        self, cards: CardRepository, abilities: AbilityRepository, images: ImageService
    ) -> None:
        self._cards = cards
        self._abilities = abilities
        self._images = images

    def execute(self, command: CreateCardCommand) -> Card:
        existing = self._cards.find_by_idempotency_key(command.idempotency_key)
        if existing is not None:
            return existing

        ability = self._abilities.get(command.draft.ability_code)
        if ability is None:
            raise AbilityNotFound(command.draft.ability_code)
        problem = evolution_problem(None, ability, self._abilities.ability_of_card)
        if problem:
            raise ValidationFailed([FieldError("ability_code", problem)])

        info = self._images.validate(command.image, CARD_IMAGE)
        stored = self._images.store("cards", command.image, info, CARD_IMAGE)
        try:
            return self._cards.add(command.draft, stored, command.idempotency_key)
        except DuplicateRequest:
            # Otra solicitud con la misma llave ganó la carrera: se devuelve esa carta.
            self._images.discard(stored)
            card = self._cards.find_by_idempotency_key(command.idempotency_key)
            assert card is not None
            return card
        except Exception:
            self._images.discard(stored)
            raise


class RetryCardThumbnail:
    """Regenera la versión pequeña de una carta cuya imagen quedó en FAILED."""

    def __init__(self, cards: CardRepository, images: ImageService) -> None:
        self._cards = cards
        self._images = images

    def execute(self, code: str) -> Card:
        card = self._cards.get(code)
        if card is None:
            raise NotFound(f"La carta {code} no existe.")
        if card.available_to_players:
            return card
        thumb_key = self._images.regenerate(card.image_key, CARD_IMAGE)
        status = ImageStatus.READY if thumb_key else ImageStatus.FAILED
        return self._cards.update_thumbnail(code, thumb_key, status)
