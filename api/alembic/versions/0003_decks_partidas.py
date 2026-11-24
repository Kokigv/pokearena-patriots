"""Decks, cola de búsqueda y partidas del Sprint 3.

Revision ID: 0003
Revises: 0002
"""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE player_decks (
        id uuid PRIMARY KEY, player_id uuid NOT NULL, name varchar(60) NOT NULL,
        card_codes jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now(),
        idempotency_key text, UNIQUE(player_id,idempotency_key))""")
    op.execute("CREATE UNIQUE INDEX uq_deck_player_name ON player_decks(player_id,lower(name))")
    op.execute("""CREATE TABLE match_searches (
        id uuid PRIMARY KEY, player_id uuid NOT NULL, deck_id uuid NOT NULL,
        mode varchar(16) NOT NULL DEFAULT 'RANKED', status varchar(20) NOT NULL DEFAULT 'WAITING',
        created_at timestamptz NOT NULL DEFAULT now(),
        last_seen_at timestamptz NOT NULL DEFAULT now(),
        match_id uuid, bot_offered boolean NOT NULL DEFAULT false)""")
    op.execute(
        "CREATE UNIQUE INDEX ux_search_active_player ON match_searches(player_id) "
        "WHERE status = 'WAITING'"
    )
    op.execute("CREATE INDEX ix_search_waiting ON match_searches(status,created_at)")
    op.execute("""CREATE TABLE game_matches (
        id uuid PRIMARY KEY, player_one uuid NOT NULL, player_two uuid,
        bot boolean NOT NULL DEFAULT false, status varchar(16) NOT NULL DEFAULT 'ACTIVE',
        deck_one uuid NOT NULL, deck_two uuid,
        state jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now())""")
    op.execute(
        "CREATE UNIQUE INDEX ux_active_match_one ON game_matches(player_one) WHERE status='ACTIVE'"
    )
    op.execute(
        "CREATE UNIQUE INDEX ux_active_match_two ON game_matches(player_two) "
        "WHERE status='ACTIVE' AND player_two IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS game_matches")
    op.execute("DROP TABLE IF EXISTS match_searches")
    op.execute("DROP TABLE IF EXISTS player_decks")
