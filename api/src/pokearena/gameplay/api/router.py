"""Endpoints de Deck (US 125)."""

import json
import uuid
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from pokearena.gameplay.domain.rules import RuleViolation, validate_deck
from pokearena.identity.api.dependencies import current_principal
from pokearena.identity.domain.principal import Principal
from pokearena.shared.db import get_session

router = APIRouter(prefix="/v1", tags=["Decks y partidas"])


class DeckIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    card_codes: list[str]


def _deck(row: Mapping[Any, Any]) -> dict:
    return {"id": str(row["id"]), "name": row["name"], "card_codes": row["card_codes"]}


@router.post("/me/decks", status_code=201)
def create_deck(
    payload: DeckIn,
    principal: Principal = Depends(current_principal),
    session: Session = Depends(get_session),
    idempotency_key: str | None = Header(None),
) -> dict:
    owner = principal.subject
    name = payload.name.strip()
    if not name:
        raise HTTPException(422, "El nombre es obligatorio")
    owned = set(
        session.execute(
            text("SELECT card_code FROM collection_cards WHERE player_id=:p"), {"p": owner}
        ).scalars()
    )
    try:
        validate_deck(payload.card_codes, owned)
    except RuleViolation as exc:
        raise HTTPException(422, str(exc)) from exc
    params = {
        "p": owner,
        "n": name,
        "k": idempotency_key,
        "i": str(uuid.uuid4()),
        "c": json.dumps(payload.card_codes),
    }
    inserted = (
        session.execute(
            text("""
        INSERT INTO player_decks(id,player_id,name,card_codes,idempotency_key)
        VALUES (:i,:p,:n,CAST(:c AS jsonb),:k)
        ON CONFLICT DO NOTHING RETURNING *
    """),
            params,
        )
        .mappings()
        .first()
    )
    if inserted:
        session.commit()
        return _deck(inserted)
    existing = (
        session.execute(
            text("""
        SELECT * FROM player_decks WHERE player_id=:p AND
        ((CAST(:k AS text) IS NOT NULL AND idempotency_key=:k)
          OR (CAST(:k AS text) IS NULL AND lower(name)=lower(:n)))
    """),
            params,
        )
        .mappings()
        .first()
    )
    if (
        existing
        and existing["name"].lower() == name.lower()
        and existing["card_codes"] == payload.card_codes
    ):
        return _deck(existing)
    raise HTTPException(409, "Conflicto con el nombre o la clave de idempotencia")


@router.get("/me/decks")
def list_decks(
    principal: Principal = Depends(current_principal), session: Session = Depends(get_session)
) -> list[dict]:
    rows = (
        session.execute(
            text("SELECT * FROM player_decks WHERE player_id=:p ORDER BY created_at,id"),
            {"p": principal.subject},
        )
        .mappings()
        .all()
    )
    return [_deck(r) for r in rows]


@router.get("/me/decks/{deck_id}")
def get_deck(
    deck_id: uuid.UUID,
    principal: Principal = Depends(current_principal),
    session: Session = Depends(get_session),
) -> dict:
    row = (
        session.execute(
            text("SELECT * FROM player_decks WHERE id=:i AND player_id=:p"),
            {"i": str(deck_id), "p": principal.subject},
        )
        .mappings()
        .first()
    )
    if row is None:
        raise HTTPException(404, "Deck no encontrado")
    return _deck(row)
