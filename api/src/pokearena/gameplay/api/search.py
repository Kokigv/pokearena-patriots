"""Buscar rival en clasificatoria. Reglas de concurrencia en PostgreSQL."""
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from pokearena.gameplay.domain.rules import RuleViolation, elo_window, validate_deck
from pokearena.gameplay.infrastructure.matches import create_game
from pokearena.identity.api.dependencies import current_principal
from pokearena.identity.domain.principal import Principal
from pokearena.shared.db import get_session

router = APIRouter(prefix='/v1', tags=['Matchmaking'])


class SearchIn(BaseModel):
    deck_id: uuid.UUID


def _find_valid_deck(session: Session, player: str, deck_id: str) -> list[str]:
    deck = session.execute(text('SELECT card_codes FROM player_decks WHERE id=:d AND player_id=:p'), {'d': deck_id, 'p': player}).scalar_one_or_none()
    if deck is None:
        raise HTTPException(404, 'Deck inexistente o ajeno')
    owned = set(session.execute(text('SELECT card_code FROM collection_cards WHERE player_id=:p'), {'p': player}).scalars())
    try:
        validate_deck(list(deck), owned)
    except RuleViolation as exc:
        raise HTTPException(422, str(exc)) from exc
    return list(deck)


def _active_game(session: Session, player: str) -> bool:
    return bool(session.execute(text("SELECT EXISTS(SELECT 1 FROM game_matches WHERE status='ACTIVE' AND (player_one=:p OR player_two=:p))"), {'p': player}).scalar())


@router.post('/matches/search', status_code=201)
def start_search(payload: SearchIn, principal: Principal = Depends(current_principal), session: Session = Depends(get_session)) -> dict:
    player = principal.subject
    # El bloqueo de la cuenta serializa solicitudes simultáneas del mismo jugador.
    session.execute(text('SELECT id FROM players WHERE id=:p FOR UPDATE'), {'p': player}).first()
    if _active_game(session, player):
        session.rollback()
        raise HTTPException(409, 'Ya tiene una partida activa')
    active = session.execute(text("SELECT id,deck_id FROM match_searches WHERE player_id=:p AND status='WAITING' FOR UPDATE"), {'p': player}).mappings().first()
    if active:
        session.rollback()
        if str(active['deck_id']) != str(payload.deck_id):
            raise HTTPException(409, 'Ya existe una búsqueda con otro deck')
        return {'search_id': str(active['id']), 'status': 'WAITING'}
    _find_valid_deck(session, player, str(payload.deck_id))
    cubes = session.execute(text('SELECT cubes FROM player_wallets WHERE player_id=:p'), {'p': player}).scalar()
    if cubes is None or cubes < 8:
        session.rollback()
        raise HTTPException(422, 'Se necesitan al menos 8 cubos')
    sid = str(uuid.uuid4())
    session.execute(text("INSERT INTO match_searches(id,player_id,deck_id,mode,status) VALUES(:i,:p,:d,'RANKED','WAITING')"), {'i': sid, 'p': player, 'd': str(payload.deck_id)})
    own = session.execute(text('SELECT * FROM match_searches WHERE id=:i FOR UPDATE'), {'i': sid}).mappings().one()
    own_elo = session.execute(text('SELECT elo FROM players WHERE id=:p'), {'p': player}).scalar_one()
    candidate = candidate_for(session, own, int(own_elo))
    if candidate:
        try:
            mid = create_game(session, own, candidate)
            session.execute(text("UPDATE match_searches SET status='MATCHED',match_id=:m WHERE id IN (:a,:b)"), {'m': mid, 'a': sid, 'b': str(candidate['id'])})
            session.commit()
            return {'search_id': sid, 'status': 'MATCHED', 'match_id': mid}
        except Exception:
            # Se revierte todo el emparejamiento; luego se mantiene esta búsqueda en cola.
            session.rollback()
            session.execute(text("INSERT INTO match_searches(id,player_id,deck_id,mode,status) VALUES(:i,:p,:d,'RANKED','WAITING') ON CONFLICT (id) DO NOTHING"), {'i': sid, 'p': player, 'd': str(payload.deck_id)})
            session.commit()
            return {'search_id': sid, 'status': 'WAITING'}
    session.commit()
    return {'search_id': sid, 'status': 'WAITING'}


def candidate_for(session: Session, search: dict, player_elo: int) -> dict | None:
    """Selecciona candidato con lock SKIP LOCKED para evitar emparejamientos dobles."""
    now = datetime.now(UTC)
    wait = max(0, (now - search['created_at']).total_seconds())
    window = elo_window(wait)
    return session.execute(text('''SELECT s.*,p.elo FROM match_searches s
        JOIN players p ON p.id=s.player_id WHERE s.status='WAITING'
        AND s.player_id <> :player AND abs(p.elo - :elo) <= :window
        ORDER BY s.created_at LIMIT 1 FOR UPDATE OF s SKIP LOCKED'''),
        {'player': search['player_id'], 'elo': player_elo, 'window': window}).mappings().first()
