"""Adaptador que conecta el puerto ``PlayerOnboarding`` de Identidad con la colección inicial.

Identidad define el puerto y no conoce cartas ni cubos; Colección lo implementa. La raíz de
composición (``main.py``) registra ``onboarding_factory`` en la aplicación.
"""

from sqlalchemy.orm import Session

from pokearena.collection.api.wiring import grant_initial_collection
from pokearena.collection.application.initial_collection import (
    FAILED_MESSAGE,
    NOT_AVAILABLE_MESSAGE,
    GrantInitialCollection,
    GrantOutcome,
)
from pokearena.identity.application.login import (
    OnboardingResult,
    OnboardingStatus,
    PlayerOnboarding,
)


class InitialCollectionOnboarding:
    def __init__(self, use_case: GrantInitialCollection) -> None:
        self._use_case = use_case

    def on_login(self, player_id: str) -> OnboardingResult:
        outcome = self._use_case.execute(player_id)
        if outcome is GrantOutcome.NOT_ENOUGH_CARDS:
            return OnboardingResult(OnboardingStatus.PENDING_CATALOG, NOT_AVAILABLE_MESSAGE)
        if outcome is GrantOutcome.FAILED:
            return OnboardingResult(OnboardingStatus.PENDING_RETRY, FAILED_MESSAGE)
        return OnboardingResult(OnboardingStatus.COMPLETED)


def onboarding_factory(session: Session) -> PlayerOnboarding:
    return InitialCollectionOnboarding(grant_initial_collection(session))
