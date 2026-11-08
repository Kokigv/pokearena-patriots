"""US 116 Inicio de sesión con proveedor: Google valida una vez y PokéArena emite su credencial.

Las pruebas no llaman a Google (RNF-PRU-05): firman ID tokens con una llave RSA local y el
adaptador real ``GoogleIdentityProvider`` los valida contra esa llave pública.
"""

import threading
import time
from collections.abc import Iterator
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from pokearena.identity.api.dependencies import get_google_provider
from pokearena.identity.domain.player import ExternalIdentity
from pokearena.identity.infrastructure.providers import GoogleIdentityProvider
from pokearena.identity.infrastructure.sql_players import SqlPlayerRepository
from pokearena.main import create_app
from pokearena.shared.config import get_settings
from pokearena.shared.db import get_engine

CLIENT_ID = "pokearena-test.apps.googleusercontent.com"
GOOGLE_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)
OTHER_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


class LocalKeys:
    """Hace el papel de las llaves públicas de Google (en producción, ``PyJWKClient``)."""

    def __init__(self, available: bool = True) -> None:
        self.available = available

    def get_signing_key_from_jwt(self, token: str) -> Any:
        if not self.available:
            raise jwt.PyJWKClientConnectionError("no se pudo conectar con Google")
        jwt.get_unverified_header(token)  # lanza DecodeError si no es un JWT
        return GOOGLE_KEY.public_key()


def google_token(
    sub: str = "google-123",
    email: str = "ash@example.com",
    name: str = "Ash Ketchum",
    aud: str = CLIENT_ID,
    iss: str = "https://accounts.google.com",
    expires_in: int = 3600,
    key: Any = GOOGLE_KEY,
) -> str:
    now = int(time.time())
    claims = {
        "iss": iss,
        "sub": sub,
        "aud": aud,
        "email": email,
        "email_verified": True,
        "name": name,
        "iat": now - 10,
        "exp": now + expires_in,
    }
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "test"})


@pytest.fixture
def keys() -> LocalKeys:
    return LocalKeys()


@pytest.fixture
def google(keys: LocalKeys) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_google_provider] = lambda: GoogleIdentityProvider(CLIENT_ID, keys)
    with TestClient(app) as c:
        yield c


def login(client: TestClient, token: str):
    return client.post("/v1/auth/google", json={"id_token": token})


def player_count() -> int:
    with get_engine().connect() as conn:
        return conn.execute(text("SELECT count(*) FROM players")).scalar_one()


# ---------------------------------------------------------------- Éxito


def test_valid_token_creates_player_and_returns_own_credentials(google: TestClient) -> None:
    resp = login(google, google_token())
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["first_login"] is True
    assert body["player"]["role"] == "player"
    assert body["player"]["elo"] == 0
    assert body["player"]["display_name"] == "Ash Ketchum"
    assert body["player"]["is_test"] is False
    # Expiración corta (15 minutos por defecto).
    assert body["expires_in"] == get_settings().access_token_minutes * 60 <= 3600
    claims = jwt.decode(body["access_token"], options={"verify_signature": False})
    assert claims["iss"] == "pokearena"
    assert claims["sub"] == body["player"]["id"]


def test_later_logins_reuse_the_same_account(google: TestClient) -> None:
    first = login(google, google_token()).json()
    second = login(google, google_token()).json()
    assert second["first_login"] is False
    assert second["player"]["id"] == first["player"]["id"]
    assert player_count() == 1


def test_api_is_authorized_with_pokearena_credentials_not_google_token(
    google: TestClient,
) -> None:
    session = login(google, google_token()).json()
    me = google.get("/v1/me", headers={"Authorization": f"Bearer {session['access_token']}"})
    assert me.status_code == 200
    assert me.json()["player"]["id"] == session["player"]["id"]
    # El token de Google no sirve para llamar a la API.
    raw = google.get("/v1/me", headers={"Authorization": f"Bearer {google_token()}"})
    assert raw.status_code == 401
    assert raw.json()["type"].endswith("/unauthenticated")


# ---------------------------------------------------------------- Errores


@pytest.mark.parametrize(
    ("token", "reason"),
    [
        (google_token(expires_in=-60), "expiró"),
        (google_token(aud="otra-app.apps.googleusercontent.com"), "otra aplicación"),
        (google_token(iss="https://evil.example.com"), "no fue emitido por Google"),
        (google_token(key=OTHER_KEY), "firma"),
        ("no-es-un-jwt", "formato"),
        ("aaa.bbb.ccc", "no fue firmado por Google"),
    ],
)
def test_invalid_tokens_are_rejected_without_creating_accounts(
    google: TestClient, token: str, reason: str
) -> None:
    resp = login(google, token)
    assert resp.status_code == 401, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["type"].endswith("/invalid-provider-token")
    assert reason in resp.json()["detail"]
    assert player_count() == 0


def test_provider_unavailable_gives_descriptive_error_and_no_account(
    google: TestClient, keys: LocalKeys
) -> None:
    keys.available = False
    resp = login(google, google_token())
    assert resp.status_code == 503
    assert resp.json()["type"].endswith("/identity-provider-unavailable")
    assert "no está disponible" in resp.json()["detail"]
    assert player_count() == 0


def test_missing_id_token_is_a_validation_error(google: TestClient) -> None:
    resp = google.post("/v1/auth/google", json={})
    assert resp.status_code == 422


# ---------------------------------------------------------------- Alternos


def test_changing_email_at_provider_keeps_the_account(google: TestClient) -> None:
    first = login(google, google_token(email="ash@kanto.com")).json()
    second = login(google, google_token(email="ash@johto.com")).json()
    assert second["player"]["id"] == first["player"]["id"]
    assert second["player"]["email"] == "ash@johto.com"
    assert player_count() == 1


def test_two_simultaneous_first_logins_create_exactly_one_account() -> None:
    identity = ExternalIdentity("google", "google-race", "race@example.com", "Race")
    barrier = threading.Barrier(8)
    ids: list[str] = []

    def worker() -> None:
        with Session(get_engine()) as session:
            barrier.wait()
            player, _ = SqlPlayerRepository(session).get_or_create(identity)
            ids.append(player.id)

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(set(ids)) == 1
    assert player_count() == 1


def test_another_provider_uses_the_same_authorization(google: TestClient) -> None:
    """Agregar un proveedor (aquí, el de prueba) no cambia cómo se autoriza la API."""
    from_google = login(google, google_token(sub="mismo-sujeto")).json()
    from_test = google.post("/v1/dev/tokens", json={"subject": "mismo-sujeto"}).json()
    assert from_google["player"]["id"] != from_test["player"]["id"]  # proveedores distintos
    for session in (from_google, from_test):
        headers = {"Authorization": f"Bearer {session['access_token']}"}
        assert google.get("/v1/me", headers=headers).status_code == 200


def test_google_login_without_client_id_is_unavailable(keys: LocalKeys) -> None:
    app = create_app()
    app.dependency_overrides[get_google_provider] = lambda: GoogleIdentityProvider(None, keys)
    with TestClient(app) as client:
        resp = login(client, google_token())
    assert resp.status_code == 503
    assert player_count() == 0
