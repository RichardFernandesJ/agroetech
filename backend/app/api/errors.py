"""Tradução de exceções de domínio em respostas HTTP."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError

from app.core.exceptions import AppError, AuthenticationError


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(IntegrityError)
    async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
        # Duas requisições simultâneas colidiram numa restrição única do banco (ex.: mesmo
        # e-mail cadastrado ao mesmo tempo). A transação já foi desfeita; avisa o cliente.
        return JSONResponse(
            status_code=409,
            content={
                "detail": "Esta operação colidiu com outra em andamento. Tente novamente.",
                "code": "conflict",
            },
        )

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        headers = None
        if isinstance(exc, AuthenticationError):
            headers = {"WWW-Authenticate": "Bearer"}
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.message, "code": exc.code},
            headers=headers,
        )
