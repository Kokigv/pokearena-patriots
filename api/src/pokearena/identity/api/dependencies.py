"""Dependencias de FastAPI que otros módulos usan para autenticar y autorizar."""

from collections.abc import Callable
from functools import lru_cache

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from pokearena.identity.application.authentication import AuthenticationService, ensure_admin
from pokearena.identity.application.login import (
    IdentityProvider,
    NoOnboarding,
    PlayerOnboarding,
)
from pokearena.identity.domain.principal import Principal
from pokearena.identity.infrastructure.config_roles import ConfigRoleResolver
from pokearena.identity.infrastructure.jwt_codec import JwtTokenCodec
from pokearena.identity.infrastructure.providers import (
    GOOGLE_JWKS_URL,
    GoogleIdentityProvider,
    TestIdentityProvider,
)
from pokearena.identity.infrastructure.sql_players import SqlPlayerRepository
from pokearena.shared.config import get_settings
from pokearena.shared.db import get_session
from pokearena.shared.errors import NotAuthenticated

_bearer = HTTPBearer(auto_error=False)

# Nombre del atributo de ``app.state`` donde la raíz de composición (main.py) registra la
# fábrica de incorporación de jugadores. Así Identidad no importa al módulo Colección.
ONBOARDING_FACTORY = "player_onboarding_factory"
OnboardingFactory = Callable[[Session], PlayerOnboarding]


@lru_cache
def get_token_codec() -> JwtTokenCodec:
    settings = get_settings()
    return JwtTokenCodec(settings.jwt_secret, settings.jwt_issuer, settings.access_token_minutes)


@lru_cache
def get_auth_service() -> AuthenticationService:
    return AuthenticationService(get_token_codec())


@lru_cache
def get_role_resolver() -> ConfigRoleResolver:
    return ConfigRoleResolver(get_settings().admin_subjects)


@lru_cache
def get_google_provider() -> IdentityProvider:
    settings = get_settings()
    # PyJWKClient guarda en memoria las llaves públicas de Google (caché con expiración).
    keys = jwt.PyJWKClient(settings.google_jwks_url or GOOGLE_JWKS_URL, lifespan=3600, timeout=5)
    return GoogleIdentityProvider(settings.google_client_id, keys)


def get_test_provider() -> IdentityProvider:
    return TestIdentityProvider()


def get_player_repository(session: Session = Depends(get_session)) -> SqlPlayerRepository:
    return SqlPlayerRepository(session)


def get_onboarding(request: Request, session: Session = Depends(get_session)) -> PlayerOnboarding:
    factory: OnboardingFactory | None = getattr(request.app.state, ONBOARDING_FACTORY, None)
    return factory(session) if factory else NoOnboarding()


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth: AuthenticationService = Depends(get_auth_service),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise NotAuthenticated()
    return auth.authenticate(credentials.credentials)


def require_admin(principal: Principal = Depends(current_principal)) -> Principal:
    return ensure_admin(principal)
