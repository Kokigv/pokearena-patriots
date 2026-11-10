"""US 123 Recibir colección inicial: 15 Comunes distintas y 1,000 cubos, todo o nada, una vez."""

import threading
from collections.abc import Sequence

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from pokearena.collection.api.wiring import grant_initial_collection
from pokearena.collection.application.initial_collection import (
    GrantInitialCollection,
    GrantOutcome,
)
from pokearena.collection.domain.initial_collection import (
    DECK_SIZE,
    INITIAL_CARD_COUNT,
    InitialGrant,
    NotEnoughCommonCards,
    choose_initial_grant,
)
from pokearena.collection.infrastructure.sql_collection import SqlCollectionRepository
from pokearena.shared.db import get_engine
from tests.conftest import bearer, login_as, seed_cards, seed_commons


def collection_of(client: TestClient, session: dict) -> dict:
    resp = client.get("/v1/me/collection", headers=bearer(session))
    assert resp.status_code == 200, resp.text
    return resp.json()


def count(sql: str) -> int:
    with get_engine().connect() as conn:
        return conn.execute(text(sql)).scalar_one()


# ---------------------------------------------------------------- Dominio (sin base de datos)


class FirstK:
    """Generador "aleatorio" determinista para probar el dominio."""

    def sample(self, population: Sequence[str], k: int) -> list[str]:
        return list(population)[:k]


def test_domain_chooses_15_distinct_cards_for_a_valid_deck() -> None:
    grant = choose_initial_grant([f"PKA-FUE-{i:03d}" for i in range(40)], FirstK())
    assert len(grant.card_codes) == len(set(grant.card_codes)) == INITIAL_CARD_COUNT
    assert len(grant.card_codes) >= DECK_SIZE
    assert grant.cubes == 1_000


def test_domain_rejects_catalog_with_fewer_than_15_commons() -> None:
    with pytest.raises(NotEnoughCommonCards):
        # Repetidos no cuentan: 14 distintas.
        choose_initial_grant([f"PKA-AGU-{i:03d}" for i in range(14)] * 2, FirstK())


# ---------------------------------------------------------------- Éxito


def test_first_login_grants_15_distinct_commons_and_1000_cubes(client: TestClient) -> None:
    commons = set(seed_commons(30))
    seed_cards(
        [
            {"name": "Rara", "cost": 3, "power": 5, "type": "AGUA", "rarity": "RARA"},
            {"name": "Leyenda", "cost": 9, "power": 15, "type": "FUEGO", "rarity": "LEGENDARIA"},
        ]
    )
    session = login_as(client, "ash")
    assert session["onboarding"]["status"] == "COMPLETED"

    body = collection_of(client, session)
    codes = [c["card_code"] for c in body["cards"]]
    assert body["initial_granted"] is True
    assert body["cubes"] == 1_000
    assert body["distinct_cards"] == len(set(codes)) == 15
    assert set(codes) <= commons  # solo Comunes del catálogo
    assert all(c["copies"] == 1 for c in body["cards"])
    assert len(codes) >= DECK_SIZE  # alcanza para un deck válido de 12


def test_initial_cubes_are_the_first_movement_of_the_history(client: TestClient) -> None:
    seed_commons(15)
    body = collection_of(client, login_as(client, "misty"))
    assert body["cube_movements"][0]["amount"] == 1_000
    assert body["cube_movements"][0]["reason"] == "INITIAL_GRANT"
    assert body["cube_movements"][0]["balance_after"] == body["cubes"] == 1_000


def test_cards_without_ready_image_are_never_granted(client: TestClient) -> None:
    hidden = set(seed_commons(10, status="FAILED"))
    seed_commons(15)
    codes = {c["card_code"] for c in collection_of(client, login_as(client, "brock"))["cards"]}
    assert not codes & hidden


def test_selection_is_random_on_the_server(client: TestClient) -> None:
    seed_commons(60)
    picks = {
        frozenset(c["card_code"] for c in collection_of(client, login_as(client, f"j{i}"))["cards"])
        for i in range(5)
    }
    assert len(picks) > 1  # 5 jugadores con 60 opciones: no reciben todos las mismas


# ---------------------------------------------------------------- Errores


def test_failed_delivery_leaves_nothing_and_completes_on_next_login(client: TestClient) -> None:
    seed_commons(15)
    session = login_as(client, "gary")
    player_id = session["player"]["id"]
    # Simula una falla a mitad de la entrega: un código inválido hace fallar el INSERT de las
    # cartas después de crear la billetera.
    with Session(get_engine()) as db:
        repo = SqlCollectionRepository(db)
        db.execute(text("DELETE FROM player_wallets WHERE player_id = :p"), {"p": player_id})
        db.execute(text("DELETE FROM collection_cards WHERE player_id = :p"), {"p": player_id})
        db.execute(text("DELETE FROM cube_movements WHERE player_id = :p"), {"p": player_id})
        db.commit()
        broken = InitialGrant(card_codes=("PKA-FUE-001", "X" * 50))
        with pytest.raises(Exception):  # noqa: B017
            repo.grant_initial(player_id, broken)
    empty = collection_of(client, session)
    assert empty == {
        "initial_granted": False,
        "cubes": 0,
        "distinct_cards": 0,
        "cards": [],
        "cube_movements": [],
    }
    login_as(client, "gary")  # siguiente ingreso
    body = collection_of(client, session)
    assert body["distinct_cards"] == 15 and body["cubes"] == 1_000


def test_use_case_reports_failure_without_breaking_login() -> None:
    class Exploding(SqlCollectionRepository):
        def grant_initial(self, player_id: str, grant: InitialGrant) -> bool:
            raise RuntimeError("base de datos caída")

    seed_commons(15)
    with Session(get_engine()) as db:
        base = grant_initial_collection(db)
        use_case = GrantInitialCollection(base._catalog, Exploding(db), base._random)
        outcome = use_case.execute("00000000-0000-0000-0000-000000000001")
    assert outcome is GrantOutcome.FAILED


def test_fewer_than_15_commons_creates_account_without_collection(client: TestClient) -> None:
    seed_commons(14)
    session = login_as(client, "tracey")
    assert session["first_login"] is True
    assert session["onboarding"]["status"] == "PENDING_CATALOG"
    assert "aún no está disponible" in session["onboarding"]["message"]
    body = collection_of(client, session)
    assert body["initial_granted"] is False and body["cubes"] == 0 and body["cards"] == []

    seed_commons(1)  # ya hay 15 Comunes
    again = login_as(client, "tracey")
    assert again["onboarding"]["status"] == "COMPLETED"
    assert collection_of(client, again)["distinct_cards"] == 15


def test_client_data_does_not_influence_the_cards(client: TestClient) -> None:
    seed_commons(15)
    resp = client.post(
        "/v1/dev/tokens",
        json={"subject": "hacker", "cards": ["PKA-LEG-001"], "cubes": 999_999},
    )
    assert resp.status_code == 201
    body = collection_of(client, resp.json())
    assert body["cubes"] == 1_000
    assert "PKA-LEG-001" not in {c["card_code"] for c in body["cards"]}


# ---------------------------------------------------------------- Alternos


def test_later_logins_do_not_grant_again(client: TestClient) -> None:
    seed_commons(40)
    first = collection_of(client, login_as(client, "dawn"))
    for _ in range(3):
        login_as(client, "dawn")
    again = collection_of(client, login_as(client, "dawn"))
    assert again == first
    assert count("SELECT count(*) FROM cube_movements") == 1


def test_two_simultaneous_first_logins_grant_exactly_once(client: TestClient) -> None:
    seed_commons(40)
    player_id = login_as(client, "racer")["player"]["id"]
    with get_engine().begin() as conn:  # deja la cuenta sin colección para la carrera
        conn.execute(text("TRUNCATE player_wallets, collection_cards, cube_movements"))

    barrier = threading.Barrier(6)
    outcomes: list[GrantOutcome] = []

    def worker() -> None:
        with Session(get_engine()) as db:
            barrier.wait()
            outcomes.append(grant_initial_collection(db).execute(player_id))

    threads = [threading.Thread(target=worker) for _ in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert outcomes.count(GrantOutcome.GRANTED) == 1
    assert count("SELECT count(*) FROM player_wallets") == 1
    assert count("SELECT count(*) FROM collection_cards") == 15
    assert count("SELECT count(*) FROM cube_movements") == 1
    assert count("SELECT sum(cubes) FROM player_wallets") == 1_000
