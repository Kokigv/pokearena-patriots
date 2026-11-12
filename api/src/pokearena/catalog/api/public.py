"""API pública del módulo Catálogo para otros módulos: construye la fachada con sus adaptadores.

Otros módulos importan solo este archivo y ``catalog.application.facade`` (RNF-ARQ-03).
"""

from sqlalchemy.orm import Session

from pokearena.catalog.application.facade import CatalogFacade
from pokearena.catalog.infrastructure.sql_repositories import (
    SqlAbilityRepository,
    SqlCardRepository,
)


def build_catalog_facade(session: Session) -> CatalogFacade:
    return CatalogFacade(SqlCardRepository(session), SqlAbilityRepository(session))
