"""La API responde en /health; lo usan Docker Compose y la nube para saber si está viva."""

from fastapi.testclient import TestClient

from pokearena.main import create_app


def test_health_responds_ok() -> None:
    with TestClient(create_app()) as client:
        resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
