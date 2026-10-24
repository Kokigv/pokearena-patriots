"""Puertos (interfaces) que el catálogo necesita del exterior. Los implementa infrastructure/."""

from dataclasses import dataclass
from typing import Protocol

from pokearena.catalog.domain.ability import Ability
from pokearena.catalog.domain.card import Card, CardDraft
from pokearena.catalog.domain.enums import ImageStatus
from pokearena.catalog.domain.images import ImageInfo
from pokearena.catalog.domain.location import Location, LocationDraft


@dataclass(frozen=True)
class StoredImages:
    image_key: str
    thumb_key: str | None
    status: ImageStatus


class ImageProcessor(Protocol):
    def inspect(self, data: bytes) -> ImageInfo: ...

    def thumbnail(self, data: bytes, width: int, height: int) -> bytes: ...


class ImageStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> tuple[bytes, str]: ...

    def delete(self, key: str) -> None: ...


class AbilityRepository(Protocol):
    def get(self, code: str) -> Ability | None: ...

    def ability_of_card(self, card_code: str) -> Ability | None: ...

    def list_all(self) -> list[Ability]: ...


class CardRepository(Protocol):
    def find_by_idempotency_key(self, key: str) -> Card | None: ...

    def add(self, draft: CardDraft, images: StoredImages, idempotency_key: str) -> Card:
        """Asigna el siguiente código del tipo y guarda la carta en una sola transacción.

        Lanza ``DuplicateRequest`` si la llave de idempotencia ya existe.
        """
        ...

    def get(self, code: str) -> Card | None: ...

    def update_thumbnail(self, code: str, thumb_key: str | None, status: ImageStatus) -> Card: ...


class LocationRepository(Protocol):
    def find_by_idempotency_key(self, key: str) -> Location | None: ...

    def add(self, draft: LocationDraft, images: StoredImages, idempotency_key: str) -> Location: ...

    def get(self, location_id: str) -> Location | None: ...

    def update_thumbnail(
        self, location_id: str, thumb_key: str | None, status: ImageStatus
    ) -> Location: ...


class DuplicateRequest(Exception):
    """La llave de idempotencia ya fue usada para crear un registro."""
