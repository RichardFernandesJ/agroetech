"""Configurações da aplicação, carregadas de variáveis de ambiente (prefixo AGRO_)."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="AGRO_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "Agro & Tech API"
    environment: str = "development"
    debug: bool = False

    # Banco de dados. Em testes a URL é substituída por SQLite em memória.
    database_url: str = "postgresql+asyncpg://agro:agro@localhost:5432/agroetech"
    # O schema é responsabilidade do Alembic. `true` serve apenas para bancos
    # descartáveis de prototipagem.
    auto_create_tables: bool = False

    # Autenticação
    jwt_secret: str = "dev-secret-change-me-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24  # 24h

    # CORS (frontend Phaser/TypeScript)
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ]

    # Regras de produção offline
    offline_max_hours: int = 12
    offline_max_cycles_per_planting: int = 8

    # Limites de propriedade
    max_plots_per_property: int = 12
    default_plots_per_property: int = 6

    @property
    def is_production(self) -> bool:
        return self.environment.lower() in {"production", "prod"}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
