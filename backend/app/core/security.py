"""Hash de senhas e emissão/validação de tokens JWT."""

import base64
import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

import jwt

from app.core.config import settings
from app.core.exceptions import InvalidTokenError

_PASSWORD_ALGORITHM = "pbkdf2_sha256"
_PASSWORD_ITERATIONS = 600_000
_SALT_BYTES = 16
_TOKEN_TYPE = "access"


def hash_password(password: str) -> str:
    """Gera um hash versionado no formato ``pbkdf2_sha256$iterações$salt$hash``.

    PBKDF2-HMAC-SHA256 faz parte da biblioteca padrão e não exige dependências
    nativas. Para trocar por Argon2/bcrypt basta alterar este módulo.
    """
    salt = secrets.token_bytes(_SALT_BYTES)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PASSWORD_ITERATIONS)
    salt_b64 = base64.b64encode(salt).decode("ascii")
    digest_b64 = base64.b64encode(digest).decode("ascii")
    return f"{_PASSWORD_ALGORITHM}${_PASSWORD_ITERATIONS}${salt_b64}${digest_b64}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, iterations, salt_b64, digest_b64 = password_hash.split("$", 3)
        if algorithm != _PASSWORD_ALGORITHM:
            return False
        salt = base64.b64decode(salt_b64)
        expected = base64.b64decode(digest_b64)
        digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, int(iterations))
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest, expected)


def create_access_token(
    subject: str,
    expires_delta: timedelta | None = None,
) -> tuple[str, int]:
    """Cria o token e devolve ``(token, segundos_até_expirar)``."""
    now = datetime.now(UTC)
    expires_delta = expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    expire = now + expires_delta
    payload = {
        "sub": subject,
        "type": _TOKEN_TYPE,
        "iat": now,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
        )
    except jwt.PyJWTError as exc:
        raise InvalidTokenError("Token inválido ou expirado") from exc

    if payload.get("type") != _TOKEN_TYPE or not payload.get("sub"):
        raise InvalidTokenError("Token inválido")
    return payload
