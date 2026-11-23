"""Exceções de domínio.

Services e repositories não conhecem HTTP: eles lançam estas exceções e a
camada de API as traduz em respostas JSON com o status correto.
"""


class AppError(Exception):
    status_code: int = 400
    code: str = "app_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class AuthenticationError(AppError):
    status_code = 401
    code = "authentication_error"


class InvalidTokenError(AuthenticationError):
    code = "invalid_token"


class ForbiddenError(AppError):
    status_code = 403
    code = "forbidden"


class GameRuleError(AppError):
    """Regra de jogo violada (sem sementes, talhão ocupado, etc.)."""

    status_code = 422
    code = "game_rule_violation"
