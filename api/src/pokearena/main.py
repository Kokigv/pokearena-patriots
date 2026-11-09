"""Punto de entrada de la API de PokéArena."""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from pokearena.catalog.api.router import images_router
from pokearena.catalog.api.router import router as catalog_router
from pokearena.collection.api.onboarding import onboarding_factory
from pokearena.identity.api.dependencies import ONBOARDING_FACTORY
from pokearena.identity.api.router import auth_router, dev_router, me_router
from pokearena.shared import http
from pokearena.shared.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    app = FastAPI(
        title="PokéArena API",
        version="0.2.0",
        description=(
            "Sprint 2: inicio de sesión con Google, colección inicial y exploración del "
            "catálogo. Contrato en api/openapi.yaml."
        ),
    )
    # Raíz de composición: Identidad expone el puerto PlayerOnboarding y Colección lo
    # implementa (colección inicial, US 123). Así ningún módulo importa al otro al revés.
    setattr(app.state, ONBOARDING_FACTORY, onboarding_factory)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Location", "X-Correlation-Id", "Idempotent-Replayed"],
    )
    http.install(app)
    app.include_router(auth_router)
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
