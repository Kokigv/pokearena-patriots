"""US 120 Buscar carta: criterios combinables, validación y paginación estable."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from pokearena.shared.db import get_engine
from tests.conftest import insert_ability

ABBR = {
    "FUEGO": "FUE",
    "AGUA": "AGU",
    "PLANTA": "PLA",
    "ELECTRICO": "ELE",
    "PSIQUICO": "PSI",
    "LUCHA": "LUC",
}


def seed(cards: list[dict[str, object]]) -> None:
    """Inserta cartas directo en la base para preparar escenarios de búsqueda."""
    with get_engine().begin() as conn:
        for card in cards:
            seq = conn.execute(
                text(
                    "UPDATE card_code_counters SET last_value = last_value + 1 "
                    "WHERE card_type = :t RETURNING last_value"
                ),
                {"t": card["type"]},
            ).scalar_one()
            conn.execute(
                text(
                    "INSERT INTO cards (code, seq, name, cost, power, type, rarity, "
                    "ability_code, image_key, thumb_key, image_status) VALUES (:code, :seq, "
                    ":name, :cost, :power, :type, :rarity, :ability, 'x.png', 'x_small.webp', "
                    "'READY')"
                ),
                {
                    "code": f"PKA-{ABBR[str(card['type'])]}-{seq:03d}",
                    "seq": seq,
                    "ability": card.get("ability", "HAB-000"),
                    **card,
                },
            )


@pytest.fixture
def catalog() -> None:
    insert_ability("HAB-001", effect="MODIFICAR_PODER", trigger="AL_REVELARSE")
    insert_ability("HAB-002", effect="DESTRUIR", trigger="CONTINUO")
    seed(
        [
            {"name": "Pikachu", "cost": 2, "power": 3, "type": "ELECTRICO", "rarity": "COMUN"},
            {
                "name": "Raichu",
                "cost": 4,
                "power": 7,
                "type": "ELECTRICO",
                "rarity": "RARA",
                "ability": "HAB-001",
            },
            {"name": "Charmander", "cost": 1, "power": 2, "type": "FUEGO", "rarity": "COMUN"},
            {
                "name": "Charizard",
                "cost": 6,
                "power": 12,
                "type": "FUEGO",
                "rarity": "LEGENDARIA",
                "ability": "HAB-002",
            },
            {"name": "Squirtle", "cost": 1, "power": -2, "type": "AGUA", "rarity": "COMUN"},
            {
                "name": "Pokémon Ñandú",
                "cost": 3,
                "power": 4,
                "type": "PLANTA",
                "rarity": "POCO_COMUN",
            },
        ]
    )


def names(resp) -> list[str]:
    assert resp.status_code == 200, resp.text
    return [c["name"] for c in resp.json()["items"]]


def test_search_by_code_prefix(client: TestClient, admin, catalog) -> None:
    assert names(client.get("/v1/cards?code=PKA-FUE", headers=admin)) == ["Charmander", "Charizard"]
    assert names(client.get("/v1/cards?code=pka-ele-002", headers=admin)) == ["Raichu"]


def test_name_is_partial_case_and_accent_insensitive(client: TestClient, admin, catalog) -> None:
    assert names(client.get("/v1/cards?name=CHAR", headers=admin)) == ["Charmander", "Charizard"]
    assert names(client.get("/v1/cards?name=pokemon nandu", headers=admin)) == ["Pokémon Ñandú"]


def test_exact_and_range_filters(client: TestClient, admin, catalog) -> None:
    assert names(client.get("/v1/cards?cost=1", headers=admin)) == ["Squirtle", "Charmander"]
    assert set(names(client.get("/v1/cards?cost_min=3&cost_max=6", headers=admin))) == {
        "Raichu",
        "Charizard",
        "Pokémon Ñandú",
    }
    assert names(client.get("/v1/cards?power_max=0", headers=admin)) == ["Squirtle"]


def test_type_rarity_and_ability_filters(client: TestClient, admin, catalog) -> None:
    assert names(client.get("/v1/cards?type=FUEGO&rarity=LEGENDARIA", headers=admin)) == [
        "Charizard"
    ]
    assert names(client.get("/v1/cards?ability_code=HAB-001", headers=admin)) == ["Raichu"]
    assert len(names(client.get("/v1/cards?ability_code=HAB-000", headers=admin))) == 4
    assert names(client.get("/v1/cards?trigger=CONTINUO&effect=DESTRUIR", headers=admin)) == [
        "Charizard"
    ]


def test_criteria_combine_with_and(client: TestClient, admin, catalog) -> None:
    resp = client.get("/v1/cards?type=ELECTRICO&cost_min=3&name=chu", headers=admin)
    assert names(resp) == ["Raichu"]


def test_result_shows_required_fields(client: TestClient, admin, catalog) -> None:
    card = client.get("/v1/cards?name=raichu", headers=admin).json()["items"][0]
    assert {"code", "name", "image", "cost", "power", "type", "rarity", "ability"} <= card.keys()
    assert card["image"]["status"] == "READY"
    assert card["ability"]["code"] == "HAB-001"
    assert card["ability"]["params"] == {"amount": 2}


def test_no_results_is_empty_list(client: TestClient, admin, catalog) -> None:
    resp = client.get("/v1/cards?type=AGUA&rarity=LEGENDARIA", headers=admin)
    assert resp.status_code == 200
    assert resp.json() == {"items": [], "next_cursor": None}


@pytest.mark.parametrize(
    ("query", "field"),
    [
        ("type=DRAGON", "type"),
        ("rarity=MITICA", "rarity"),
        ("cost=11", "cost"),
        ("power_min=-21", "power_min"),
        ("cost_min=5&cost_max=2", "cost"),
        ("cost=2&cost_min=1", "cost"),
        ("limit=0", "limit"),
        ("limit=101", "limit"),
        ("cursor=no-es-un-cursor", "cursor"),
    ],
)
def test_invalid_criteria_are_rejected(client: TestClient, admin, query, field) -> None:
    resp = client.get(f"/v1/cards?{query}", headers=admin)
    assert resp.status_code == 422, resp.text
    assert field in [e["field"] for e in resp.json()["errors"]]


def test_paging_reaches_every_card_without_repeats(client: TestClient, admin) -> None:
    seed(
        [
            {"name": f"Carta {i}", "cost": i % 11, "power": 1, "type": "AGUA", "rarity": "COMUN"}
            for i in range(25)
        ]
    )
    seen: list[str] = []
    cursor = None
    pages = 0
    while True:
        url = "/v1/cards?limit=10" + (f"&cursor={cursor}" if cursor else "")
        body = client.get(url, headers=admin).json()
        seen += [c["code"] for c in body["items"]]
        pages += 1
        if pages == 1:  # se crean cartas mientras se recorre
            seed([{"name": "Nueva", "cost": 1, "power": 1, "type": "AGUA", "rarity": "COMUN"}])
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert len(seen) == len(set(seen))
    assert {f"PKA-AGU-{n:03d}" for n in range(1, 26)} <= set(seen)
    assert pages == 3


def test_search_without_criteria_is_paged(client: TestClient, admin) -> None:
    seed(
        [
            {"name": f"C{i}", "cost": 1, "power": 1, "type": "LUCHA", "rarity": "COMUN"}
            for i in range(120)
        ]
    )
    body = client.get("/v1/cards", headers=admin).json()
    assert len(body["items"]) == 50
    assert body["next_cursor"]


def test_codes_after_999_keep_numeric_order(client: TestClient, admin) -> None:
    with get_engine().begin() as conn:
        conn.execute(text("UPDATE card_code_counters SET last_value = 997 WHERE card_type='AGUA'"))
    seed(
        [
            {"name": f"A{i}", "cost": 1, "power": 1, "type": "AGUA", "rarity": "COMUN"}
            for i in range(4)
        ]
    )
    body = client.get("/v1/cards?type=AGUA&limit=2", headers=admin).json()
    first = [c["code"] for c in body["items"]]
    rest = client.get(
        f"/v1/cards?type=AGUA&limit=2&cursor={body['next_cursor']}", headers=admin
    ).json()
    assert first + [c["code"] for c in rest["items"]] == [
        "PKA-AGU-998",
        "PKA-AGU-999",
        "PKA-AGU-1000",
        "PKA-AGU-1001",
    ]
