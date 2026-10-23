"""Catálogo: habilidades, cartas, contadores de código y ubicaciones.

Revision ID: 0001
Revises:
"""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

CARD_TYPES = ("FUEGO", "AGUA", "PLANTA", "ELECTRICO", "PSIQUICO", "LUCHA")


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    # unaccent() no es IMMUTABLE, así que no puede usarse en un índice; este envoltorio sí.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text
        LANGUAGE sql IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent'::regdictionary, $1) $$
        """
    )

    op.execute(
        """
        CREATE TABLE abilities (
            code             varchar(10) PRIMARY KEY,
            name             varchar(60) NOT NULL,
            trigger          varchar(20) NOT NULL,
            effect           varchar(20) NOT NULL,
            target           varchar(30),
            affected_type    varchar(12),
            condition        jsonb NOT NULL DEFAULT '{}',
            params           jsonb NOT NULL DEFAULT '{}',
            evolution_target varchar(20),
            created_at       timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        INSERT INTO abilities (code, name, trigger, effect)
        VALUES ('HAB-000', 'Sin Habilidad', 'NINGUNO', 'SIN_EFECTO')
        """
    )

    op.execute(
        """
        CREATE TABLE card_code_counters (
            card_type  varchar(12) PRIMARY KEY,
            last_value integer NOT NULL DEFAULT 0
        )
        """
    )
    values = ", ".join(f"('{t}', 0)" for t in CARD_TYPES)
    op.execute(f"INSERT INTO card_code_counters (card_type, last_value) VALUES {values}")

    op.execute(
        """
        CREATE TABLE cards (
            code            varchar(20) PRIMARY KEY,
            seq             bigint NOT NULL,
            name            varchar(60) NOT NULL,
            cost            smallint NOT NULL
                            CONSTRAINT ck_cards_cost CHECK (cost BETWEEN 0 AND 10),
            power           smallint NOT NULL
                            CONSTRAINT ck_cards_power CHECK (power BETWEEN -20 AND 20),
            type            varchar(12) NOT NULL,
            rarity          varchar(12) NOT NULL,
            ability_code    varchar(10) NOT NULL REFERENCES abilities(code),
            image_key       text NOT NULL,
            thumb_key       text,
            image_status    varchar(10) NOT NULL,
            idempotency_key varchar(100) UNIQUE,
            created_by      varchar(64),
            created_at      timestamptz NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "ALTER TABLE abilities ADD CONSTRAINT fk_abilities_evolution_target "
        "FOREIGN KEY (evolution_target) REFERENCES cards(code)"
    )
    op.execute(
        "CREATE INDEX ix_cards_name_trgm ON cards USING gin (f_unaccent(lower(name)) gin_trgm_ops)"
    )
    op.execute("CREATE INDEX ix_cards_code_trgm ON cards USING gin (code gin_trgm_ops)")
    op.execute("CREATE UNIQUE INDEX ux_cards_type_seq ON cards (type, seq)")
    op.execute("CREATE INDEX ix_cards_rarity ON cards (rarity)")
    op.execute("CREATE INDEX ix_cards_cost ON cards (cost)")
    op.execute("CREATE INDEX ix_cards_power ON cards (power)")
    op.execute("CREATE INDEX ix_cards_ability ON cards (ability_code)")

    op.execute(
        """
        CREATE TABLE locations (
            id                  uuid PRIMARY KEY,
            name                varchar(60) NOT NULL,
            description         varchar(500) NOT NULL,
            card_limit          smallint NOT NULL
                                CONSTRAINT ck_locations_card_limit
                                CHECK (card_limit BETWEEN 0 AND 5),
            extra_energy_mode   varchar(12) NOT NULL,
            extra_energy_amount smallint NOT NULL,
            effect_type         varchar(30) NOT NULL,
            effect_params       jsonb NOT NULL DEFAULT '{}',
            image_key           text NOT NULL,
            thumb_key           text,
            image_status        varchar(10) NOT NULL,
            idempotency_key     varchar(100) UNIQUE,
            created_by          varchar(64),
            created_at          timestamptz NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS locations")
    op.execute("ALTER TABLE abilities DROP CONSTRAINT IF EXISTS fk_abilities_evolution_target")
    op.execute("DROP TABLE IF EXISTS cards")
    op.execute("DROP TABLE IF EXISTS card_code_counters")
    op.execute("DROP TABLE IF EXISTS abilities")
    op.execute("DROP FUNCTION IF EXISTS f_unaccent(text)")
