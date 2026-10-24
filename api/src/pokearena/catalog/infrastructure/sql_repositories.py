"""Adaptadores de PostgreSQL para los repositorios del catálogo."""

import uuid
from typing import Any

from sqlalchemy import Row, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from pokearena.catalog.application.ports import DuplicateRequest, StoredImages
from pokearena.catalog.domain.ability import Ability
from pokearena.catalog.domain.card import Card, CardDraft, card_code
from pokearena.catalog.domain.enums import CardType, EffectKind, ImageStatus, Rarity, Trigger
from pokearena.catalog.domain.location import (
    EffectType,
    ExtraEnergyMode,
    Location,
    LocationDraft,
)
from pokearena.catalog.infrastructure.tables import (
    abilities,
    card_code_counters,
    cards,
    locations,
)


def _ability(row: Row[Any]) -> Ability:
    return Ability(
        code=row.code,
        name=row.name,
        trigger=Trigger(row.trigger),
        effect=EffectKind(row.effect),
        target=row.target,
        affected_type=CardType(row.affected_type) if row.affected_type else None,
        condition=row.condition or {},
        params=row.params or {},
        evolution_target=row.evolution_target,
    )


def _card(row: Row[Any]) -> Card:
    return Card(
        code=row.code,
        name=row.name,
        cost=row.cost,
        power=row.power,
        type=CardType(row.type),
        rarity=Rarity(row.rarity),
        ability_code=row.ability_code,
        image_key=row.image_key,
        thumb_key=row.thumb_key,
        image_status=ImageStatus(row.image_status),
        created_at=row.created_at,
    )


def _location(row: Row[Any]) -> Location:
    return Location(
        id=str(row.id),
        name=row.name,
        description=row.description,
        card_limit=row.card_limit,
        extra_energy_mode=ExtraEnergyMode(row.extra_energy_mode),
        extra_energy_amount=row.extra_energy_amount,
        effect_type=EffectType(row.effect_type),
        effect_params=row.effect_params or {},
        image_key=row.image_key,
        thumb_key=row.thumb_key,
        image_status=ImageStatus(row.image_status),
        created_at=row.created_at,
    )


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class SqlAbilityRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, code: str) -> Ability | None:
        row = self._session.execute(select(abilities).where(abilities.c.code == code)).first()
        return _ability(row) if row else None

    def ability_of_card(self, card_code: str) -> Ability | None:
        stmt = (
            select(abilities)
            .join(cards, cards.c.ability_code == abilities.c.code)
            .where(cards.c.code == card_code)
        )
        row = self._session.execute(stmt).first()
        return _ability(row) if row else None

    def list_all(self) -> list[Ability]:
        rows = self._session.execute(select(abilities).order_by(abilities.c.code)).all()
        return [_ability(r) for r in rows]


class SqlCardRepository:
    def __init__(self, session: Session, created_by: str | None = None) -> None:
        self._session = session
        self._created_by = created_by

    def find_by_idempotency_key(self, key: str) -> Card | None:
        stmt = select(cards).where(cards.c.idempotency_key == key)
        row = self._session.execute(stmt).first()
        return _card(row) if row else None

    def get(self, code: str) -> Card | None:
        row = self._session.execute(select(cards).where(cards.c.code == code)).first()
        return _card(row) if row else None

    def add(self, draft: CardDraft, images: StoredImages, idempotency_key: str) -> Card:
        try:
            # El UPDATE ... RETURNING bloquea la fila del contador hasta el COMMIT: dos
            # administradores que crean cartas del mismo tipo reciben consecutivos distintos.
            # Si el INSERT falla, el ROLLBACK devuelve el consecutivo (no se consume un código).
            seq = self._session.execute(
                update(card_code_counters)
                .where(card_code_counters.c.card_type == draft.type.value)
                .values(last_value=card_code_counters.c.last_value + 1)
                .returning(card_code_counters.c.last_value)
            ).scalar_one()
            row = self._session.execute(
                insert(cards)
                .values(
                    code=card_code(draft.type, seq),
                    seq=seq,
                    name=draft.name,
                    cost=draft.cost,
                    power=draft.power,
                    type=draft.type.value,
                    rarity=draft.rarity.value,
                    ability_code=draft.ability_code,
                    image_key=images.image_key,
                    thumb_key=images.thumb_key,
                    image_status=images.status.value,
                    idempotency_key=idempotency_key,
                    created_by=self._created_by,
                )
                .returning(*cards.c)
            ).one()
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if "idempotency_key" in str(exc.orig):
                raise DuplicateRequest() from exc
            raise
        return _card(row)

    def update_thumbnail(self, code: str, thumb_key: str | None, status: ImageStatus) -> Card:
        row = self._session.execute(
            update(cards)
            .where(cards.c.code == code)
            .values(thumb_key=thumb_key, image_status=status.value)
            .returning(*cards.c)
        ).one()
        self._session.commit()
        return _card(row)


class SqlLocationRepository:
    def __init__(self, session: Session, created_by: str | None = None) -> None:
        self._session = session
        self._created_by = created_by

    def find_by_idempotency_key(self, key: str) -> Location | None:
        stmt = select(locations).where(locations.c.idempotency_key == key)
        row = self._session.execute(stmt).first()
        return _location(row) if row else None

    def get(self, location_id: str) -> Location | None:
        try:
            uuid.UUID(location_id)
        except ValueError:
            return None
        stmt = select(locations).where(locations.c.id == location_id)
        row = self._session.execute(stmt).first()
        return _location(row) if row else None

    def add(self, draft: LocationDraft, images: StoredImages, idempotency_key: str) -> Location:
        try:
            row = self._session.execute(
                insert(locations)
                .values(
                    id=str(uuid.uuid4()),
                    name=draft.name,
                    description=draft.description,
                    card_limit=draft.card_limit,
                    extra_energy_mode=draft.extra_energy_mode.value,
                    extra_energy_amount=draft.extra_energy_amount,
                    effect_type=draft.effect_type.value,
                    effect_params=draft.effect_params,
                    image_key=images.image_key,
                    thumb_key=images.thumb_key,
                    image_status=images.status.value,
                    idempotency_key=idempotency_key,
                    created_by=self._created_by,
                )
                .returning(*locations.c)
            ).one()
            self._session.commit()
        except IntegrityError as exc:
            self._session.rollback()
            if "idempotency_key" in str(exc.orig):
                raise DuplicateRequest() from exc
            raise
        return _location(row)

    def update_thumbnail(
        self, location_id: str, thumb_key: str | None, status: ImageStatus
    ) -> Location:
        row = self._session.execute(
            update(locations)
            .where(locations.c.id == location_id)
            .values(thumb_key=thumb_key, image_status=status.value)
            .returning(*locations.c)
        ).one()
        self._session.commit()
        return _location(row)
