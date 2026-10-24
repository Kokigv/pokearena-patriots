"""Criterios de búsqueda del catálogo (US Buscar carta)."""

import base64
import binascii
from dataclasses import dataclass
from typing import Any

from pokearena.catalog.domain.card import COST_RANGE, POWER_RANGE, parse_card_code
from pokearena.catalog.domain.enums import CardType, EffectKind, Rarity, Trigger
from pokearena.catalog.domain.values import check_enum, check_int_range, check_text
from pokearena.shared.errors import FieldError, ValidationFailed

DEFAULT_LIMIT = 50
MAX_LIMIT = 100


@dataclass(frozen=True)
class IntRange:
    low: int | None
    high: int | None


@dataclass(frozen=True)
class SearchCriteria:
    code: str | None = None
    name: str | None = None
    cost: IntRange | None = None
    power: IntRange | None = None
    type: CardType | None = None
    rarity: Rarity | None = None
    ability_code: str | None = None
    trigger: Trigger | None = None
    effect: EffectKind | None = None
    after_code: str | None = None  # cursor: última carta de la página anterior
    limit: int = DEFAULT_LIMIT


def encode_cursor(code: str) -> str:
    return base64.urlsafe_b64encode(code.encode()).decode().rstrip("=")


def _decode_cursor(errors: list[FieldError], cursor: str) -> str | None:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        code = base64.urlsafe_b64decode(padded.encode()).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError):
        code = ""
    if parse_card_code(code) is None:
        errors.append(FieldError("cursor", "cursor inválido"))
        return None
    return code


def _range(
    errors: list[FieldError],
    field: str,
    exact: Any,
    low: Any,
    high: Any,
    bounds: tuple[int, int],
) -> IntRange | None:
    if exact is not None:
        if low is not None or high is not None:
            errors.append(FieldError(field, f"use {field} o {field}_min/{field}_max, no ambos"))
            return None
        value = check_int_range(errors, field, exact, *bounds)
        return IntRange(value, value) if value is not None else None
    if low is None and high is None:
        return None
    clean_low = check_int_range(errors, f"{field}_min", low, *bounds) if low is not None else None
    clean_high = (
        check_int_range(errors, f"{field}_max", high, *bounds) if high is not None else None
    )
    if clean_low is not None and clean_high is not None and clean_low > clean_high:
        errors.append(FieldError(field, "el mínimo no puede ser mayor que el máximo"))
        return None
    return IntRange(clean_low, clean_high)


def parse_criteria(
    *,
    code: str | None = None,
    name: str | None = None,
    cost: int | None = None,
    cost_min: int | None = None,
    cost_max: int | None = None,
    power: int | None = None,
    power_min: int | None = None,
    power_max: int | None = None,
    type: str | None = None,
    rarity: str | None = None,
    ability_code: str | None = None,
    trigger: str | None = None,
    effect: str | None = None,
    cursor: str | None = None,
    limit: int | None = None,
) -> SearchCriteria:
    errors: list[FieldError] = []
    criteria = SearchCriteria(
        code=check_text(errors, "code", code, 20, required=False),
        name=check_text(errors, "name", name, 60, required=False),
        cost=_range(errors, "cost", cost, cost_min, cost_max, COST_RANGE),
        power=_range(errors, "power", power, power_min, power_max, POWER_RANGE),
        type=check_enum(errors, "type", type, CardType) if type is not None else None,
        rarity=check_enum(errors, "rarity", rarity, Rarity) if rarity is not None else None,
        ability_code=check_text(errors, "ability_code", ability_code, 20, required=False),
        trigger=check_enum(errors, "trigger", trigger, Trigger) if trigger is not None else None,
        effect=check_enum(errors, "effect", effect, EffectKind) if effect is not None else None,
        after_code=_decode_cursor(errors, cursor) if cursor else None,
        limit=(
            check_int_range(errors, "limit", limit, 1, MAX_LIMIT) or DEFAULT_LIMIT
            if limit is not None
            else DEFAULT_LIMIT
        ),
    )
    if errors:
        raise ValidationFailed(errors)
    return criteria
