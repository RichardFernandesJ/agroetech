"""Regras de cadastro e autenticação."""

from app.core.exceptions import AuthenticationError, ConflictError, ForbiddenError
from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.auth import RegisterRequest


class AuthService:
    def __init__(self, users: UserRepository) -> None:
        self.users = users

    async def register(self, payload: RegisterRequest) -> User:
        email = payload.email.strip().lower()
        username = payload.username.strip().lower()

        if await self.users.get_by_email(email) is not None:
            raise ConflictError("Já existe uma conta com este e-mail.")
        if await self.users.get_by_username(username) is not None:
            raise ConflictError("Este nome de usuário já está em uso.")

        user = User(
            email=email,
            username=username,
            password_hash=hash_password(payload.password),
        )
        return await self.users.add(user)

    async def authenticate(self, login: str, password: str) -> User:
        user = await self.users.get_by_login(login.strip())
        if user is None or not verify_password(password, user.password_hash):
            raise AuthenticationError("E-mail/usuário ou senha inválidos.")
        if not user.is_active:
            raise ForbiddenError("Esta conta está desativada.")
        return user

    def issue_access_token(self, user: User) -> tuple[str, int]:
        return create_access_token(subject=str(user.id))
