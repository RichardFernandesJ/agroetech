"""Ponto de entrada da API do Agro & Tech."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401  (registra os models no metadata)
from app.api.errors import register_exception_handlers
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import dispose_engine, get_engine
from app.models.base import Base


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.auto_create_tables:
        async with get_engine().begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
    yield
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    description="Backend do RPG de fazenda Agro & Tech.",
    version="0.1.1",
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router)


@app.get("/", tags=["Infra"], summary="Identificação da API")
async def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    }


@app.get("/health", tags=["Infra"], summary="Verificação de saúde")
async def health() -> dict[str, str]:
    return {"status": "ok"}
