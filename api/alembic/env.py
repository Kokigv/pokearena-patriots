"""Migraciones de base de datos. La URL sale de DATABASE_URL."""

from sqlalchemy import create_engine

from alembic import context
from pokearena.shared.config import Settings

url = context.config.attributes.get("database_url") or Settings.from_env().database_url


def run_migrations_online() -> None:
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection)
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


run_migrations_online()
