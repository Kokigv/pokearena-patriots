"""Caso de uso: Explorar el catálogo y mi colección (US 124)."""

from dataclasses import dataclass

from pokearena.catalog.application.facade import BrowseFilters, CatalogCard
from pokearena.collection.application.ports import CatalogReader, CollectionRepository
from pokearena.collection.domain.collection import CollectionSummary


@dataclass(frozen=True)
class CatalogEntry:
    card: CatalogCard
    owned: bool
    copies: int


@dataclass(frozen=True)
class CatalogEntryPage:
    items: list[CatalogEntry]
    next_cursor: str | None


class ExploreCatalog:
    """Combina una página del catálogo con lo que posee el jugador.

    El catálogo y la colección son de módulos distintos: se consulta una página acotada del
    catálogo (fachada) y las copias del jugador (sus propias tablas), y se unen en memoria.
    Con ``owned_only`` la colección del jugador se pasa como filtro al catálogo, así la
    paginación sigue siendo correcta.
    """

    def __init__(self, catalog: CatalogReader, collection: CollectionRepository) -> None:
        self._catalog = catalog
        self._collection = collection

    def execute(self, player_id: str, filters: BrowseFilters, owned_only: bool) -> CatalogEntryPage:
        copies = self._collection.copies_by_card(player_id)
        if owned_only and not copies:
            return CatalogEntryPage(items=[], next_cursor=None)
        page = self._catalog.browse(filters, frozenset(copies) if owned_only else None)
        items = [
            CatalogEntry(card, owned=card.code in copies, copies=copies.get(card.code, 0))
            for card in page.items
        ]
        return CatalogEntryPage(items, page.next_cursor)


class GetMyCollection:
    def __init__(self, collection: CollectionRepository) -> None:
        self._collection = collection

    def execute(self, player_id: str) -> CollectionSummary:
        return self._collection.summary(player_id)
