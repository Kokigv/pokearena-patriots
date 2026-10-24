"""Buscar carta con 10.000 cartas: tiempo y tamaño de respuesta acotados (nota del Sprint 1)."""

import statistics
import time

import pytest
from fastapi.testclient import TestClient

from scripts.seed_cards import main as seed_cards

QUERIES = [
    "",
    "name=chu",
    "name=nandu",
    "type=FUEGO",
    "type=AGUA&rarity=RARA",
    "cost_min=3&cost_max=5",
    "power_min=10",
    "name=char&cost=2",
    "code=PKA-ELE",
    "ability_code=HAB-000&limit=100",
]


@pytest.mark.slow
def test_search_stays_fast_with_10000_cards(client: TestClient, admin) -> None:
    seed_cards(10_000)
    timings: list[float] = []
    for _ in range(3):
        for query in QUERIES:
            start = time.perf_counter()
            resp = client.get(f"/v1/cards?{query}", headers=admin)
            timings.append((time.perf_counter() - start) * 1000)
            assert resp.status_code == 200
            assert len(resp.json()["items"]) <= 100
    p95 = statistics.quantiles(timings, n=20)[18]
    print(f"p95 = {p95:.1f} ms sobre {len(timings)} búsquedas")
    assert p95 < 200


@pytest.mark.slow
def test_full_walk_of_10000_cards_has_no_repeats(client: TestClient, admin) -> None:
    seed_cards(10_000)
    seen: set[str] = set()
    cursor = None
    while True:
        url = "/v1/cards?limit=100" + (f"&cursor={cursor}" if cursor else "")
        body = client.get(url, headers=admin).json()
        codes = [c["code"] for c in body["items"]]
        assert not seen.intersection(codes)
        seen.update(codes)
        cursor = body["next_cursor"]
        if not cursor:
            break
    assert len(seen) == 10_000
