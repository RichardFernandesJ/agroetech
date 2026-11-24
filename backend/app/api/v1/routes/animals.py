"""Rotas dos animais."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Header

from app.api.deps import AnimalServiceDep, CurrentUser
from app.game.catalog import get_item
from app.schemas.animal import (
    AnimalRead,
    AnimalsStateRead,
    BuyAnimalRequest,
    FeedRequest,
    HousingRead,
    SpeciesRead,
)
from app.services.animal_service import AnimalsState

router = APIRouter(prefix="/properties/{property_id}/animals", tags=["Animais"])

IdempotencyKey = Annotated[
    str | None,
    Header(
        alias="Idempotency-Key",
        min_length=8,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
        description="Chave única por intenção de compra; reenvios não cobram de novo.",
    ),
]


def _to_read(state: AnimalsState) -> AnimalsStateRead:
    animals = [
        AnimalRead(
            id=view.animal.id,
            species=view.definition.id,
            species_name=view.definition.name,
            product_item=view.definition.product_item,
            product_name=view.definition.product_name,
            stored=view.animal.stored,
            max_stored=view.max_stored,
            produce_seconds=view.produce_seconds,
            yield_bonus_bp=view.yield_bp,
            is_fed=view.fed_seconds_left > 0,
            fed_seconds_left=view.fed_seconds_left,
            seconds_to_next=view.seconds_to_next,
            fed_until=view.animal.fed_until,
        )
        for view in state.animals
    ]
    species = []
    for view in state.species:
        definition = view.definition
        feed = get_item(definition.feed_item)
        species.append(
            SpeciesRead(
                id=definition.id,
                name=definition.name,
                description=definition.description,
                housing=definition.housing,
                price=definition.price,
                min_player_level=definition.min_player_level,
                produce_seconds=definition.produce_seconds,
                product_item=definition.product_item,
                product_name=definition.product_name,
                sell_price=definition.sell_price,
                feed_item=definition.feed_item,
                feed_name=feed.name if feed else definition.feed_item,
                feed_seconds=definition.feed_seconds,
                max_feed_seconds=definition.max_feed_seconds,
                owned=view.owned,
                can_buy=view.can_buy,
                blocked_reason=view.blocked_reason,
            )
        )
    return AnimalsStateRead(
        property_id=state.property.id,
        player_level=state.player_level,
        balance=state.balance,
        animals=animals,
        housings=[
            HousingRead(
                building_id=h.building_id,
                name=h.name,
                level=h.level,
                capacity=h.capacity,
                used=h.used,
            )
            for h in state.housings
        ],
        species=species,
        replayed=state.replayed,
        products=state.products,
        units_fed=state.units_fed,
        xp_gained=state.xp_gained,
    )


@router.get("", response_model=AnimalsStateRead, summary="Animais, abrigos e espécies disponíveis")
async def get_animals(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    animals: AnimalServiceDep,
) -> AnimalsStateRead:
    return _to_read(await animals.state(current_user, property_id))


@router.post("/buy", response_model=AnimalsStateRead, summary="Compra um animal com AgroCoin")
async def buy_animal(
    property_id: uuid.UUID,
    payload: BuyAnimalRequest,
    current_user: CurrentUser,
    animals: AnimalServiceDep,
    idempotency_key: IdempotencyKey = None,
) -> AnimalsStateRead:
    state = await animals.buy(current_user, property_id, payload.species, idempotency_key)
    return _to_read(state)


@router.post("/feed-all", response_model=AnimalsStateRead, summary="Alimenta todos os animais")
async def feed_all(
    property_id: uuid.UUID,
    payload: FeedRequest,
    current_user: CurrentUser,
    animals: AnimalServiceDep,
) -> AnimalsStateRead:
    return _to_read(await animals.feed(current_user, property_id, None, payload.units))


@router.post("/collect", response_model=AnimalsStateRead, summary="Coleta os produtos prontos")
async def collect(
    property_id: uuid.UUID,
    current_user: CurrentUser,
    animals: AnimalServiceDep,
) -> AnimalsStateRead:
    return _to_read(await animals.collect(current_user, property_id))


@router.post(
    "/{animal_id}/feed",
    response_model=AnimalsStateRead,
    summary="Alimenta um animal com ração do inventário",
)
async def feed_animal(
    property_id: uuid.UUID,
    animal_id: uuid.UUID,
    payload: FeedRequest,
    current_user: CurrentUser,
    animals: AnimalServiceDep,
) -> AnimalsStateRead:
    return _to_read(await animals.feed(current_user, property_id, animal_id, payload.units))
