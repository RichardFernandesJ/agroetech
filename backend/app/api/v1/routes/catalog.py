"""Rotas públicas do catálogo (consumidas pelo frontend Phaser)."""

from fastapi import APIRouter

from app.api.v1.routes.buildings import level_to_read
from app.api.v1.serializers import serialize_crop
from app.game.buildings import BUILDINGS
from app.game.catalog import CROPS, ITEM_CATALOG
from app.game.talents import BRANCHES, MAP_CENTER, NODES, TIER_NAMES
from app.schemas.building import BuildingCatalogRead
from app.schemas.catalog import CropRead, ItemRead
from app.schemas.talent import BranchRead, EffectRead, TalentCatalogRead, TalentNodeRead

router = APIRouter(prefix="/catalog", tags=["Catálogo"])


@router.get("/crops", response_model=list[CropRead], summary="Lista as culturas disponíveis")
async def list_crops() -> list[CropRead]:
    return [serialize_crop(crop) for crop in CROPS.values()]


@router.get("/items", response_model=list[ItemRead], summary="Lista sementes e produtos")
async def list_items() -> list[ItemRead]:
    return [
        ItemRead(
            id=item.id,
            name=item.name,
            category=item.category,
            description=item.description,
        )
        for item in ITEM_CATALOG.values()
    ]


@router.get(
    "/talents",
    response_model=TalentCatalogRead,
    summary="Mapa de talentos: ramos, nós, requisitos e posições",
)
async def list_talents() -> TalentCatalogRead:
    return TalentCatalogRead(
        center_x=MAP_CENTER[0],
        center_y=MAP_CENTER[1],
        branches=[
            BranchRead(
                id=branch.id,
                name=branch.name,
                description=branch.description,
                available=branch.available,
                angle=branch.angle,
            )
            for branch in BRANCHES
        ],
        nodes=[
            TalentNodeRead(
                id=node.id,
                name=node.name,
                description=node.description,
                branch=node.branch,
                tier=node.tier,
                tier_name=TIER_NAMES[node.tier],
                cost=node.cost,
                min_level=node.min_level,
                requires=list(node.requires),
                requires_any=list(node.requires_any),
                branch_points=dict(node.branch_points),
                exclusive_group=node.exclusive_group,
                effects=[
                    EffectRead(stat=e.stat, value_bp=e.value_bp, scope=e.scope)
                    for e in node.effects
                ],
                x=node.x,
                y=node.y,
            )
            for node in NODES
        ],
    )


@router.get(
    "/buildings",
    response_model=list[BuildingCatalogRead],
    summary="Construções, níveis, custos e benefícios",
)
async def list_buildings() -> list[BuildingCatalogRead]:
    return [
        BuildingCatalogRead(
            id=definition.id,
            name=definition.name,
            description=definition.description,
            initial_level=definition.initial_level,
            max_level=definition.max_level,
            levels=[level_to_read(level) for level in definition.levels],
        )
        for definition in BUILDINGS.values()
    ]
