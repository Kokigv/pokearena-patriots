"""Construcción de los casos de uso con sus adaptadores (inyección de dependencias)."""

from functools import lru_cache

import boto3
from fastapi import Depends
from redis import Redis
from sqlalchemy.orm import Session

from pokearena.catalog.application.create_card import CreateCard, RetryCardThumbnail
from pokearena.catalog.application.create_location import (
    CreateLocation,
    RetryLocationThumbnail,
)
from pokearena.catalog.application.images import ImageService
from pokearena.catalog.application.ports import ImageStorage
from pokearena.catalog.application.search_cards import ListAbilities, SearchCards
from pokearena.catalog.infrastructure.pillow_images import PillowImageProcessor
from pokearena.catalog.infrastructure.sql_repositories import (
    SqlAbilityRepository,
    SqlCardRepository,
    SqlLocationRepository,
)
from pokearena.catalog.infrastructure.storage import LocalImageStorage, S3ImageStorage
from pokearena.identity.api.dependencies import require_admin
from pokearena.identity.domain.principal import Principal
from pokearena.shared.config import get_settings
from pokearena.shared.db import get_session
from pokearena.shared.idempotency import IdempotencyStore, RedisIdempotencyStore


@lru_cache
def get_image_storage() -> ImageStorage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
        )
        return S3ImageStorage(client, settings.s3_bucket)
    return LocalImageStorage(settings.storage_local_path)


@lru_cache
def get_idempotency_store() -> IdempotencyStore:
    settings = get_settings()
    return RedisIdempotencyStore(
        Redis.from_url(settings.redis_url), settings.idempotency_ttl_seconds
    )


def get_image_service(storage: ImageStorage = Depends(get_image_storage)) -> ImageService:
    return ImageService(PillowImageProcessor(), storage)


def create_card_uc(
    session: Session = Depends(get_session),
    admin: Principal = Depends(require_admin),
    images: ImageService = Depends(get_image_service),
) -> CreateCard:
    return CreateCard(
        SqlCardRepository(session, admin.subject), SqlAbilityRepository(session), images
    )


def retry_card_thumbnail_uc(
    session: Session = Depends(get_session),
    _: Principal = Depends(require_admin),
    images: ImageService = Depends(get_image_service),
) -> RetryCardThumbnail:
    return RetryCardThumbnail(SqlCardRepository(session), images)


def search_cards_uc(
    session: Session = Depends(get_session), _: Principal = Depends(require_admin)
) -> SearchCards:
    return SearchCards(SqlCardRepository(session))


def card_repository(
    session: Session = Depends(get_session), _: Principal = Depends(require_admin)
) -> SqlCardRepository:
    return SqlCardRepository(session)


def ability_repository(
    session: Session = Depends(get_session), _: Principal = Depends(require_admin)
) -> SqlAbilityRepository:
    return SqlAbilityRepository(session)


def list_abilities_uc(repo: SqlAbilityRepository = Depends(ability_repository)) -> ListAbilities:
    return ListAbilities(repo)


def create_location_uc(
    session: Session = Depends(get_session),
    admin: Principal = Depends(require_admin),
    images: ImageService = Depends(get_image_service),
) -> CreateLocation:
    return CreateLocation(SqlLocationRepository(session, admin.subject), images)


def retry_location_thumbnail_uc(
    session: Session = Depends(get_session),
    _: Principal = Depends(require_admin),
    images: ImageService = Depends(get_image_service),
) -> RetryLocationThumbnail:
    return RetryLocationThumbnail(SqlLocationRepository(session), images)


def location_repository(
    session: Session = Depends(get_session), _: Principal = Depends(require_admin)
) -> SqlLocationRepository:
    return SqlLocationRepository(session)
