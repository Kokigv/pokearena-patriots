"""Tablas del módulo Colección. Ningún otro módulo las consulta directamente (RNF-ARQ-03).

No hay llaves foráneas hacia ``players`` ni ``cards``: son tablas de otros módulos y cada
módulo es dueño de las suyas (ADR-001). La integridad la garantizan los casos de uso.
"""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    Identity,
    Integer,
    MetaData,
    String,
    Table,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

# Una fila por jugador que ya recibió su colección inicial. La llave primaria es la garantía de
# "exactamente una vez": dos entregas simultáneas no pueden insertar la misma fila.
player_wallets = Table(
    "player_wallets",
    metadata,
    Column("player_id", UUID(as_uuid=False), primary_key=True),
    Column("cubes", Integer, nullable=False),
    Column(
        "initial_granted_at", DateTime(timezone=True), nullable=False, server_default=func.now()
    ),
    CheckConstraint("cubes >= 0", name="ck_player_wallets_cubes"),
)

collection_cards = Table(
    "collection_cards",
    metadata,
    Column("player_id", UUID(as_uuid=False), primary_key=True),
    Column("card_code", String(20), primary_key=True),
    Column("copies", Integer, nullable=False),
    Column("acquired_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("copies > 0", name="ck_collection_cards_copies"),
)

# Historial de cubos: el saldo siempre coincide con la suma de los movimientos (RNF-INT-03).
cube_movements = Table(
    "cube_movements",
    metadata,
    Column("id", BigInteger, Identity(), primary_key=True),
    Column("player_id", UUID(as_uuid=False), nullable=False),
    Column("amount", Integer, nullable=False),
    Column("reason", String(30), nullable=False),
    Column("balance_after", Integer, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
