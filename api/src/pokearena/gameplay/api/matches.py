"""Lectura segura del estado de una partida inicializada."""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from pokearena.gameplay.infrastructure.matches import public_game
from pokearena.identity.api.dependencies import current_principal
from pokearena.identity.domain.principal import Principal
from pokearena.shared.db import get_session

router = APIRouter(prefix="/v1", tags=["Partidas"])


@router.get("/matches/{match_id}")
def read_match(
    match_id: uuid.UUID,
    principal: Principal = Depends(current_principal),
    session: Session = Depends(get_session),
) -> dict:
    result = public_game(session, str(match_id), principal.subject)
    if result is None:
        raise HTTPException(404, "Partida no encontrada")
    return result
