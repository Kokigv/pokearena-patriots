"""US 119 Crear carta: criterios de éxito, error y alternos."""

import io
import os
import re
import threading
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from PIL import Image
from redis import Redis

from pokearena.catalog.application import images as images_module
from pokearena.catalog.domain.ability import Ability, evolution_problem
from pokearena.catalog.domain.enums import EffectKind, Trigger
from tests.conftest import CARD_PNG, create_card, insert_ability, make_image


def test_creates_card_with_all_fields(client: TestClient, admin) -> None:
    resp = create_card(client, admin, name="Charmander", cost=2, power=3)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["code"] == "PKA-FUE-001"
    assert resp.headers["Location"] == "/v1/cards/PKA-FUE-001"
    assert (body["name"], body["cost"], body["power"]) == ("Charmander", 2, 3)
    assert (body["type"], body["rarity"]) == ("FUEGO", "COMUN")
    assert body["ability"]["code"] == "HAB-000"
    assert body["image"]["status"] == "READY"
    assert body["available_to_players"] is True


def test_code_format_and_sequence_per_type(client: TestClient, admin) -> None:
    codes = [
        create_card(client, admin, type=t).json()["code"]
        for t in ["FUEGO", "AGUA", "FUEGO", "PLANTA", "ELECTRICO", "PSIQUICO", "LUCHA"]
    ]
    assert codes == [
        "PKA-FUE-001",
        "PKA-AGU-001",
        "PKA-FUE-002",
        "PKA-PLA-001",
        "PKA-ELE-001",
        "PKA-PSI-001",
        "PKA-LUC-001",
    ]
    assert all(re.fullmatch(r"PKA-(FUE|AGU|PLA|ELE|PSI|LUC)-\d{3,}", c) for c in codes)


def test_generates_small_version_of_200x280(client: TestClient, admin) -> None:
    body = create_card(client, admin).json()
    small = client.get(body["image"]["small_url"])
    assert small.status_code == 200
    with Image.open(io.BytesIO(small.content)) as img:
        assert img.size == (200, 280)
    large = client.get(body["image"]["url"])
    with Image.open(io.BytesIO(large.content)) as img:
        assert img.size == (600, 840)


@pytest.mark.parametrize("fmt", ["PNG", "JPEG", "WEBP"])
def test_accepts_png_jpg_and_webp(client: TestClient, admin, fmt: str) -> None:
    assert create_card(client, admin, image=make_image(600, 840, fmt)).status_code == 201


def test_accepts_boundary_values(client: TestClient, admin) -> None:
    for cost, power in [(0, -20), (10, 20)]:
        assert create_card(client, admin, cost=cost, power=power).status_code == 201


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cost", -1),
        ("cost", 11),
        ("cost", "dos"),
        ("power", -21),
        ("power", 21),
        ("type", "DRAGON"),
        ("rarity", "MITICA"),
        ("name", ""),
    ],
)
def test_rejects_invalid_field(client: TestClient, admin, field: str, value: object) -> None:
    resp = create_card(client, admin, **{field: value})
    assert resp.status_code == 422
    assert resp.json()["type"].endswith("/validation-error")
    assert field in [e["field"] for e in resp.json()["errors"]]


def test_rejects_card_without_ability(client: TestClient, admin) -> None:
    resp = create_card(client, admin, ability_code=None)
    assert resp.status_code == 422
    error = resp.json()["errors"][0]
    assert error["field"] == "ability_code"
    assert "Sin Habilidad" in error["reason"]


def test_rejects_unknown_ability(client: TestClient, admin) -> None:
    resp = create_card(client, admin, ability_code="HAB-999")
    assert resp.status_code == 422
    assert resp.json()["type"].endswith("/ability-not-found")


def test_card_sheet_shows_ability_and_affected_type(client: TestClient, admin) -> None:
    insert_ability("HAB-001", affected_type="AGUA")
    body = create_card(client, admin, ability_code="HAB-001").json()
    assert body["ability"]["code"] == "HAB-001"
    assert body["ability"]["affected_type"] == "AGUA"


@pytest.mark.parametrize(
    ("image", "reason"),
    [
        (b"esto no es una imagen", "formato"),
        (make_image(600, 840, "GIF"), "formato"),
        (make_image(600, 600), "proporción"),
        (make_image(500, 700), "resolución"),
    ],
)
def test_rejects_invalid_image(client: TestClient, admin, image: bytes, reason: str) -> None:
    resp = create_card(client, admin, image=image)
    assert resp.status_code == 422
    assert any(reason in e["reason"] for e in resp.json()["errors"])
    assert create_card(client, admin).json()["code"] == "PKA-FUE-001"  # no se guardó nada


def test_rejects_image_over_5_mb(client: TestClient, admin) -> None:
    big = make_image(600, 840) + os.urandom(5 * 1024 * 1024)
    resp = create_card(client, admin, image=big)
    assert resp.status_code == 422
    assert "5 MB" in resp.json()["errors"][0]["reason"]


def test_retry_with_same_key_does_not_duplicate_nor_consume_code(client: TestClient, admin) -> None:
    key = str(uuid.uuid4())
    first = create_card(client, admin, key=key)
    second = create_card(client, admin, key=key)
    assert first.status_code == second.status_code == 201
    assert first.json()["code"] == second.json()["code"] == "PKA-FUE-001"
    assert second.headers.get("Idempotent-Replayed") == "true"
    assert second.headers["Location"] == first.headers["Location"]
    assert create_card(client, admin).json()["code"] == "PKA-FUE-002"


def test_retry_after_losing_redis_still_does_not_duplicate(client: TestClient, admin) -> None:
    key = str(uuid.uuid4())
    first = create_card(client, admin, key=key)
    Redis.from_url(os.environ["REDIS_URL"]).flushdb()  # se pierde la caché de idempotencia
    second = create_card(client, admin, key=key)
    assert second.json()["code"] == first.json()["code"]
    assert create_card(client, admin).json()["code"] == "PKA-FUE-002"


def test_same_key_with_different_request_is_rejected(client: TestClient, admin) -> None:
    key = str(uuid.uuid4())
    create_card(client, admin, key=key, name="Charmander")
    resp = create_card(client, admin, key=key, name="Vulpix")
    assert resp.status_code == 422
    assert resp.json()["type"].endswith("/idempotency-key-reused")


def test_requires_idempotency_key(client: TestClient, admin) -> None:
    resp = client.post(
        "/v1/cards",
        data={"name": "X"},
        headers=admin,
        files={"image": ("c.png", CARD_PNG, "image/png")},
    )
    assert resp.status_code == 422
    assert resp.json()["errors"][0]["field"] == "Idempotency-Key"


def test_concurrent_admins_get_distinct_codes(client: TestClient, admin) -> None:
    results: list[str] = []

    def worker() -> None:
        resp = create_card(client, admin, type="AGUA")
        results.append(resp.json()["code"])

    threads = [threading.Thread(target=worker) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sorted(results) == [f"PKA-AGU-{n:03d}" for n in range(1, 9)]


def test_failed_small_version_hides_card_and_can_be_retried(
    client: TestClient, admin, monkeypatch: pytest.MonkeyPatch
) -> None:
    from pokearena.catalog.infrastructure.pillow_images import PillowImageProcessor

    original = PillowImageProcessor.thumbnail

    def broken(self, data: bytes, width: int, height: int) -> bytes:
        raise OSError("disco lleno")

    monkeypatch.setattr(PillowImageProcessor, "thumbnail", broken)
    body = create_card(client, admin).json()
    assert body["image"]["status"] == "FAILED"
    assert body["image"]["small_url"] is None
    assert body["available_to_players"] is False
    assert images_module.THUMBNAIL_ATTEMPTS == 3  # se reintentó antes de marcar FAILED

    status = client.get(f"/v1/cards/{body['code']}", headers=admin).json()["image"]["status"]
    assert status == "FAILED"  # el administrador ve el estado de la imagen

    monkeypatch.setattr(PillowImageProcessor, "thumbnail", original)
    retried = client.post(f"/v1/cards/{body['code']}/image/retry", headers=admin).json()
    assert retried["image"]["status"] == "READY"
    assert retried["available_to_players"] is True


def test_rejects_evolution_ability_that_closes_a_cycle(client: TestClient, admin) -> None:
    # A (PKA-FUE-001) evoluciona a B (PKA-FUE-002) y B evoluciona a A: ciclo.
    a = create_card(client, admin).json()["code"]
    b = create_card(client, admin).json()["code"]
    insert_ability("HAB-001", effect="EVOLUCIONAR", trigger="CONTINUO", evolution_target=b)
    insert_ability("HAB-002", effect="EVOLUCIONAR", trigger="CONTINUO", evolution_target=a)
    from sqlalchemy import text

    from pokearena.shared.db import get_engine

    with get_engine().begin() as conn:
        conn.execute(text("UPDATE cards SET ability_code='HAB-001' WHERE code=:a"), {"a": a})
        conn.execute(text("UPDATE cards SET ability_code='HAB-002' WHERE code=:b"), {"b": b})
    # Una carta nueva que evoluciona hacia A entraría en la cadena A -> B -> A.
    insert_ability("HAB-003", effect="EVOLUCIONAR", trigger="CONTINUO", evolution_target=a)
    resp = create_card(client, admin, ability_code="HAB-003")
    assert resp.status_code == 422
    assert "ciclo" in resp.json()["errors"][0]["reason"]


def _evo(code: str, target: str) -> Ability:
    return Ability(code, code, Trigger.CONTINUO, EffectKind.EVOLUCIONAR, evolution_target=target)


def test_evolution_rules_in_domain() -> None:
    abilities_by_card = {"B": _evo("HAB-B", "A")}
    lookup = abilities_by_card.get
    assert evolution_problem("A", _evo("HAB-A", "A"), lookup) == (
        "una carta no puede evolucionar en sí misma"
    )
    assert evolution_problem("A", _evo("HAB-A", "B"), lookup) == (
        "las evoluciones forman un ciclo entre cartas"
    )
    assert evolution_problem("C", _evo("HAB-C", "B"), {}.get) is None


def test_images_are_written_to_storage(client: TestClient, admin) -> None:
    create_card(client, admin)
    stored = list(Path(os.environ["STORAGE_LOCAL_PATH"]).rglob("*_small.webp"))
    assert stored
