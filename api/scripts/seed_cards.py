"""Carga N cartas de prueba (por defecto 10.000) para demostrar la búsqueda a escala.

Uso: python scripts/seed_cards.py [cantidad]
Usa DATABASE_URL y el almacenamiento configurado (STORAGE_BACKEND). Todas las cartas comparten
una imagen de prueba; las cartas reales se crean con POST /v1/cards.
"""

import io
import random
import sys

from PIL import Image
from sqlalchemy import text

from pokearena.catalog.api.wiring import get_image_storage
from pokearena.catalog.domain.card import card_code
from pokearena.catalog.domain.enums import CardType, Rarity
from pokearena.shared.db import get_engine

PREFIXES = [
    "Pika",
    "Char",
    "Squir",
    "Bulba",
    "Eve",
    "Mew",
    "Geo",
    "Mach",
    "Abra",
    "Onix",
    "Vulp",
    "Psy",
    "Ñan",
    "Mágn",
    "Lápr",
    "Drag",
    "Snor",
    "Jigg",
    "Gast",
    "Hitm",
]
SUFFIXES = [
    "chu",
    "mander",
    "tle",
    "saur",
    "vee",
    "two",
    "dude",
    "op",
    "kadabra",
    "ix",
    "pix",
    "duck",
    "dú",
    "emite",
    "as",
    "onite",
    "lax",
    "lypuff",
    "ly",
    "onlee",
]


def placeholder(width: int, height: int) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", (width, height), (90, 90, 160)).save(out, format="WEBP")
    return out.getvalue()


def main(count: int) -> None:
    storage = get_image_storage()
    storage.put("seed/placeholder.webp", placeholder(600, 840), "image/webp")
    storage.put("seed/placeholder_small.webp", placeholder(200, 280), "image/webp")
    rng = random.Random(1116)
    types = list(CardType)
    with get_engine().begin() as conn:
        counters = dict(
            conn.execute(text("SELECT card_type, last_value FROM card_code_counters")).all()
        )
        rows = []
        for i in range(count):
            card_type = types[i % len(types)]
            counters[card_type.value] += 1
            seq = counters[card_type.value]
            rows.append(
                {
                    "code": card_code(card_type, seq),
                    "seq": seq,
                    "name": f"{rng.choice(PREFIXES)}{rng.choice(SUFFIXES)} {i}",
                    "cost": rng.randint(0, 10),
                    "power": rng.randint(-20, 20),
                    "type": card_type.value,
                    "rarity": rng.choice(list(Rarity)).value,
                }
            )
        conn.execute(
            text(
                "INSERT INTO cards (code, seq, name, cost, power, type, rarity, ability_code, "
                "image_key, thumb_key, image_status) VALUES (:code, :seq, :name, :cost, :power, "
                ":type, :rarity, 'HAB-000', 'seed/placeholder.webp', "
                "'seed/placeholder_small.webp', 'READY')"
            ),
            rows,
        )
        for card_type, last in counters.items():
            conn.execute(
                text("UPDATE card_code_counters SET last_value = :v WHERE card_type = :t"),
                {"v": last, "t": card_type},
            )
        conn.execute(text("ANALYZE cards"))
    print(f"Se cargaron {count} cartas.")


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 10_000)
