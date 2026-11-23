"""Rotas de cadastro e autenticação."""

from fastapi import APIRouter, status

from app.api.deps import AuthServiceDep, CurrentUser
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserRead

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post(
    "/register",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    summary="Cadastra um novo jogador",
)
async def register(payload: RegisterRequest, service: AuthServiceDep) -> User:
    return await service.register(payload)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Autentica por e-mail ou nome de usuário",
)
async def login(payload: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    user = await service.authenticate(payload.login, payload.password)
    access_token, expires_in = service.issue_access_token(user)
    return TokenResponse(access_token=access_token, expires_in=expires_in)


@router.get(
    "/me",
    response_model=UserRead,
    summary="Retorna o jogador autenticado",
)
async def me(current_user: CurrentUser) -> User:
    return current_user
