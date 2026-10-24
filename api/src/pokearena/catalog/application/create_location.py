"""Caso de uso: Crear ubicación (US 122)."""

from dataclasses import dataclass

from pokearena.catalog.application.images import ImageService
from pokearena.catalog.application.ports import DuplicateRequest, LocationRepository
from pokearena.catalog.domain.enums import ImageStatus
from pokearena.catalog.domain.images import LOCATION_IMAGE
from pokearena.catalog.domain.location import Location, LocationDraft
from pokearena.shared.errors import NotFound


@dataclass(frozen=True)
class CreateLocationCommand:
    draft: LocationDraft
    image: bytes
    idempotency_key: str


class CreateLocation:
    def __init__(self, locations: LocationRepository, images: ImageService) -> None:
        self._locations = locations
        self._images = images

    def execute(self, command: CreateLocationCommand) -> Location:
        existing = self._locations.find_by_idempotency_key(command.idempotency_key)
        if existing is not None:
            return existing
        info = self._images.validate(command.image, LOCATION_IMAGE)
        stored = self._images.store("locations", command.image, info, LOCATION_IMAGE)
        try:
            return self._locations.add(command.draft, stored, command.idempotency_key)
        except DuplicateRequest:
            self._images.discard(stored)
            location = self._locations.find_by_idempotency_key(command.idempotency_key)
            assert location is not None
            return location
        except Exception:
            self._images.discard(stored)
            raise


class RetryLocationThumbnail:
    def __init__(self, locations: LocationRepository, images: ImageService) -> None:
        self._locations = locations
        self._images = images

    def execute(self, location_id: str) -> Location:
        location = self._locations.get(location_id)
        if location is None:
            raise NotFound(f"La ubicación {location_id} no existe.")
        if location.assignable_to_matches:
            return location
        thumb_key = self._images.regenerate(location.image_key, LOCATION_IMAGE)
        status = ImageStatus.READY if thumb_key else ImageStatus.FAILED
        return self._locations.update_thumbnail(location_id, thumb_key, status)
