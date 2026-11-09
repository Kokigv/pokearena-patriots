"""Construcción de los casos de uso de Colección con sus adaptadores."""

from functools import lru_cache

from redis import Redis
from sqlalchemy.orm import Session

from pokearena.catalog.api.public import build_catalog_facade
from pokearena.collection.application.initial_collection import GrantInitialCollection
from pokearena.collection.application.ports import CatalogReader
from pokearena.collection.infrastructure.cached_catalog import CachedCatalogReader
from pokearena.collection.infrastructure.randomness import SystemRandomSource
from pokearena.collection.infrastructure.sql_collection import SqlCollectionRepository
from pokearena.shared.config import get_settings


@lru_cache
def _redis() -> Redis:
    return Redis.from_url(get_settings().redis_url, socket_timeout=0.5)


def catalog_reader(session: Session) -> CatalogReader:
    return CachedCatalogReader(
        build_catalog_facade(session), _redis(), get_settings().catalog_cache_seconds
    )


def grant_initial_collection(session: Session) -> GrantInitialCollection:
    return GrantInitialCollection(
        catalog_reader(session), SqlCollectionRepository(session), SystemRandomSource()
    )
