"""Schemas de cadastro e autenticação."""

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    username: str = Field(
        min_length=3,
        max_length=30,
        pattern=r"^[a-zA-Z0-9_.-]+$",
        examples=["fazendeiro_ana"],
    )
    password: str = Field(min_length=8, max_length=128, examples=["colheita2026"])


class LoginRequest(BaseModel):
    login: str = Field(
        min_length=1,
        max_length=255,
        description="E-mail ou nome de usuário.",
        examples=["ana@agro.com.br"],
    )
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
