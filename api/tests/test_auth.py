"""401 y 403 distinguibles (RNF-SEG-03) e identidad de prueba solo fuera de producción.

Por ahora se prueban sobre /v1/me; las rutas del catálogo se agregan cuando existan.
"""

from datetime import UTC, datetime, timedelta

import jwt
from fastapi.testclient import TestClient

from pokearena.main import create_app
from pokearena.shared.config import Settings, get_settings


def test_without_credentials_is_unauthenticated(client: TestClient) -> None:
    resp = client.get("/v1/me")
    assert resp.status_code == 401
    assert resp.headers["content-type"].startswith("application/problem+json")
    assert resp.json()["type"].endswith("/unauthenticated")


def test_invalid_token_is_unauthenticated(client: TestClient) -> None:
    resp = client.get("/v1/me", headers={"Authorization": "Bearer no-es-un-jwt"})
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
    resp = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401
    assert resp.json()["type"].endswith("/token-expired")


def test_admin_role_comes_from_configuration(client: TestClient, admin, player) -> None:
    assert "admin" in client.get("/v1/me", headers=admin).json()["roles"]
    assert "admin" not in client.get("/v1/me", headers=player).json()["roles"]


def test_test_identity_does_not_exist_in_production() -> None:
    prod = create_app(Settings(app_env="production"))
    with TestClient(prod) as client:
        assert client.post("/v1/dev/tokens", json={"subject": "admin-1"}).status_code == 404
        paths = client.get("/openapi.json").json()["paths"]
        assert not any(p.startswith("/v1/dev") for p in paths)
