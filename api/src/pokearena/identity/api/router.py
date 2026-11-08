"""Rutas de identidad: inicio de sesión con Google (US 116) y usuarios de prueba (US 118)."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from pokearena.identity.api.dependencies import (
    current_principal,
    get_google_provider,
    get_onboarding,
    get_player_repository,
    get_role_resolver,
    get_test_provider,
    get_token_codec,
)
from pokearena.identity.application.authentication import RoleResolver, TokenCodec
from pokearena.identity.application.login import (
    IdentityProvider,
    LoginResult,
    LoginWithProvider,
    PlayerOnboarding,
)
from pokearena.identity.domain.player import Player
from pokearena.identity.domain.principal import Principal
from pokearena.identity.infrastructure.sql_players import SqlPlayerRepository
from pokearena.shared.errors import NotFound

auth_router = APIRouter(prefix="/v1/auth", tags=["Identidad"])
dev_router = APIRouter(prefix="/v1/dev", tags=["Desarrollo (no existe en producción)"])
me_router = APIRouter(prefix="/v1", tags=["Identidad"])


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(min_length=1, max_length=4096, description="ID token de Google")


class TestTokenRequest(BaseModel):
    subject: str = Field(min_length=1, max_length=64, examples=["admin-1"])


class PlayerOut(BaseModel):
    id: str
    display_name: str
    email: str | None
    role: str
    elo: int
    is_test: bool


class OnboardingOut(BaseModel):
    status: str
    message: str | None


class SessionResponse(BaseModel):
    access_token: str
    token_type: str
    expires_in: int
    player: PlayerOut
    first_login: bool
    onboarding: OnboardingOut


class MeResponse(BaseModel):
    subject: str
    roles: list[str]
    player: PlayerOut | None


def _player_out(player: Player) -> PlayerOut:
    return PlayerOut(
        id=player.id,
        display_name=player.display_name,
        email=player.email,
        role=player.role.value,
        elo=player.elo,
        is_test=player.is_test,
    )


def _session_response(result: LoginResult) -> SessionResponse:
    return SessionResponse(
        access_token=result.token.access_token,
        token_type=result.token.token_type,
        expires_in=result.token.expires_in,
        player=_player_out(result.player),
        first_login=result.created,
        onboarding=OnboardingOut(
            status=result.onboarding.status.value, message=result.onboarding.message
        ),
    )


def _login(
    provider: IdentityProvider,
    players: SqlPlayerRepository,
    codec: TokenCodec,
    roles: RoleResolver,
    onboarding: PlayerOnboarding,
    credential: str,
) -> SessionResponse:
    use_case = LoginWithProvider(provider, players, codec, roles, onboarding)
    return _session_response(use_case.execute(credential))


@auth_router.post(
    "/google",
    response_model=SessionResponse,
    summary="Iniciar sesión con Google",
    responses={401: {}, 422: {}, 503: {}},
)
def login_with_google(
    body: GoogleLoginRequest,
    provider: IdentityProvider = Depends(get_google_provider),
    players: SqlPlayerRepository = Depends(get_player_repository),
    codec: TokenCodec = Depends(get_token_codec),
    roles: RoleResolver = Depends(get_role_resolver),
    onboarding: PlayerOnboarding = Depends(get_onboarding),
) -> SessionResponse:
    """Valida el ID token de Google una sola vez y entrega credenciales de PokéArena."""
    return _login(provider, players, codec, roles, onboarding, body.id_token)


@dev_router.post("/tokens", response_model=SessionResponse, status_code=201)
def issue_test_token(
    body: TestTokenRequest,
    provider: IdentityProvider = Depends(get_test_provider),
    players: SqlPlayerRepository = Depends(get_player_repository),
    codec: TokenCodec = Depends(get_token_codec),
    roles: RoleResolver = Depends(get_role_resolver),
    onboarding: PlayerOnboarding = Depends(get_onboarding),
) -> SessionResponse:
    """Crea una sesión para un usuario de prueba (US 118). Solo se registra fuera de producción.

    Sigue el mismo flujo que el inicio de sesión con Google: misma cuenta, misma colección
    inicial y el mismo formato de credencial.
    """
    return _login(provider, players, codec, roles, onboarding, body.subject.strip())


@me_router.get("/me", response_model=MeResponse)
def me(
    principal: Principal = Depends(current_principal),
    players: SqlPlayerRepository = Depends(get_player_repository),
) -> MeResponse:
    player = players.get(principal.subject)
    if player is None:
        raise NotFound("La cuenta de esta credencial ya no existe.")
    return MeResponse(
        subject=principal.subject,
        roles=sorted(r.value for r in principal.roles),
        player=_player_out(player),
    )
