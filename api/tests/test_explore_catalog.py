"""US 124 Explorar el catálogo y mi colección."""

import json
import statistics
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from redis import Redis
from redis.exceptions import ConnectionError as RedisConnectionError

from pokearena.catalog.application.facade import (
    BrowseFilters,
    CatalogCard,
    CatalogPage,
    parse_browse_filters,
)
from pokearena.collection.infrastructure.cached_catalog import CachedCatalogReader
from pokearena.shared.config import get_settings
from scripts.seed_cards import main as seed_10000
from tests.conftest import bearer, insert_ability, login_as, seed_cards, seed_commons


@pytest.fixture
def ash(client: TestClient) -> dict:
    """Jugador con su colección inicial (15 de las 20 Comunes) en un catálogo variado."""
    insert_ability("HAB-001")
    seed_commons(20)
    seed_cards(
        [
            {"name": "Raichu", "cost": 4, "power": 7, "type": "ELECTRICO", "rarity": "RARA"},
            {
                "name": "Charizard",
                "cost": 6,
                "power": 12,
                "type": "FUEGO",
                "rarity": "LEGENDARIA",
                "ability": "HAB-001",
            },
            {
                "name": "Oculta",
                "cost": 1,
                "power": 1,
                "type": "AGUA",
                "rarity": "RARA",
                "status": "FAILED",
            },
        ]
    )
    session = login_as(client, "ash")
    assert session["onboarding"]["status"] == "COMPLETED"
    return session


def page(client: TestClient, session: dict, query: str = "") -> dict:
    resp = client.get(f"/v1/catalog?{query}", headers=bearer(session))
    assert resp.status_code == 200, resp.text
    return resp.json()


def owned_codes(client: TestClient, session: dict) -> set[str]:
    body = client.get("/v1/me/collection", headers=bearer(session)).json()
    return {c["card_code"] for c in body["cards"]}


# ---------------------------------------------------------------- Éxito


def test_catalog_is_paginated_with_all_card_fields(client: TestClient, ash: dict) -> None:
    first = page(client, ash, "limit=10")
    assert len(first["items"]) == 10 and first["next_cursor"]
    card = first["items"][0]
    assert {
        "code",
        "name",
        "image_url",
        "cost",
        "power",
        "type",
        "rarity",
        "ability",
        "owned",
        "copies",
    } <= card.keys()
    seen = [c["code"] for c in first["items"]]
    cursor = first["next_cursor"]
    while cursor:
        nxt = page(client, ash, f"limit=10&cursor={cursor}")
        seen += [c["code"] for c in nxt["items"]]
        cursor = nxt["next_cursor"]
    assert len(seen) == len(set(seen)) == 22  # 20 Comunes + 2 visibles; la FAILED no aparece


def test_each_card_says_if_the_player_owns_it(client: TestClient, ash: dict) -> None:
    mine = owned_codes(client, ash)
    items = page(client, ash, "limit=100")["items"]
    for card in items:
        assert card["owned"] is (card["code"] in mine)
        assert card["copies"] == (1 if card["code"] in mine else 0)
    assert sum(c["owned"] for c in items) == 15


def test_owned_filter_shows_only_my_cards(client: TestClient, ash: dict) -> None:
    items = page(client, ash, "owned=true&limit=100")["items"]
    assert {c["code"] for c in items} == owned_codes(client, ash)
    assert all(c["owned"] and c["copies"] == 1 for c in items)


def test_type_and_cost_filters_combine(client: TestClient, ash: dict) -> None:
    items = page(client, ash, "type=FUEGO&cost_min=2&cost_max=8&limit=100")["items"]
    assert items
    assert all(c["type"] == "FUEGO" and 2 <= c["cost"] <= 8 for c in items)
    exact = page(client, ash, "type=ELECTRICO&cost=4")["items"]
    assert "Raichu" in [c["name"] for c in exact]
    assert all(c["type"] == "ELECTRICO" and c["cost"] == 4 for c in exact)
    combined = page(client, ash, "owned=true&type=AGUA&limit=100")["items"]
    assert all(c["type"] == "AGUA" and c["owned"] for c in combined)


def test_catalog_shows_the_large_image_and_the_ability(client: TestClient, ash: dict) -> None:
    items = page(client, ash, "type=FUEGO&cost=6")["items"]
    charizard = next(c for c in items if c["name"] == "Charizard")
    assert charizard["image_url"] == "/v1/images/x.png"  # no la versión pequeña
    assert charizard["ability"]["code"] == "HAB-001"


def test_any_player_can_explore_but_must_be_authenticated(client: TestClient, ash: dict) -> None:
    assert client.get("/v1/catalog").status_code == 401
    admin = login_as(client, "admin-1")
    assert client.get("/v1/catalog", headers=bearer(admin)).status_code == 200


# ---------------------------------------------------------------- Errores


@pytest.mark.parametrize(
    ("query", "field", "reason"),
    [
        ("type=DRAGON", "type", "FUEGO, AGUA, PLANTA, ELECTRICO, PSIQUICO, LUCHA"),
        ("cost=11", "cost", "entre 0 y 10"),
        ("cost_min=-1", "cost_min", "entre 0 y 10"),
        ("cost_min=5&cost_max=2", "cost", "mínimo no puede ser mayor"),
        ("limit=0", "limit", "entre 1 y 100"),
        ("limit=500", "limit", "entre 1 y 100"),
        ("cursor=@@@", "cursor", "cursor inválido"),
    ],
)
def test_invalid_filters_and_pagination_are_rejected_with_allowed_values(
    client: TestClient, ash: dict, query: str, field: str, reason: str
) -> None:
    resp = client.get(f"/v1/catalog?{query}", headers=bearer(ash))
    assert resp.status_code == 422, resp.text
    assert resp.headers["content-type"].startswith("application/problem+json")
    errors = {e["field"]: e["reason"] for e in resp.json()["errors"]}
    assert reason in errors[field]


@pytest.mark.parametrize("query", ["limit=abc", "cost=barato", "owned=quizas"])
def test_malformed_parameters_are_a_validation_error_not_a_server_error(
    client: TestClient, ash: dict, query: str
) -> None:
    resp = client.get(f"/v1/catalog?{query}", headers=bearer(ash))
    assert resp.status_code == 422


# ---------------------------------------------------------------- Alternos


def test_filters_without_results_return_an_empty_list(client: TestClient, ash: dict) -> None:
    assert page(client, ash, "type=LUCHA&cost=10") == {
        "items": [],
        "next_cursor": None,
    }


def test_player_without_collection_sees_catalog_but_nothing_owned(client: TestClient) -> None:
    seed_commons(5)  # menos de 15: el jugador entra sin colección
    session = login_as(client, "nuevo")
    items = page(client, session)["items"]
    assert len(items) == 5 and not any(c["owned"] for c in items)
    assert page(client, session, "owned=true")["items"] == []


# ---------------------------------------------------------------- Caché


class CountingCatalog:
    def __init__(self) -> None:
        self.calls = 0

    def playable_common_codes(self) -> list[str]:
        self.calls += 1
        return ["PKA-FUE-001"]

    def browse(self, filters: BrowseFilters, only_codes: frozenset[str] | None) -> CatalogPage:
        self.calls += 1
        card = CatalogCard("PKA-FUE-001", "Charmander", 1, 2, "FUEGO", "COMUN", "x.png", None)
        return CatalogPage([card], None)


class BrokenRedis:
    def get(self, key: str) -> Any:
        raise RedisConnectionError("caído")

    def set(self, *args: Any, **kwargs: Any) -> Any:
        raise RedisConnectionError("caído")


def test_cache_serves_repeated_catalog_pages_until_they_expire() -> None:
    redis = Redis.from_url(get_settings().redis_url)
    inner = CountingCatalog()
    cached = CachedCatalogReader(inner, redis, ttl_seconds=30)
    filters = parse_browse_filters(type="FUEGO")
    first = cached.browse(filters, None)
    second = cached.browse(filters, None)
    assert first == second and inner.calls == 1
    assert cached.playable_common_codes() == cached.playable_common_codes()
    assert inner.calls == 2
    keys = redis.keys("cache:catalog:v1:*")
    assert len(keys) == 2 and all(0 < redis.ttl(k) <= 30 for k in keys)
    json.loads(redis.get(keys[0]))  # se guarda como JSON legible


def test_cache_never_stores_a_players_own_collection() -> None:
    inner = CountingCatalog()
    cached = CachedCatalogReader(inner, Redis.from_url(get_settings().redis_url), 30)
    filters = parse_browse_filters()
    cached.browse(filters, frozenset({"PKA-FUE-001"}))
    cached.browse(filters, frozenset({"PKA-FUE-001"}))
    assert inner.calls == 2


def test_catalog_still_works_when_redis_is_down() -> None:
    inner = CountingCatalog()
    cached = CachedCatalogReader(inner, BrokenRedis(), ttl_seconds=30)
    assert cached.browse(parse_browse_filters(), None).items[0].code == "PKA-FUE-001"
    assert cached.playable_common_codes() == ["PKA-FUE-001"]


# ---------------------------------------------------------------- 10.000 cartas


@pytest.mark.slow
def test_exploring_10000_cards_stays_fast(client: TestClient) -> None:
    seed_10000(10_000)
    session = login_as(client, "competitivo")
    assert session["onboarding"]["status"] == "COMPLETED"
    queries = [
        "",
        "type=AGUA",
        "cost=3",
        "type=FUEGO&cost_min=2&cost_max=5",
        "owned=true",
        "owned=true&type=PLANTA",
        "limit=100",
    ]
    timings: list[float] = []
    for _ in range(3):
        for query in queries:
            start = time.perf_counter()
            body = page(client, session, query)
            timings.append((time.perf_counter() - start) * 1000)
            assert len(body["items"]) <= 100
    p95 = statistics.quantiles(timings, n=20)[18]
    print(f"p95 = {p95:.1f} ms sobre {len(timings)} consultas del catálogo")
    assert p95 < 200
