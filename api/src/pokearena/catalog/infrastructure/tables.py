"""Tablas del módulo Catálogo. Ningún otro módulo las consulta directamente (RNF-ARQ-03)."""

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    SmallInteger,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID

metadata = MetaData()

abilities = Table(
    "abilities",
    metadata,
    Column("code", String(10), primary_key=True),
    Column("name", String(60), nullable=False),
    Column("trigger", String(20), nullable=False),
    Column("effect", String(20), nullable=False),
    Column("target", String(30)),
    Column("affected_type", String(12)),
    Column("condition", JSONB, nullable=False, server_default="{}"),
    Column("params", JSONB, nullable=False, server_default="{}"),
    Column("evolution_target", String(20)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
)

card_code_counters = Table(
    "card_code_counters",
    metadata,
    Column("card_type", String(12), primary_key=True),
    Column("last_value", Integer, nullable=False, server_default="0"),
)

cards = Table(
    "cards",
    metadata,
    Column("code", String(20), primary_key=True),
    Column("seq", BigInteger, nullable=False),
    Column("name", String(60), nullable=False),
    Column("cost", SmallInteger, nullable=False),
    Column("power", SmallInteger, nullable=False),
    Column("type", String(12), nullable=False),
    Column("rarity", String(12), nullable=False),
    Column("ability_code", String(10), ForeignKey("abilities.code"), nullable=False),
    Column("image_key", Text, nullable=False),
    Column("thumb_key", Text),
    Column("image_status", String(10), nullable=False),
    Column("idempotency_key", String(100), unique=True),
    Column("created_by", String(64)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("cost BETWEEN 0 AND 10", name="ck_cards_cost"),
    CheckConstraint("power BETWEEN -20 AND 20", name="ck_cards_power"),
)

locations = Table(
    "locations",
    metadata,
    Column("id", UUID(as_uuid=False), primary_key=True),
    Column("name", String(60), nullable=False),
    Column("description", String(500), nullable=False),
    Column("card_limit", SmallInteger, nullable=False),
    Column("extra_energy_mode", String(12), nullable=False),
    Column("extra_energy_amount", SmallInteger, nullable=False),
    Column("effect_type", String(30), nullable=False),
    Column("effect_params", JSONB, nullable=False, server_default="{}"),
    Column("image_key", Text, nullable=False),
    Column("thumb_key", Text),
    Column("image_status", String(10), nullable=False),
    Column("idempotency_key", String(100), unique=True),
    Column("created_by", String(64)),
    Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    CheckConstraint("card_limit BETWEEN 0 AND 5", name="ck_locations_card_limit"),
)
