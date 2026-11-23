"""Agregador de rotas da versão 1 da API."""

from fastapi import APIRouter

from app.api.v1.routes import auth, catalog, inventory, plantings, production, properties

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(properties.router)
api_router.include_router(inventory.router)
api_router.include_router(plantings.router)
api_router.include_router(production.router)
api_router.include_router(catalog.router)
