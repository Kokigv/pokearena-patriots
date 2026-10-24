"""Crea la base de pruebas indicada en DATABASE_URL si todavía no existe."""

import os

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

url = make_url(os.environ["DATABASE_URL"])
admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
with admin.connect() as conn:
    exists = conn.execute(
        text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": url.database}
    ).scalar()
    if not exists:
        conn.execute(text(f'CREATE DATABASE "{url.database}"'))
        print(f"Base {url.database} creada.")
