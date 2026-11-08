"""Adaptador de PostgreSQL para las cuentas de jugador."""

import uuid
from typing import Any

from sqlalchemy import Row, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from pokearena.identity.domain.player import (
    INITIAL_ELO,
    ExternalIdentity,
    Player,
    display_name_for,
)
from pokearena.identity.domain.principal import Role
from pokearena.identity.infrastructure.tables import player_identities, players


def _player(row: Row[Any]) -> Player:
    return Player(
        id=str(row.id),
        display_name=row.display_name,
        email=row.email,
        role=Role(row.role),
        elo=row.elo,
        is_test=row.is_test,
        created_at=row.created_at,
    )


class SqlPlayerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, player_id: str) -> Player | None:
        try:
            uuid.UUID(player_id)
        except ValueError:
            return None
        row = self._session.execute(select(players).where(players.c.id == player_id)).first()
        return _player(row) if row else None

    def _find(self, identity: ExternalIdentity) -> Player | None:
        stmt = (
            select(players)
            .join(player_identities, player_identities.c.player_id == players.c.id)
            .where(
                player_identities.c.provider == identity.provider,
                player_identities.c.subject == identity.subject,
            )
        )
        row = self._session.execute(stmt).first()
        return _player(row) if row else None

    def get_or_create(self, identity: ExternalIdentity) -> tuple[Player, bool]:
        existing = self._find(identity)
        if existing is not None:
            self._touch(existing.id, identity)
            refreshed = self.get(existing.id)
            assert refreshed is not None
            return refreshed, False

        # Primer ingreso: cuenta + identidad en la misma transacción. Si otra solicitud con la
        # misma identidad ganó la carrera, el INSERT de la identidad no inserta nada (ON
        # CONFLICT DO NOTHING); se deshace la cuenta sobrante y se usa la del ganador.
        player_id = str(uuid.uuid4())
        self._session.execute(
            insert(players).values(
                id=player_id,
                display_name=display_name_for(identity),
                email=identity.email,
                role=Role.PLAYER.value,
                elo=INITIAL_ELO,
                is_test=identity.is_test,
            )
        )
        linked = self._session.execute(
            insert(player_identities)
            .values(
                provider=identity.provider,
                subject=identity.subject,
                player_id=player_id,
                email=identity.email,
            )
            .on_conflict_do_nothing(index_elements=["provider", "subject"])
            .returning(player_identities.c.player_id)
        ).first()
        if linked is None:
            self._session.rollback()
            winner = self._find(identity)
            assert winner is not None
            return winner, False
        self._session.commit()
        created = self.get(player_id)
        assert created is not None
        return created, True

    def _touch(self, player_id: str, identity: ExternalIdentity) -> None:
        """Registra el ingreso y actualiza el correo si cambió en el proveedor."""
        self._session.execute(
            update(players)
            .where(players.c.id == player_id)
            .values(last_login_at=func.now(), email=identity.email or players.c.email)
        )
        self._session.execute(
            update(player_identities)
            .where(
                player_identities.c.provider == identity.provider,
                player_identities.c.subject == identity.subject,
            )
            .values(email=identity.email or player_identities.c.email)
        )
        self._session.commit()
