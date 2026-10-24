"""Dependencias de FastAPI que otros módulos usan para autenticar y autorizar."""

from functools import lru_cache

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from pokearena.identity.application.authentication import AuthenticationService, ensure_admin
from pokearena.identity.domain.principal import Principal
from pokearena.identity.infrastructure.config_roles import ConfigRoleResolver
from pokearena.identity.infrastructure.jwt_codec import JwtTokenCodec
from pokearena.shared.config import get_settings
from pokearena.shared.errors import NotAuthenticated

_bearer = HTTPBearer(auto_error=False)


@lru_cache
def get_auth_service() -> AuthenticationService:
    settings = get_settings()
    codec = JwtTokenCodec(settings.jwt_secret, settings.jwt_issuer, settings.access_token_minutes)
    return AuthenticationService(codec, ConfigRoleResolver(settings.admin_subjects))


def current_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
    auth: AuthenticationService = Depends(get_auth_service),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise NotAuthenticated()
    return auth.authenticate(credentials.credentials)


def require_admin(principal: Principal = Depends(current_principal)) -> Principal:
    return ensure_admin(principal)
