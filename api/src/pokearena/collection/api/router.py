"""Rutas HTTP de Colección: Explorar el catálogo y mi colección (US 124)."""

from fastapi import APIRouter, Depends, Query

from pokearena.catalog.application.facade import parse_browse_filters
from pokearena.collection.api.schemas import CatalogCardOut, CatalogPageOut, CollectionOut
from pokearena.collection.api.wiring import explore_catalog_uc, my_collection_uc
from pokearena.collection.application.explore_catalog import ExploreCatalog, GetMyCollection
from pokearena.identity.api.dependencies import current_principal
from pokearena.identity.domain.principal import Principal

router = APIRouter(prefix="/v1", tags=["Colección"])


@router.get(
    "/catalog",
    response_model=CatalogPageOut,
    summary="Explorar el catálogo y mi colección",
    responses={401: {}, 422: {}},
)
def explore_catalog(
    type: str | None = Query(None, description="FUEGO, AGUA, PLANTA, ELECTRICO, PSIQUICO, LUCHA"),
    cost: int | None = Query(None, description="Costo exacto (0 a 10)"),
    cost_min: int | None = Query(None, description="Costo mínimo (0 a 10)"),
    cost_max: int | None = Query(None, description="Costo máximo (0 a 10)"),
    owned: bool = Query(False, description="true: solo las cartas que poseo"),
    cursor: str | None = Query(None, description="next_cursor de la página anterior"),
    limit: int | None = Query(None, description="1 a 100; por defecto 50"),
    principal: Principal = Depends(current_principal),
    use_case: ExploreCatalog = Depends(explore_catalog_uc),
) -> CatalogPageOut:
    filters = parse_browse_filters(
        type=type, cost=cost, cost_min=cost_min, cost_max=cost_max, cursor=cursor, limit=limit
    )
    page = use_case.execute(principal.subject, filters, owned_only=owned)
    return CatalogPageOut(
        items=[CatalogCardOut.of(entry) for entry in page.items], next_cursor=page.next_cursor
    )


@router.get(
    "/me/collection",
    response_model=CollectionOut,
    summary="Mi colección y saldo de cubos",
    responses={401: {}},
)
def my_collection(
    principal: Principal = Depends(current_principal),
    use_case: GetMyCollection = Depends(my_collection_uc),
) -> CollectionOut:
    return CollectionOut.of(use_case.execute(principal.subject))
