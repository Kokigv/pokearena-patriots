"""Rutas de identidad. En el Sprint 1 solo existe el emisor de credenciales de prueba."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from pokearena.identity.api.dependencies import current_principal, get_auth_service
from pokearena.identity.application.authentication import AuthenticationService
from pokearena.identity.domain.principal import Principal

dev_router = APIRouter(prefix="/v1/dev", tags=["Desarrollo (no existe en producción)"])
me_router = APIRouter(prefix="/v1", tags=["Identidad"])


class TestTokenRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=64, examples=["admin-1"])


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int


class MeResponse(BaseModel):
    subject: str
    roles: list[str]


@dev_router.post("/tokens", response_model=TokenResponse, status_code=201)
def issue_test_token(
    body: TestTokenRequest, auth: AuthenticationService = Depends(get_auth_service)
) -> TokenResponse:
    """Crea una sesión para un usuario de prueba (F-01). Solo se registra fuera de producción."""
    issued = auth.issue_test_token(body.subject)
    return TokenResponse(
        access_token=issued.access_token,
        token_type=issued.token_type,
        expires_in=issued.expires_in,
    )


@me_router.get("/me", response_model=MeResponse)
def me(principal: Principal = Depends(current_principal)) -> MeResponse:
    return MeResponse(subject=principal.subject, roles=sorted(r.value for r in principal.roles))
