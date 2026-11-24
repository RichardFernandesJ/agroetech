"""Agregador de rotas da versão 1 da API."""

from fastapi import APIRouter

from app.api.v1.routes import (
    animals,
    auth,
    buildings,
    catalog,
    characters,
    crafting,
    exchange,
    inventory,
    market,
    plantings,
    production,
    progress,
    properties,
    talents,
    wallet,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(characters.router)
api_router.include_router(properties.router)
api_router.include_router(inventory.router)
api_router.include_router(plantings.router)
api_router.include_router(production.router)
api_router.include_router(catalog.router)
api_router.include_router(wallet.router)
api_router.include_router(market.router)
api_router.include_router(progress.router)
api_router.include_router(talents.router)
api_router.include_router(buildings.router)
api_router.include_router(animals.router)
api_router.include_router(crafting.router)
api_router.include_router(exchange.router)
