"""Punto de entrada de la API de PokéArena."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pokearena.catalog.api.router import images_router
from pokearena.catalog.api.router import router as catalog_router
from pokearena.identity.api.router import dev_router, me_router
from pokearena.shared import http
from pokearena.shared.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = FastAPI(
        title="PokéArena API",
        version="0.1.0",
        description="Sprint 1: catálogo de cartas y ubicaciones. Contrato en api/openapi.yaml.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Location", "X-Correlation-Id", "Idempotent-Replayed"],
    )
    http.install(app)
    app.include_router(me_router)
    app.include_router(catalog_router)
    app.include_router(images_router)
    # RNF-SEG-10: el mecanismo de usuarios de prueba no existe en producción.
    if not settings.is_production:
        app.include_router(dev_router)

    @app.get("/health", tags=["Operación"])
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
