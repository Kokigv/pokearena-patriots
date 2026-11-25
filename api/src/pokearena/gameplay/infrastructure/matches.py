"""Inicialización de partidas atómica dentro de la misma transacción SQL."""

import json
import secrets
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from pokearena.gameplay.domain.rules import prepare_state


def create_game(session: Session, first: dict, second: dict | None = None) -> str:
    """Crea una partida sin confirmar la transacción; el llamador debe hacer commit/rollback."""
    player_one = str(first["player_id"])
    player_two = str(second["player_id"]) if second else None
    deck_one = session.execute(
        text("SELECT card_codes FROM player_decks WHERE id=:i AND player_id=:p"),
        {"i": str(first["deck_id"]), "p": player_one},
    ).scalar_one()
    deck_two = (
        session.execute(
            text("SELECT card_codes FROM player_decks WHERE id=:i AND player_id=:p"),
            {"i": str(second["deck_id"]), "p": player_two},
        ).scalar_one()
        if second
        else None
    )
    places = [
        dict(row)
        for row in session.execute(
            text(
                "SELECT id,card_limit,assignable_to_matches,image_status FROM locations "
                "WHERE assignable_to_matches=true AND image_status='READY'"
            )
        )
        .mappings()
        .all()
    ]
    seed = secrets.randbits(63)
    state = prepare_state(list(deck_one), list(deck_two) if deck_two else None, places, seed)
    mid = str(uuid.uuid4())
    session.execute(
        text("""INSERT INTO game_matches(id,player_one,player_two,bot,deck_one,deck_two,state)
        VALUES(:i,:p,:q,:b,:d,:e,CAST(:s AS jsonb))"""),
        {
            "i": mid,
            "p": player_one,
            "q": player_two,
            "b": second is None,
            "d": str(first["deck_id"]),
            "e": str(second["deck_id"]) if second else None,
            "s": json.dumps(state),
        },
    )
    return mid


def public_game(session: Session, match_id: str, player_id: str) -> dict | None:
    row = (
        session.execute(
            text("SELECT * FROM game_matches WHERE id=:i AND (player_one=:p OR player_two=:p)"),
            {"i": match_id, "p": player_id},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    data = dict(row["state"])
    # Nunca transmitir el orden del deck, las cartas en mano ni la pila del contrincante.
    first = str(row["player_one"]) == player_id
    mine, other = ("one", "two") if first else ("two", "one")
    return {
        "id": str(row["id"]),
        "status": row["status"],
        "bot": row["bot"],
        "locations": data["locations"],
        "energy": data["energy"],
        "turn": data["turn"],
        "turn_seconds": data["turn_seconds"],
        "cube_stake": data["cube_stake"],
        "my_hand": data[f"hand_{mine}"],
        "my_draw_count": len(data[f"draw_pile_{mine}"]),
        "opponent_hand_count": len(data[f"hand_{other}"]),
        "my_cemetery": data[f"cemetery_{mine}"],
    }
