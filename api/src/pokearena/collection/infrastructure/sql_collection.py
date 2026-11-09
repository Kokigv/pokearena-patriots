"""Adaptador de PostgreSQL para la colección de los jugadores."""

import uuid

from sqlalchemy import exists, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from pokearena.collection.domain.collection import CollectionSummary, CubeMovement, OwnedCard
from pokearena.collection.domain.initial_collection import INITIAL_GRANT_REASON, InitialGrant
from pokearena.collection.infrastructure.tables import (
    collection_cards,
    cube_movements,
    player_wallets,
)


def _is_uuid(value: str) -> bool:
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


class SqlCollectionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def has_initial_grant(self, player_id: str) -> bool:
        if not _is_uuid(player_id):
            return False
        stmt = select(exists().where(player_wallets.c.player_id == player_id))
        return bool(self._session.execute(stmt).scalar())

    def grant_initial(self, player_id: str, grant: InitialGrant) -> bool:
        """Unidad de trabajo: billetera, cartas y primer movimiento de cubos se confirman
        juntos con un solo COMMIT, o se deshacen juntos con ROLLBACK."""
        try:
            # 1. La fila de la billetera es el candado: si otra transacción la está creando,
            #    esta espera; si ya existe, no inserta nada y no se entrega dos veces.
            created = self._session.execute(
                insert(player_wallets)
                .values(player_id=player_id, cubes=grant.cubes)
                .on_conflict_do_nothing(index_elements=["player_id"])
                .returning(player_wallets.c.player_id)
            ).first()
            if created is None:
                self._session.rollback()
                return False
            # 2. Las 15 cartas (una copia de cada una).
            self._session.execute(
                insert(collection_cards),
                [{"player_id": player_id, "card_code": c, "copies": 1} for c in grant.card_codes],
            )
            # 3. Los 1,000 cubos como primer movimiento del historial.
            self._session.execute(
                insert(cube_movements).values(
                    player_id=player_id,
                    amount=grant.cubes,
                    reason=INITIAL_GRANT_REASON,
                    balance_after=grant.cubes,
                )
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise
        return True

    def copies_by_card(self, player_id: str) -> dict[str, int]:
        if not _is_uuid(player_id):  # credencial sin cuenta de jugador: no posee cartas
            return {}
        stmt = select(collection_cards.c.card_code, collection_cards.c.copies).where(
            collection_cards.c.player_id == player_id
        )
        return {code: copies for code, copies in self._session.execute(stmt).all()}

    def summary(self, player_id: str) -> CollectionSummary:
        if not _is_uuid(player_id):
            return CollectionSummary(player_id=player_id, initial_granted=False, cubes=0)
        wallet = self._session.execute(
            select(player_wallets.c.cubes).where(player_wallets.c.player_id == player_id)
        ).scalar()
        cards = [
            OwnedCard(code, copies)
            for code, copies in sorted(self.copies_by_card(player_id).items())
        ]
        movements = [
            CubeMovement(r.amount, r.reason, r.balance_after, r.created_at)
            for r in self._session.execute(
                select(cube_movements)
                .where(cube_movements.c.player_id == player_id)
                .order_by(cube_movements.c.id)
            ).all()
        ]
        return CollectionSummary(
            player_id=player_id,
            initial_granted=wallet is not None,
            cubes=wallet or 0,
            cards=cards,
            movements=movements,
        )
