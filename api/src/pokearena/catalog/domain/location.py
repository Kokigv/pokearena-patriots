"""Ubicaciones del tablero y su catálogo cerrado de efectos.

Cada tipo de efecto tiene su propio validador registrado en ``EFFECT_VALIDATORS``. Agregar un
tipo nuevo es agregar una clase al registro, sin tocar la creación de ubicaciones
(principio abierto/cerrado, RNF-ARQ-02).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any, Protocol

from pokearena.catalog.domain.enums import CardType, ImageStatus
from pokearena.catalog.domain.values import check_enum, check_int_range, check_text
from pokearena.shared.errors import FieldError, ValidationFailed

CARD_LIMIT_RANGE = (0, 5)
TURNS = (1, 6)


class ExtraEnergyMode(StrEnum):
    FIJA = "FIJA"  # cada jugador recibe un monto fijo al inicio de cada turno
    POR_CARTA = "POR_CARTA"  # monto por cada carta propia en la ubicación


EXTRA_ENERGY_RANGES = {ExtraEnergyMode.FIJA: (0, 3), ExtraEnergyMode.POR_CARTA: (0, 2)}


class EffectType(StrEnum):
    NINGUNO = "NINGUNO"
    BONIFICACION_POR_TIPO = "BONIFICACION_POR_TIPO"
    MODIFICADOR_DE_COSTO = "MODIFICADOR_DE_COSTO"
    RESTRICCION_POR_TURNO = "RESTRICCION_POR_TURNO"


class EffectValidator(Protocol):
    def validate(self, params: Mapping[str, Any]) -> tuple[dict[str, Any], list[FieldError]]: ...


def _unexpected(params: Mapping[str, Any], allowed: set[str]) -> list[FieldError]:
    return [
        FieldError(f"effect_params.{key}", "parámetro no admitido para este efecto")
        for key in params
        if key not in allowed
    ]


class NoEffect:
    def validate(self, params: Mapping[str, Any]) -> tuple[dict[str, Any], list[FieldError]]:
        return {}, _unexpected(params, set())


class TypeBonus:
    """Bonificación de poder (-5 a +5) a las cartas de un tipo en la ubicación."""

    def validate(self, params: Mapping[str, Any]) -> tuple[dict[str, Any], list[FieldError]]:
        errors = _unexpected(params, {"card_type", "amount"})
        card_type = check_enum(errors, "effect_params.card_type", params.get("card_type"), CardType)
        amount = check_int_range(errors, "effect_params.amount", params.get("amount"), -5, 5)
        clean = {"card_type": card_type.value if card_type else None, "amount": amount}
        return clean, errors


class CostModifier:
    """Cambia el costo (-5 a +5) de las cartas que se juegan aquí, opcionalmente de un tipo."""

    def validate(self, params: Mapping[str, Any]) -> tuple[dict[str, Any], list[FieldError]]:
        errors = _unexpected(params, {"card_type", "amount"})
        amount = check_int_range(errors, "effect_params.amount", params.get("amount"), -5, 5)
        card_type = None
        if params.get("card_type") is not None:
            parsed = check_enum(
                errors, "effect_params.card_type", params.get("card_type"), CardType
            )
            card_type = parsed.value if parsed else None
        return {"amount": amount, "card_type": card_type}, errors


class TurnRestriction:
    """Turnos (1 a 6) en los que no se pueden jugar cartas en la ubicación."""

    def validate(self, params: Mapping[str, Any]) -> tuple[dict[str, Any], list[FieldError]]:
        errors = _unexpected(params, {"turns"})
        turns = params.get("turns")
        if not isinstance(turns, list) or not turns:
            errors.append(FieldError("effect_params.turns", "debe ser una lista de turnos"))
            return {}, errors
        clean: list[int] = []
        for turn in turns:
            value = check_int_range(errors, "effect_params.turns", turn, *TURNS)
            if value is not None and value not in clean:
                clean.append(value)
        if len(clean) == TURNS[1]:
            errors.append(FieldError("effect_params.turns", "no puede restringir los 6 turnos"))
        return {"turns": sorted(clean)}, errors


EFFECT_VALIDATORS: dict[EffectType, EffectValidator] = {
    EffectType.NINGUNO: NoEffect(),
    EffectType.BONIFICACION_POR_TIPO: TypeBonus(),
    EffectType.MODIFICADOR_DE_COSTO: CostModifier(),
    EffectType.RESTRICCION_POR_TURNO: TurnRestriction(),
}


@dataclass(frozen=True)
class LocationDraft:
    name: str
    description: str
    card_limit: int
    extra_energy_mode: ExtraEnergyMode
    extra_energy_amount: int
    effect_type: EffectType
    effect_params: dict[str, Any]

    @classmethod
    def parse(
        cls,
        name: Any,
        description: Any,
        card_limit: Any,
        extra_energy_mode: Any,
        extra_energy_amount: Any,
        effect_type: Any,
        effect_params: Any,
    ) -> "LocationDraft":
        errors: list[FieldError] = []
        clean_name = check_text(errors, "name", name, 60)
        clean_description = check_text(errors, "description", description, 500)
        clean_limit = check_int_range(errors, "card_limit", card_limit, *CARD_LIMIT_RANGE)
        mode = check_enum(errors, "extra_energy_mode", extra_energy_mode, ExtraEnergyMode)
        amount = None
        if mode is not None:
            amount = check_int_range(
                errors, "extra_energy_amount", extra_energy_amount, *EXTRA_ENERGY_RANGES[mode]
            )
        effect = check_enum(errors, "effect_type", effect_type or "NINGUNO", EffectType)
        clean_params: dict[str, Any] = {}
        if effect is not None:
            if effect_params is None:
                effect_params = {}
            if not isinstance(effect_params, Mapping):
                errors.append(FieldError("effect_params", "debe ser un objeto JSON"))
            else:
                clean_params, param_errors = EFFECT_VALIDATORS[effect].validate(effect_params)
                errors.extend(param_errors)
        if errors:
            raise ValidationFailed(errors)
        assert clean_name is not None and clean_description is not None
        assert clean_limit is not None and mode is not None and amount is not None
        assert effect is not None
        return cls(clean_name, clean_description, clean_limit, mode, amount, effect, clean_params)


@dataclass(frozen=True)
class Location:
    id: str
    name: str
    description: str
    card_limit: int
    extra_energy_mode: ExtraEnergyMode
    extra_energy_amount: int
    effect_type: EffectType
    effect_params: dict[str, Any]
    image_key: str
    thumb_key: str | None
    image_status: ImageStatus
    created_at: datetime

    @property
    def assignable_to_matches(self) -> bool:
        return self.image_status is ImageStatus.READY
