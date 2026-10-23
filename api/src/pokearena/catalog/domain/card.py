"""Cartas del catálogo."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pokearena.catalog.domain.enums import CardType, ImageStatus, Rarity
from pokearena.catalog.domain.values import check_enum, check_int_range, check_text
from pokearena.shared.errors import FieldError, ValidationFailed

COST_RANGE = (0, 10)
POWER_RANGE = (-20, 20)
NAME_MAX = 60


@dataclass(frozen=True)
class CardDraft:
    """Datos validados de una carta nueva, antes de tener código e imagen."""

    name: str
    cost: int
    power: int
    type: CardType
    rarity: Rarity
    ability_code: str

    @classmethod
    def parse(
        cls,
        name: Any,
        cost: Any,
        power: Any,
        type: Any,
        rarity: Any,
        ability_code: Any,
    ) -> "CardDraft":
        errors: list[FieldError] = []
        clean_name = check_text(errors, "name", name, NAME_MAX)
        clean_cost = check_int_range(errors, "cost", cost, *COST_RANGE)
        clean_power = check_int_range(errors, "power", power, *POWER_RANGE)
        clean_type = check_enum(errors, "type", type, CardType)
        clean_rarity = check_enum(errors, "rarity", rarity, Rarity)
        clean_ability = check_text(errors, "ability_code", ability_code, 20, required=False)
        if clean_ability is None and not any(e.field == "ability_code" for e in errors):
            errors.append(
                FieldError("ability_code", "debe elegir una habilidad, aunque sea Sin Habilidad")
            )
        if errors:
            raise ValidationFailed(errors)
        assert clean_name is not None and clean_cost is not None and clean_power is not None
        assert clean_type is not None and clean_rarity is not None and clean_ability is not None
        return cls(clean_name, clean_cost, clean_power, clean_type, clean_rarity, clean_ability)


def card_code(card_type: CardType, sequence: int) -> str:
    """Código único e inmutable PKA-<TIPO>-<NNN>, con al menos 3 dígitos.

    El caso estima ~10.000 cartas (más de 999 por tipo), así que después de PKA-FUE-999 sigue
    PKA-FUE-1000 en lugar de repetir o rechazar códigos.
    """
    return f"PKA-{card_type.abbreviation}-{sequence:03d}"


def parse_card_code(code: str) -> tuple[CardType, int] | None:
    """Inverso de ``card_code``: devuelve el tipo y el consecutivo, o None si no es válido."""
    parts = code.split("-")
    if len(parts) != 3 or parts[0] != "PKA" or not parts[2].isdigit():
        return None
    card_type = next((t for t in CardType if t.abbreviation == parts[1]), None)
    return (card_type, int(parts[2])) if card_type else None


@dataclass(frozen=True)
class Card:
    code: str
    name: str
    cost: int
    power: int
    type: CardType
    rarity: Rarity
    ability_code: str
    image_key: str
    thumb_key: str | None
    image_status: ImageStatus
    created_at: datetime

    @property
    def available_to_players(self) -> bool:
        return self.image_status is ImageStatus.READY
