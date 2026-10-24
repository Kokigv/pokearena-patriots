"""Procesamiento de imágenes con Pillow."""

import io

from PIL import Image, ImageOps, UnidentifiedImageError

from pokearena.catalog.domain.images import ImageInfo

Image.MAX_IMAGE_PIXELS = 40_000_000  # protege contra imágenes "bomba" de descompresión


class PillowImageProcessor:
    def inspect(self, data: bytes) -> ImageInfo:
        try:
            with Image.open(io.BytesIO(data)) as img:
                img.verify()
            with Image.open(io.BytesIO(data)) as img:
                return ImageInfo(img.format, len(data), img.width, img.height)
        except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
            return ImageInfo(None, len(data), 0, 0)

    def thumbnail(self, data: bytes, width: int, height: int) -> bytes:
        with Image.open(io.BytesIO(data)) as img:
            small = ImageOps.fit(img.convert("RGBA"), (width, height), Image.Resampling.LANCZOS)
            out = io.BytesIO()
            small.save(out, format="WEBP", quality=85)
            return out.getvalue()
