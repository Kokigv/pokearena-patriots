"""401 y 403 distinguibles (RNF-SEG-03) e identidad de prueba solo fuera de producción."""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from pokearena.main import create_app
from pokearena.shared.config import Settings, get_settings
from tests.conftest import CARD_PNG, LOCATION_PNG, idem

PROTECTED = [
    ("post", "/v1/cards"),
    ("get", "/v1/cards"),
    ("post", "/v1/locations"),
    ("get", "/v1/abilities"),
]


def _call(client: TestClient, method: str, path: str, headers: dict[str, str]):
    if method == "get":
        return client.get(path, headers=headers)
    image = CARD_PNG if "cards" in path else LOCATION_PNG
    return client.post(
        path, files={"image": ("i.png", image, "image/png")}, headers={**headers, **idem()}
    )


def test_without_credentials_is_unauthenticated(client: TestClient) -> None:
    for method, path in PROTECTED:
        resp = _call(client, method, path, {})
        assert resp.status_code == 401, path
        assert resp.headers["content-type"].startswith("application/problem+json")
        assert resp.json()["type"].endswith("/unauthenticated")


def test_invalid_token_is_unauthenticated(client: TestClient) -> None:
    resp = client.get("/v1/cards", headers={"Authorization": "Bearer no-es-un-jwt"})
    assert resp.status_code == 401
    assert resp.json()["type"].endswith("/unauthenticated")


def test_expired_token_says_to_renew(client: TestClient) -> None:
    settings = get_settings()
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode(
        {"sub": "admin-1", "iss": settings.jwt_issuer, "iat": past, "exp": past},
        settings.jwt_secret,
        algorithm="HS256",
    )
    resp = client.get("/v1/cards", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["type"].endswith("/token-expired")


def test_player_without_admin_role_is_forbidden(client: TestClient, player) -> None:
    for method, path in PROTECTED:
        resp = _call(client, method, path, player)
        assert resp.status_code == 403, path
        assert resp.json()["type"].endswith("/forbidden")


def test_admin_role_comes_from_configuration(client: TestClient, admin, player) -> None:
    assert "admin" in client.get("/v1/me", headers=admin).json()["roles"]
    assert "admin" not in client.get("/v1/me", headers=player).json()["roles"]


def test_test_identity_does_not_exist_in_production() -> None:
    prod = create_app(Settings(app_env="production"))
    with TestClient(prod) as client:
        assert client.post("/v1/dev/tokens", json={"subject": "admin-1"}).status_code == 404
        paths = client.get("/openapi.json").json()["paths"]
        assert not any(p.startswith("/v1/dev") for p in paths)
