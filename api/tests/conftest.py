"""Fixtures comunes de las pruebas de la API."""

import os
import tempfile
from collections.abc import Generator

os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/pokearena_test"
)
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ["APP_ENV"] = "test"
os.environ["ADMIN_SUBJECTS"] = "admin-1,admin-2"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["STORAGE_LOCAL_PATH"] = tempfile.mkdtemp(prefix="pokearena-img-")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from pokearena.main import create_app  # noqa: E402


@pytest.fixture
def client() -> Generator[TestClient]:
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
