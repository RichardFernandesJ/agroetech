"""Rotas de progressão (XP e nível)."""

from fastapi import APIRouter

from app.api.deps import CurrentUser, ProgressServiceDep
from app.schemas.progress import ProgressRead

router = APIRouter(prefix="/progress", tags=["Progressão"])


@router.get("", response_model=ProgressRead, summary="XP e nível do jogador")
async def get_progress(current_user: CurrentUser, progress: ProgressServiceDep) -> ProgressRead:
    info = await progress.describe(current_user.id)
    return ProgressRead(
        level=info.level,
        xp=info.xp,
        xp_into_level=info.xp_into_level,
        xp_for_next=info.xp_for_next,
        max_level=info.max_level,
    )
