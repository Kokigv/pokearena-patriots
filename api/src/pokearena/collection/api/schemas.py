"""Modelos de respuesta HTTP de Colección (coinciden con api/openapi.yaml)."""

from datetime import datetime

from pydantic import BaseModel

from pokearena.collection.application.explore_catalog import CatalogEntry
from pokearena.collection.domain.collection import CollectionSummary


class CatalogAbilityOut(BaseModel):
    code: str
    name: str
    trigger: str
    effect: str


class CatalogCardOut(BaseModel):
    code: str
    name: str
    cost: int
    power: int
    type: str
    rarity: str
    image_url: str  # versión grande de la imagen (criterio alterno de la US 124)
    ability: CatalogAbilityOut | None
    owned: bool
    copies: int

    @classmethod
    def of(cls, entry: CatalogEntry) -> "CatalogCardOut":
        card = entry.card
        return cls(
            code=card.code,
            name=card.name,
            cost=card.cost,
            power=card.power,
            type=card.type,
            rarity=card.rarity,
            image_url=f"/v1/images/{card.image_key}",
            ability=CatalogAbilityOut(**card.ability.__dict__) if card.ability else None,
            owned=entry.owned,
            copies=entry.copies,
        )


class CatalogPageOut(BaseModel):
    items: list[CatalogCardOut]
    next_cursor: str | None


class OwnedCardOut(BaseModel):
    card_code: str
    copies: int


class CubeMovementOut(BaseModel):
    amount: int
    reason: str
    balance_after: int
    created_at: datetime


class CollectionOut(BaseModel):
    initial_granted: bool
    cubes: int
    distinct_cards: int
    cards: list[OwnedCardOut]
    cube_movements: list[CubeMovementOut]

    @classmethod
    def of(cls, summary: CollectionSummary) -> "CollectionOut":
        return cls(
            initial_granted=summary.initial_granted,
            cubes=summary.cubes,
            distinct_cards=summary.distinct_cards,
            cards=[OwnedCardOut(card_code=c.card_code, copies=c.copies) for c in summary.cards],
            cube_movements=[
                CubeMovementOut(
                    amount=m.amount,
                    reason=m.reason,
                    balance_after=m.balance_after,
                    created_at=m.created_at,
                )
                for m in summary.movements
            ],
        )
