"""Fixtures comunes. Las pruebas usan PostgreSQL y Redis propios del proyecto (Docker Compose
o servicios del CI) y guardan las imágenes en disco: no dependen de servicios externos
reales (RNF-PRU-05)."""

import io
import os
import tempfile
import uuid
from collections.abc import Iterator
from pathlib import Path

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/pokearena_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ["APP_ENV"] = "test"
os.environ["ADMIN_SUBJECTS"] = "admin-1,admin-2"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["CATALOG_CACHE_SECONDS"] = "0"  # las pruebas de caché lo activan explícitamente
os.environ["GOOGLE_CLIENT_ID"] = "pokearena-test.apps.googleusercontent.com"
os.environ["STORAGE_LOCAL_PATH"] = tempfile.mkdtemp(prefix="pokearena-img-")

import pytest  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402
from redis import Redis  # noqa: E402
from sqlalchemy import text  # noqa: E402

from alembic import command  # noqa: E402
from pokearena.main import create_app  # noqa: E402
from pokearena.shared.db import get_engine  # noqa: E402

API_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session", autouse=True)
def database() -> Iterator[None]:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE; CREATE SCHEMA public;"))
    cfg = Config(str(API_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(API_DIR / "alembic"))
    cfg.attributes["database_url"] = os.environ["DATABASE_URL"]
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(autouse=True)
def clean_state(database: None) -> Iterator[None]:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("UPDATE abilities SET evolution_target = NULL"))
        conn.execute(text("DELETE FROM cards"))
        conn.execute(text("DELETE FROM abilities WHERE code <> 'HAB-000'"))
        conn.execute(text("TRUNCATE locations"))
        conn.execute(text("TRUNCATE player_wallets, collection_cards, cube_movements"))
        conn.execute(text("TRUNCATE player_identities, players"))
        conn.execute(text("UPDATE card_code_counters SET last_value = 0"))
    Redis.from_url(os.environ["REDIS_URL"]).flushdb()
    yield


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(create_app()) as c:
        yield c


def token_for(client: TestClient, subject: str) -> dict[str, str]:
    resp = client.post("/v1/dev/tokens", json={"subject": subject})
    assert resp.status_code == 201, resp.text
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest.fixture
def admin(client: TestClient) -> dict[str, str]:
    return token_for(client, "admin-1")


@pytest.fixture
def player(client: TestClient) -> dict[str, str]:
    return token_for(client, "jugador-1")


def make_image(width: int, height: int, fmt: str = "PNG") -> bytes:
    img = Image.new("RGB", (width, height), (200, 60, 40))
    out = io.BytesIO()
    img.save(out, format=fmt)
    return out.getvalue()


CARD_PNG = make_image(600, 840)
LOCATION_PNG = make_image(800, 600)


def idem() -> dict[str, str]:
    return {"Idempotency-Key": str(uuid.uuid4())}


def card_form(**overrides: object) -> dict[str, str]:
    form = {
        "name": "Charmander",
        "cost": "2",
        "power": "3",
        "type": "FUEGO",
        "rarity": "COMUN",
        "ability_code": "HAB-000",
    }
    form.update({k: str(v) for k, v in overrides.items() if v is not None})
    for key in [k for k, v in overrides.items() if v is None]:
        form.pop(key, None)
    return form


def create_card(
    client: TestClient,
    headers: dict[str, str],
    image: bytes = CARD_PNG,
    key: str | None = None,
    **overrides: object,
):
    return client.post(
        "/v1/cards",
        data=card_form(**overrides),
        files={"image": ("carta.png", image, "image/png")},
        headers={**headers, "Idempotency-Key": key or str(uuid.uuid4())},
    )


def insert_ability(
    code: str,
    effect: str = "MODIFICAR_PODER",
    trigger: str = "AL_REVELARSE",
    evolution_target: str | None = None,
    affected_type: str | None = None,
) -> None:
    with get_engine().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO abilities (code, name, trigger, effect, target, affected_type, "
                "params, evolution_target) VALUES (:c, :n, :t, :e, 'ESTA_CARTA', :a, "
                "'{\"amount\": 2}', :ev)"
            ),
            {
                "c": code,
                "n": f"Habilidad {code}",
                "t": trigger,
                "e": effect,
                "a": affected_type,
                "ev": evolution_target,
            },
        )


ABBR = {
    "FUEGO": "FUE",
    "AGUA": "AGU",
    "PLANTA": "PLA",
    "ELECTRICO": "ELE",
    "PSIQUICO": "PSI",
    "LUCHA": "LUC",
}


def seed_cards(cards: list[dict[str, object]]) -> list[str]:
    """Inserta cartas directo en la base para preparar escenarios. Devuelve sus códigos."""
    codes = []
    with get_engine().begin() as conn:
        for card in cards:
            seq = conn.execute(
                text(
                    "UPDATE card_code_counters SET last_value = last_value + 1 "
                    "WHERE card_type = :t RETURNING last_value"
                ),
                {"t": card["type"]},
            ).scalar_one()
            code = f"PKA-{ABBR[str(card['type'])]}-{seq:03d}"
            conn.execute(
                text(
                    "INSERT INTO cards (code, seq, name, cost, power, type, rarity, "
                    "ability_code, image_key, thumb_key, image_status) VALUES (:code, :seq, "
                    ":name, :cost, :power, :type, :rarity, :ability, :image, 'x_small.webp', "
                    ":status)"
                ),
                {
                    "code": code,
                    "seq": seq,
                    "ability": card.get("ability", "HAB-000"),
                    "image": card.get("image", "x.png"),
                    "status": card.get("status", "READY"),
                    **{k: card[k] for k in ("name", "cost", "power", "type", "rarity")},
                },
            )
            codes.append(code)
    return codes


TYPES = list(ABBR)


def seed_commons(count: int, **overrides: object) -> list[str]:
    """``count`` cartas Comunes visibles, repartidas entre los seis tipos."""
    return seed_cards(
        [
            {
                "name": f"Común {i}",
                "cost": i % 11,
                "power": i % 7,
                "type": TYPES[i % len(TYPES)],
                "rarity": "COMUN",
                **overrides,
            }
            for i in range(count)
        ]
    )


def login_as(client: TestClient, subject: str) -> dict:
    """Inicia sesión como usuario de prueba y devuelve la respuesta completa."""
    resp = client.post("/v1/dev/tokens", json={"subject": subject})
    assert resp.status_code == 201, resp.text
    return resp.json()


def bearer(session: dict) -> dict[str, str]:
    return {"Authorization": f"Bearer {session['access_token']}"}
