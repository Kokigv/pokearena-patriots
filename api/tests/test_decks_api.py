from sqlalchemy import text

from pokearena.shared.db import get_engine


def test_deck_retry_and_owner(client, player, admin):
    owner = client.get("/v1/me", headers=player).json()["subject"]
    cards = [f"C{i}" for i in range(12)]
    with get_engine().begin() as conn:
        conn.execute(
            text("INSERT INTO collection_cards(player_id,card_code,copies) VALUES (:p,:c,1)"),
            [{"p": owner, "c": code} for code in cards],
        )
    headers = {**player, "Idempotency-Key": "retry"}
    body = {"name": "Equipo", "card_codes": cards}
    path = "/v1/me/decks"
    assert client.post(path, json=body).status_code == 401
    for invalid in (cards[:-1], cards + ["EXTRA"], cards[:-1] + [cards[0]], cards[:-1] + ["AJENA"]):
        response = client.post(path, headers=headers, json={**body, "card_codes": invalid})
        assert response.status_code == 422, response.text
    assert client.get(path, headers=player).json() == []
    first = client.post(path, headers=headers, json=body)
    assert first.status_code == 201, first.text
    assert client.post(path, headers=headers, json=body).json() == first.json()
    assert client.post(path, headers=headers, json={**body, "name": "Otro"}).status_code == 409
    assert client.get(path, headers=player).json() == [first.json()]
    assert client.get(path + "/" + first.json()["id"], headers=player).json() == first.json()
    assert client.get(path, headers=admin).json() == []
    assert client.get(path + "/" + first.json()["id"], headers=admin).status_code == 404
