"""Guardado de la imagen original y generación de la versión pequeña (ADR-002)."""

import logging
import uuid

from pokearena.catalog.application.ports import ImageProcessor, ImageStorage, StoredImages
from pokearena.catalog.domain.enums import ImageStatus
from pokearena.catalog.domain.images import ImageInfo, ImageSpec, size_error, validate_image
from pokearena.shared.errors import ValidationFailed

log = logging.getLogger(__name__)

THUMBNAIL_ATTEMPTS = 3
_CONTENT_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
_EXTENSIONS = {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}


class ImageService:
    def __init__(self, processor: ImageProcessor, storage: ImageStorage) -> None:
        self._processor = processor
        self._storage = storage

    def validate(self, data: bytes, spec: ImageSpec) -> ImageInfo:
        too_big = size_error(len(data))
        if too_big:  # se revisa antes de decodificar para no procesar archivos enormes
            raise ValidationFailed([too_big])
        info = self._processor.inspect(data)
        errors = validate_image(info, spec)
        if errors:
            raise ValidationFailed(errors)
        return info

    def store(self, folder: str, data: bytes, info: ImageInfo, spec: ImageSpec) -> StoredImages:
        assert info.format is not None
        base = f"{folder}/{uuid.uuid4().hex}"
        image_key = f"{base}.{_EXTENSIONS[info.format]}"
        self._storage.put(image_key, data, _CONTENT_TYPES[info.format])
        thumb_key = self.make_thumbnail(image_key, data, spec)
        status = ImageStatus.READY if thumb_key else ImageStatus.FAILED
        return StoredImages(image_key, thumb_key, status)

    def make_thumbnail(self, image_key: str, data: bytes, spec: ImageSpec) -> str | None:
        """Genera la versión pequeña con reintentos. Devuelve None si no se pudo."""
        thumb_key = image_key.rsplit(".", 1)[0] + "_small.webp"
        for attempt in range(1, THUMBNAIL_ATTEMPTS + 1):
            try:
                thumb = self._processor.thumbnail(data, spec.thumb_width, spec.thumb_height)
                self._storage.put(thumb_key, thumb, "image/webp")
                return thumb_key
            except Exception:  # noqa: BLE001 - cualquier falla deja la imagen en FAILED
                log.exception("Falló la miniatura de %s (intento %d)", image_key, attempt)
        return None

    def regenerate(self, image_key: str, spec: ImageSpec) -> str | None:
        data, _ = self._storage.get(image_key)
        return self.make_thumbnail(image_key, data, spec)

    def discard(self, images: StoredImages) -> None:
        for key in (images.image_key, images.thumb_key):
            if key:
                try:
                    self._storage.delete(key)
                except Exception:  # noqa: BLE001
                    log.warning("No se pudo borrar la imagen huérfana %s", key)
