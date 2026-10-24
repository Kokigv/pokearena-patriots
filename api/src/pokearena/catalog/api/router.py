"""Rutas HTTP del catálogo: Crear carta."""

from typing import Any

from fastapi import APIRouter, Depends, File, Form, Header, UploadFile
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, Response

from pokearena.catalog.api import wiring
from pokearena.catalog.api.idempotent import require_key, run_idempotent
from pokearena.catalog.api.schemas import AbilityOut, CardOut
from pokearena.catalog.application.create_card import (
    CreateCard,
    CreateCardCommand,
    RetryCardThumbnail,
)
from pokearena.catalog.application.ports import ImageStorage
from pokearena.catalog.application.search_cards import ListAbilities
from pokearena.catalog.domain.card import CardDraft
from pokearena.catalog.domain.images import MAX_BYTES
from pokearena.catalog.infrastructure.sql_repositories import (
    SqlAbilityRepository,
    SqlCardRepository,
)
from pokearena.identity.api.dependencies import require_admin
from pokearena.identity.domain.principal import Principal
from pokearena.shared.errors import FieldError, NotFound, ValidationFailed
from pokearena.shared.idempotency import IdempotencyStore, fingerprint

router = APIRouter(prefix="/v1", tags=["Catálogo"])
images_router = APIRouter(prefix="/v1", tags=["Imágenes"])


def _as_int(value: str | None) -> Any:
    """Convierte un campo de formulario a entero; si no se puede, deja el valor original
    para que el dominio reporte el campo inválido."""
    if value is None:
        return None
    try:
        return int(value.strip())
    except ValueError:
        return value


def _read_image(image: UploadFile | None) -> bytes:
    if image is None:
        raise ValidationFailed([FieldError("image", "la imagen es obligatoria")])
    return image.file.read(MAX_BYTES + 1)


# ---------------------------------------------------------------- Cartas


@router.post(
    "/cards",
    status_code=201,
    response_model=CardOut,
    summary="Crear carta",
    responses={401: {}, 403: {}, 409: {}, 422: {}},
)
def create_card(
    name: str | None = Form(None),
    cost: str | None = Form(None),
    power: str | None = Form(None),
    type: str | None = Form(None),
    rarity: str | None = Form(None),
    ability_code: str | None = Form(None),
    image: UploadFile | None = File(None),
    idempotency_key: str | None = Header(None, alias="Idempotency-Key"),
    admin: Principal = Depends(require_admin),
    use_case: CreateCard = Depends(wiring.create_card_uc),
    abilities: SqlAbilityRepository = Depends(wiring.ability_repository),
    store: IdempotencyStore = Depends(wiring.get_idempotency_store),
) -> JSONResponse:
    key = require_key(idempotency_key)
    draft = CardDraft.parse(name, _as_int(cost), _as_int(power), type, rarity, ability_code)
    data = _read_image(image)
    fp = fingerprint(admin.subject, repr(draft), data)

    def action() -> tuple[int, dict[str, Any], dict[str, str]]:
        card = use_case.execute(CreateCardCommand(draft, data, key))
        body = jsonable_encoder(CardOut.of(card, abilities.get(card.ability_code)))
        return 201, body, {"Location": f"/v1/cards/{card.code}"}

    return run_idempotent(store, "cards", key, fp, action)


@router.get("/cards/{code}", response_model=CardOut, summary="Ficha de una carta")
def get_card(
    code: str,
    cards: SqlCardRepository = Depends(wiring.card_repository),
    abilities: SqlAbilityRepository = Depends(wiring.ability_repository),
) -> CardOut:
    card = cards.get(code.upper())
    if card is None:
        raise NotFound(f"La carta {code} no existe.")
    return CardOut.of(card, abilities.get(card.ability_code))


@router.post(
    "/cards/{code}/image/retry",
    response_model=CardOut,
    summary="Reintentar la versión pequeña de la imagen",
)
def retry_card_image(
    code: str,
    use_case: RetryCardThumbnail = Depends(wiring.retry_card_thumbnail_uc),
    abilities: SqlAbilityRepository = Depends(wiring.ability_repository),
) -> CardOut:
    card = use_case.execute(code.upper())
    return CardOut.of(card, abilities.get(card.ability_code))


@router.get("/abilities", response_model=list[AbilityOut], summary="Habilidades disponibles")
def list_abilities(use_case: ListAbilities = Depends(wiring.list_abilities_uc)) -> list[AbilityOut]:
    return [AbilityOut.of(a) for a in use_case.execute()]


# ---------------------------------------------------------------- Imágenes


@images_router.get("/images/{key:path}", summary="Descargar una imagen")
def get_image(key: str, storage: ImageStorage = Depends(wiring.get_image_storage)) -> Response:
    data, content_type = storage.get(key)
    return Response(
        data, media_type=content_type, headers={"Cache-Control": "public, max-age=86400"}
    )
