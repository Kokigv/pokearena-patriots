"""Reglas de las imágenes de cartas y ubicaciones."""

from dataclasses import dataclass

from pokearena.shared.errors import FieldError

ALLOWED_FORMATS = frozenset({"PNG", "JPEG", "WEBP"})
MAX_BYTES = 5 * 1024 * 1024
RATIO_TOLERANCE = 0.01


@dataclass(frozen=True)
class ImageInfo:
    format: str | None
    size_bytes: int
    width: int
    height: int


@dataclass(frozen=True)
class ImageSpec:
    ratio_w: int
    ratio_h: int
    min_width: int
    min_height: int
    thumb_width: int
    thumb_height: int

    @property
    def ratio_label(self) -> str:
        return f"{self.ratio_w}:{self.ratio_h}"


CARD_IMAGE = ImageSpec(5, 7, 600, 840, 200, 280)
LOCATION_IMAGE = ImageSpec(4, 3, 800, 600, 320, 240)


def size_error(size_bytes: int, field: str = "image") -> FieldError | None:
    if size_bytes > MAX_BYTES:
        return FieldError(field, "la imagen supera el máximo de 5 MB")
    return None


def validate_image(info: ImageInfo, spec: ImageSpec, field: str = "image") -> list[FieldError]:
    errors: list[FieldError] = []
    if info.format not in ALLOWED_FORMATS:
        errors.append(FieldError(field, "formato no permitido; use PNG, JPG o WebP"))
    too_big = size_error(info.size_bytes, field)
    if too_big:
        errors.append(too_big)
    expected_h = info.width * spec.ratio_h / spec.ratio_w
    if info.height <= 0 or abs(info.height - expected_h) / info.height > RATIO_TOLERANCE:
        errors.append(FieldError(field, f"la proporción debe ser {spec.ratio_label}"))
    if info.width < spec.min_width or info.height < spec.min_height:
        errors.append(
            FieldError(
                field, f"la resolución mínima es {spec.min_width} × {spec.min_height} píxeles"
            )
        )
    return errors
