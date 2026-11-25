import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from pokearena.gameplay.api.search import candidate_for
from pokearena.shared.db import get_engine


@pytest.mark.parametrize("action", ["status", "cancel"])
def test_stale_search_expires_and_cannot_match(client, player, admin, action):
    owner = client.get("/v1/me", headers=player).json()["subject"]
    other = client.get("/v1/me", headers=admin).json()["subject"]
    sid = str(uuid.uuid4())
    with Session(get_engine()) as session:
        session.execute(
            text("""INSERT INTO match_searches(id, player_id, deck_id, last_seen_at)
                VALUES (:s, :p, :d, now() - interval '6 minutes')"""),
            {"s": sid, "p": owner, "d": str(uuid.uuid4())},
        )
        session.commit()
        assert (
            candidate_for(session, {"created_at": datetime.now(UTC), "player_id": other}, 0) is None
        )
    path = f"/v1/matches/search/{sid}"
    assert client.get(path, headers=admin).status_code == 404
    response = (
        client.post(path + "/cancel", headers=player)
        if action == "cancel"
        else client.get(path, headers=player)
    )
    assert response.status_code == 200
    assert response.json()["status"] == "EXPIRED"
    assert client.get(path, headers=player).json()["status"] == "EXPIRED"
