"""US 122 Crear ubicación: criterios de éxito, error y alternos."""

import io
import json
import uuid

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from tests.conftest import LOCATION_PNG, make_image


def location_form(**overrides: object) -> dict[str, str]:
    form: dict[str, object] = {
        "name": "Cascada Celeste",
        "description": "Las cartas de Agua ganan poder.",
        "card_limit": 4,
        "extra_energy_mode": "FIJA",
        "extra_energy_amount": 1,
        "effect_type": "BONIFICACION_POR_TIPO",
        "effect_params": json.dumps({"card_type": "AGUA", "amount": 2}),
    }
    form.update(overrides)
    return {k: str(v) for k, v in form.items() if v is not None}


def create_location(
    client: TestClient,
    headers,
    image: bytes = LOCATION_PNG,
    key: str | None = None,
    **overrides: object,
):
    return client.post(
        "/v1/locations",
        data=location_form(**overrides),
        files={"image": ("u.png", image, "image/png")},
        headers={**headers, "Idempotency-Key": key or str(uuid.uuid4())},
    )


def test_creates_location(client: TestClient, admin) -> None:
    resp = create_location(client, admin)
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["name"] == "Cascada Celeste"
    assert body["card_limit"] == 4
    assert body["extra_energy"] == {"mode": "FIJA", "amount": 1}
    assert body["effect"] == {
        "type": "BONIFICACION_POR_TIPO",
        "params": {"card_type": "AGUA", "amount": 2},
    }
    assert body["assignable_to_matches"] is True
    assert resp.headers["Location"] == f"/v1/locations/{body['id']}"
    small = client.get(body["image"]["small_url"])
    with Image.open(io.BytesIO(small.content)) as img:
        assert img.size == (320, 240)


@pytest.mark.parametrize(
    ("effect_type", "params"),
    [
        ("NINGUNO", None),
        ("BONIFICACION_POR_TIPO", {"card_type": "LUCHA", "amount": -5}),
        ("MODIFICADOR_DE_COSTO", {"amount": -1}),
        ("MODIFICADOR_DE_COSTO", {"amount": 5, "card_type": "PLANTA"}),
        ("RESTRICCION_POR_TURNO", {"turns": [1, 6]}),
    ],
)
def test_accepts_each_effect_type(client: TestClient, admin, effect_type, params) -> None:
    resp = create_location(
        client, admin, effect_type=effect_type, effect_params=json.dumps(params) if params else None
    )
    assert resp.status_code == 201, resp.text


def test_location_limit_zero_and_energy_per_card(client: TestClient, admin) -> None:
    resp = create_location(
        client, admin, card_limit=0, extra_energy_mode="POR_CARTA", extra_energy_amount=2
    )
    assert resp.status_code == 201
    assert resp.json()["extra_energy"] == {"mode": "POR_CARTA", "amount": 2}


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"card_limit": 6}, "card_limit"),
        ({"card_limit": -1}, "card_limit"),
        ({"extra_energy_mode": "DOBLE"}, "extra_energy_mode"),
        ({"extra_energy_mode": "FIJA", "extra_energy_amount": 4}, "extra_energy_amount"),
        ({"extra_energy_mode": "POR_CARTA", "extra_energy_amount": 3}, "extra_energy_amount"),
        ({"effect_type": "TORMENTA"}, "effect_type"),
        (
            {"effect_params": json.dumps({"card_type": "DRAGON", "amount": 2})},
            "effect_params.card_type",
        ),
        ({"effect_params": json.dumps({"card_type": "AGUA"})}, "effect_params.amount"),
        ({"effect_params": json.dumps({"card_type": "AGUA", "amount": 6})}, "effect_params.amount"),
        (
            {"effect_type": "MODIFICADOR_DE_COSTO", "effect_params": json.dumps({"amount": -6})},
            "effect_params.amount",
        ),
        (
            {"effect_type": "RESTRICCION_POR_TURNO", "effect_params": json.dumps({"turns": [7]})},
            "effect_params.turns",
        ),
        ({"effect_type": "RESTRICCION_POR_TURNO", "effect_params": "{}"}, "effect_params.turns"),
        ({"effect_params": "{no es json"}, "effect_params"),
        ({"name": ""}, "name"),
    ],
)
def test_rejects_invalid_configuration(client: TestClient, admin, overrides, field) -> None:
    resp = create_location(client, admin, **overrides)
    assert resp.status_code == 422, resp.text
    assert field in [e["field"] for e in resp.json()["errors"]]


@pytest.mark.parametrize(
    ("image", "reason"),
    [
        (make_image(800, 800), "proporción"),
        (make_image(640, 480), "resolución"),
        (make_image(800, 600, "BMP"), "formato"),
    ],
)
def test_rejects_invalid_image(client: TestClient, admin, image, reason) -> None:
    resp = create_location(client, admin, image=image)
    assert resp.status_code == 422
    assert any(reason in e["reason"] for e in resp.json()["errors"])


def test_retry_does_not_duplicate_location(client: TestClient, admin) -> None:
    key = str(uuid.uuid4())
    first = create_location(client, admin, key=key).json()
    second = create_location(client, admin, key=key).json()
    assert first["id"] == second["id"]


def test_rejects_without_credentials_or_role(client: TestClient, player) -> None:
    assert create_location(client, {}).status_code == 401
    assert create_location(client, player).status_code == 403
