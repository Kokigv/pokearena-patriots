"""Modelos de respuesta HTTP del catálogo (coinciden con api/openapi.yaml)."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from pokearena.catalog.domain.ability import Ability
from pokearena.catalog.domain.card import Card
from pokearena.catalog.domain.location import Location


def image_url(key: str | None) -> str | None:
    return f"/v1/images/{key}" if key else None


class AbilityOut(BaseModel):
    code: str
    name: str
    trigger: str
    effect: str
    target: str | None
    affected_type: str | None
    condition: dict[str, Any]
    params: dict[str, Any]
    evolution_target: str | None

    @classmethod
    def of(cls, ability: Ability) -> "AbilityOut":
        return cls(
            code=ability.code,
            name=ability.name,
            trigger=ability.trigger.value,
            effect=ability.effect.value,
            target=ability.target,
            affected_type=ability.affected_type.value if ability.affected_type else None,
            condition=dict(ability.condition),
            params=dict(ability.params),
            evolution_target=ability.evolution_target,
        )


class ImageOut(BaseModel):
    status: str
    url: str
    small_url: str | None


class CardOut(BaseModel):
    code: str
    name: str
    cost: int
    power: int
    type: str
    rarity: str
    ability: AbilityOut | None
    image: ImageOut
    available_to_players: bool
    created_at: datetime

    @classmethod
    def of(cls, card: Card, ability: Ability | None) -> "CardOut":
        return cls(
            code=card.code,
            name=card.name,
            cost=card.cost,
            power=card.power,
            type=card.type.value,
            rarity=card.rarity.value,
            ability=AbilityOut.of(ability) if ability else None,
            image=ImageOut(
                status=card.image_status.value,
                url=image_url(card.image_key) or "",
                small_url=image_url(card.thumb_key),
            ),
            available_to_players=card.available_to_players,
            created_at=card.created_at,
        )


class CardPageOut(BaseModel):
    items: list[CardOut]
    next_cursor: str | None


class ExtraEnergyOut(BaseModel):
    mode: str
    amount: int


class EffectOut(BaseModel):
    type: str
    params: dict[str, Any]


class LocationOut(BaseModel):
    id: str
    name: str
    description: str
    card_limit: int
    extra_energy: ExtraEnergyOut
    effect: EffectOut
    image: ImageOut
    assignable_to_matches: bool
    created_at: datetime

    @classmethod
    def of(cls, location: Location) -> "LocationOut":
        return cls(
            id=location.id,
            name=location.name,
            description=location.description,
            card_limit=location.card_limit,
            extra_energy=ExtraEnergyOut(
                mode=location.extra_energy_mode.value, amount=location.extra_energy_amount
            ),
            effect=EffectOut(type=location.effect_type.value, params=location.effect_params),
            image=ImageOut(
                status=location.image_status.value,
                url=image_url(location.image_key) or "",
                small_url=image_url(location.thumb_key),
            ),
            assignable_to_matches=location.assignable_to_matches,
            created_at=location.created_at,
        )
