"""Reglas deterministas reutilizables de Deck y arranque de partidas."""

from random import Random


class RuleViolation(ValueError):
    pass


def validate_deck(cards: list[str], owned: set[str]) -> None:
    if len(cards) != 12:
        raise RuleViolation(f"El deck requiere exactamente 12 cartas; se recibieron {len(cards)}")
    duplicates = sorted({c for c in cards if cards.count(c) > 1})
    if duplicates:
        raise RuleViolation(f"Cartas repetidas: {', '.join(duplicates)}")
    missing = sorted(set(cards) - owned)
    if missing:
        raise RuleViolation(f"Cartas no poseídas: {', '.join(missing)}")


def elo_window(wait_seconds: float, start: int = 100, step: int = 50, cap: int = 500) -> int:
    """Aumenta en 50 puntos cada 15 segundos, hasta ±500 puntos."""
    return min(cap, start + max(0, int(wait_seconds // 15)) * step)


def prepare_state(
    deck_one: list[str], deck_two: list[str] | None, locations: list[dict], seed: int
) -> dict:
    """La semilla y los órdenes se guardan en el servidor para auditoría/reproducción."""
    valid = [
        v for v in locations if v.get("assignable_to_matches") and v.get("image_status") == "READY"
    ]
    if len(valid) < 3:
        raise RuleViolation("No hay tres ubicaciones habilitadas para la partida")
    rng = Random(seed)
    selected = rng.sample(valid, 3)
    if sum(int(v["card_limit"]) > 0 for v in selected) < 2:
        candidates = [v for v in valid if int(v["card_limit"]) > 0]
        if len(candidates) < 2:
            raise RuleViolation("Se necesitan al menos dos ubicaciones que permitan cartas")
        selected = (
            rng.sample(candidates, 2)
            + [v for v in selected if v["id"] not in {x["id"] for x in candidates[:0]}][:1]
        )
        # El tercer lugar debe ser distinto.
        selected = selected[:2] + [
            next(v for v in valid if v["id"] not in {x["id"] for x in selected[:2]})
        ]
    one = list(deck_one)
    rng.shuffle(one)
    two = list(deck_two) if deck_two is not None else list(deck_one)
    rng.shuffle(two)
    return {
        "seed": seed,
        "locations": [str(v["id"]) for v in selected],
        "deck_order_one": one,
        "deck_order_two": two,
        "hand_one": one[:3],
        "hand_two": two[:3],
        "draw_pile_one": one[3:],
        "draw_pile_two": two[3:],
        "energy": 2,
        "energy_max": 7,
        "turn": 1,
        "turn_seconds": 30,
        "cube_stake": 4,
        "cemetery_one": [],
        "cemetery_two": [],
    }


def turn_start(state: dict, player: int) -> dict:
    """Robar como máximo una carta si la mano tiene menos de siete; reiniciar energía."""
    result = dict(state)
    suffix = "one" if player == 1 else "two"
    hand, deck = list(result[f"hand_{suffix}"]), list(result[f"draw_pile_{suffix}"])
    if len(hand) < 7 and deck:
        hand.append(deck.pop(0))
    result[f"hand_{suffix}"] = hand
    result[f"draw_pile_{suffix}"] = deck
    result["turn"] = int(result["turn"]) + 1
    result["energy"] = min(7, 2 + result["turn"] - 1)
    return result
