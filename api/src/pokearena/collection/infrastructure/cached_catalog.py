"""Caché del catálogo en Redis (patrón decorador sobre el puerto ``CatalogReader``).

Política (ver ADR de caching):
- Se guardan las páginas del catálogo general y la lista de cartas Comunes disponibles, que
  son iguales para todos los jugadores. Nunca se guarda la colección de un jugador (la fuente
  de verdad sigue siendo PostgreSQL, RNF-DIS-04).
- Expiración corta (``CATALOG_CACHE_SECONDS``, 30 s por defecto): por eso "una carta recién
  creada puede tardar algunos segundos en aparecer" (criterio alterno de la US 124).
- Si Redis falla, se consulta el catálogo directamente: el caché nunca rompe la solicitud.
"""

import hashlib
import json
import logging
from dataclasses import asdict
from typing import Any

from redis.exceptions import RedisError

from pokearena.catalog.application.facade import (
    BrowseFilters,
    CatalogAbility,
    CatalogCard,
    CatalogPage,
)
from pokearena.collection.application.ports import CatalogReader

log = logging.getLogger(__name__)
PREFIX = "cache:catalog:v1"


def _page_from_json(raw: str | bytes) -> CatalogPage:
    data = json.loads(raw)
    items = []
    for item in data["items"]:
        ability = item.pop("ability")
        items.append(CatalogCard(**item, ability=CatalogAbility(**ability) if ability else None))
    return CatalogPage(items=items, next_cursor=data["next_cursor"])


class CachedCatalogReader:
    def __init__(self, inner: CatalogReader, redis: Any, ttl_seconds: int) -> None:
        self._inner = inner
        self._redis = redis
        self._ttl = ttl_seconds

    def _get(self, key: str) -> Any:
        if self._ttl <= 0:
            return None
        try:
            return self._redis.get(key)
        except RedisError:
            log.warning("Redis no disponible; se lee el catálogo sin caché")
            return None

    def _put(self, key: str, value: str) -> None:
        if self._ttl <= 0:
            return
        try:
            self._redis.set(key, value, ex=self._ttl)
        except RedisError:
            log.warning("No se pudo guardar en el caché del catálogo")

    def playable_common_codes(self) -> list[str]:
        key = f"{PREFIX}:commons"
        cached = self._get(key)
        if cached is not None:
            return list(json.loads(cached))
        codes = self._inner.playable_common_codes()
        self._put(key, json.dumps(codes))
        return codes

    def browse(self, filters: BrowseFilters, only_codes: frozenset[str] | None) -> CatalogPage:
        if only_codes is not None:  # depende del jugador: no se guarda
            return self._inner.browse(filters, only_codes)
        digest = hashlib.sha256(filters.cache_key.encode()).hexdigest()[:32]
        key = f"{PREFIX}:page:{digest}"
        cached = self._get(key)
        if cached is not None:
            return _page_from_json(cached)
        page = self._inner.browse(filters, None)
        self._put(key, json.dumps(asdict(page)))
        return page
