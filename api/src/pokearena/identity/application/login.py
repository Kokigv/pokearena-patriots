"""Caso de uso: Inicio de sesión con proveedor (US 116).

Flujo: el proveedor verifica su token → se obtiene o crea la cuenta (una sola por identidad,
aunque lleguen dos solicitudes a la vez) → se completa la incorporación del jugador (colección
inicial, US 123) → se emite la credencial propia de PokéArena con expiración corta.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol

from pokearena.identity.application.authentication import IssuedToken, RoleResolver, TokenCodec
from pokearena.identity.domain.player import ExternalIdentity, Player


class IdentityProvider(Protocol):
    """Puerto hacia un proveedor de identidad. Agregar otro proveedor es otro adaptador."""

    name: str

    def verify(self, credential: str) -> ExternalIdentity:
        """Lanza InvalidProviderToken o ProviderUnavailable."""
        ...


class PlayerRepository(Protocol):
    def get_or_create(self, identity: ExternalIdentity) -> tuple[Player, bool]:
        """Devuelve la cuenta asociada a la identidad, creándola si no existe.

        Debe ser seguro ante dos llamadas simultáneas con la misma identidad nueva: ambas
        reciben la misma cuenta. El booleano indica si esta llamada la creó.
        """
        ...

    def get(self, player_id: str) -> Player | None: ...


class OnboardingStatus(StrEnum):
    COMPLETED = "COMPLETED"  # la colección inicial ya está entregada
    PENDING_CATALOG = "PENDING_CATALOG"  # aún no hay suficientes cartas Comunes
    PENDING_RETRY = "PENDING_RETRY"  # la entrega falló; se reintenta en el siguiente ingreso


@dataclass(frozen=True)
class OnboardingResult:
    status: OnboardingStatus
    message: str | None = None


class PlayerOnboarding(Protocol):
    """Puerto que Identidad usa para completar la incorporación del jugador en cada ingreso.

    Lo implementa el módulo Colección (US 123). Identidad no conoce cartas ni cubos.
    """

    def on_login(self, player_id: str) -> OnboardingResult: ...


class NoOnboarding:
    def on_login(self, player_id: str) -> OnboardingResult:
        return OnboardingResult(OnboardingStatus.COMPLETED)


@dataclass(frozen=True)
class LoginResult:
    token: IssuedToken
    player: Player
    created: bool
    onboarding: OnboardingResult


class LoginWithProvider:
    def __init__(
        self,
        provider: IdentityProvider,
        players: PlayerRepository,
        codec: TokenCodec,
        roles: RoleResolver,
        onboarding: PlayerOnboarding,
    ) -> None:
        self._provider = provider
        self._players = players
        self._codec = codec
        self._roles = roles
        self._onboarding = onboarding

    def execute(self, credential: str) -> LoginResult:
        # 1. Si el token no es válido o el proveedor no responde, se lanza el error antes de
        #    tocar la base de datos: nunca queda una cuenta creada ni a medias.
        identity = self._provider.verify(credential)
        # 2. Una cuenta por identidad del proveedor (restricción única + ON CONFLICT).
        player, created = self._players.get_or_create(identity)
        # 3. Colección inicial (US 123). Si no se pudo entregar, el ingreso sigue y se
        #    reintenta en el siguiente: la entrega es todo o nada.
        onboarding = self._onboarding.on_login(player.id)
        # 4. Credencial propia con el id de la cuenta como sujeto.
        token = self._codec.issue(player.id, self._roles.roles_for(identity))
        return LoginResult(token, player, created, onboarding)
