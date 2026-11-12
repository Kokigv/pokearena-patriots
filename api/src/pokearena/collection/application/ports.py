"""Puertos del módulo Colección. Los implementa infrastructure/ (o la fachada del catálogo)."""

from typing import Protocol

from pokearena.catalog.application.facade import BrowseFilters, CatalogPage
from pokearena.collection.domain.collection import CollectionSummary
from pokearena.collection.domain.initial_collection import InitialGrant


class CatalogReader(Protocol):
    """Lo que Colección necesita del catálogo. ``CatalogFacade`` lo cumple tal cual, y
    ``CachedCatalogReader`` le agrega caché sin que los casos de uso se enteren."""

    def playable_common_codes(self) -> list[str]: ...

    def browse(self, filters: BrowseFilters, only_codes: frozenset[str] | None) -> CatalogPage: ...


class CollectionRepository(Protocol):
    def has_initial_grant(self, player_id: str) -> bool: ...

    def grant_initial(self, player_id: str, grant: InitialGrant) -> bool:
        """Entrega cartas y cubos en UNA transacción (todo o nada) y exactamente una vez.

        Devuelve False si el jugador ya la había recibido (por ejemplo, otra solicitud
        simultánea ganó la carrera). Cualquier error deshace la transacción completa.
        """
        ...

    def copies_by_card(self, player_id: str) -> dict[str, int]: ...

    def summary(self, player_id: str) -> CollectionSummary: ...
