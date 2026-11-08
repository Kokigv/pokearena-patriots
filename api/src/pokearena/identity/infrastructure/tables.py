"""Tablas del módulo Identidad. Ningún otro módulo las consulta directamente (RNF-ARQ-03)."""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    func,
)
from sqlalchemy.dialects.postgresql import UUID

metadata = MetaData()

players = Table(
    "players",
    metadata,
    Column("id", UUID(as_uuid=False), primary_key=True),
    Column("display_name", String(60), nullable=False),
    Column("email", String(254)),
    Column("role", String(10), nullable=False),
    Column("elo", Integer, nullable=False),
    Column("is_test", Boolean, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("last_login_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

# Una fila por identidad de proveedor. La llave primaria (provider, subject) garantiza que una
# misma identidad nunca tenga dos cuentas, aunque inicie sesión dos veces al mismo tiempo.
player_identities = Table(
    "player_identities",
    metadata,
    Column("provider", String(20), primary_key=True),
    Column("subject", String(255), primary_key=True),
    Column("player_id", UUID(as_uuid=False), ForeignKey("players.id"), nullable=False),
    Column("email", String(254)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)
