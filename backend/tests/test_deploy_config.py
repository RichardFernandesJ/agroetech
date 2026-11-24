"""Verificação estática da configuração de Docker/Compose/nginx.

Não substitui subir os contêineres (veja docs/VALIDATION.md), mas pega cedo os erros
de referência mais comuns: serviço apontando para estágio inexistente, variável de
ambiente que a aplicação não conhece, comando sem migração, etc.
"""

import re
from pathlib import Path

import yaml

from app.core.config import Settings

ROOT = Path(__file__).resolve().parents[2]
COMPOSE = yaml.safe_load((ROOT / "docker-compose.yml").read_text(encoding="utf-8"))
SERVICES = COMPOSE["services"]


def _settings_fields() -> set[str]:
    return {name.upper() for name in Settings.model_fields}


def _agro_vars(text: str) -> set[str]:
    return set(re.findall(r"\bAGRO_([A-Z0-9_]+)\b", text))


def test_compose_declares_the_expected_services() -> None:
    assert {"db", "api", "web", "tests", "tests-pg"} <= set(SERVICES)
    assert SERVICES["db"]["image"].startswith("postgres:16")
    assert "healthcheck" in SERVICES["db"] and "healthcheck" in SERVICES["api"]


def test_api_waits_for_a_healthy_database_and_migrates_before_serving() -> None:
    api = SERVICES["api"]
    assert api["depends_on"]["db"]["condition"] == "service_healthy"
    command = api["command"]
    assert command.index("alembic upgrade head") < command.index("uvicorn")
    url = api["environment"]["AGRO_DATABASE_URL"]
    assert url.startswith("postgresql+asyncpg://") and "@db:5432/" in url
    assert str(api["environment"]["AGRO_AUTO_CREATE_TABLES"]).lower() == "false"


def test_web_depends_on_a_healthy_api_and_targets_an_existing_stage() -> None:
    web = SERVICES["web"]
    assert web["depends_on"]["api"]["condition"] == "service_healthy"
    dockerfile = (ROOT / "frontend" / "Dockerfile").read_text(encoding="utf-8")
    stages = set(re.findall(r"^FROM .* AS (\w+)$", dockerfile, flags=re.MULTILINE))
    assert web["build"]["target"] in stages
    assert {"dev", "build", "prod"} <= stages
    assert web["environment"]["API_PROXY_TARGET"] == "http://api:8000"


def test_every_build_context_has_its_dockerfile() -> None:
    for name, service in SERVICES.items():
        if "build" in service:
            context = ROOT / service["build"]["context"]
            assert (context / "Dockerfile").is_file(), name
            assert (context / ".dockerignore").is_file(), name


def test_compose_only_uses_settings_the_app_knows() -> None:
    known = _settings_fields()
    for name, service in SERVICES.items():
        for variable in service.get("environment", {}):
            if variable.startswith("AGRO_") and not variable.startswith("AGRO_TEST_"):
                assert variable.removeprefix("AGRO_") in known, (name, variable)


def test_env_examples_only_use_settings_the_app_knows() -> None:
    known = _settings_fields()
    for path in (ROOT / ".env.example", ROOT / "backend" / ".env.example"):
        unknown = _agro_vars(path.read_text(encoding="utf-8")) - known
        assert not unknown, (path.name, unknown)


def test_backend_image_installs_runtime_dependencies_including_the_postgres_driver() -> None:
    requirements = (ROOT / "backend" / "requirements.txt").read_text(encoding="utf-8")
    for package in ("asyncpg", "alembic", "fastapi", "sqlalchemy"):
        assert package in requirements.lower(), package
    dockerfile = (ROOT / "backend" / "Dockerfile").read_text(encoding="utf-8")
    assert "requirements.txt" in dockerfile and "uvicorn" in dockerfile


def test_pg_test_service_uses_a_separate_test_database() -> None:
    url = SERVICES["tests-pg"]["environment"]["AGRO_TEST_DATABASE_URL"]
    assert url.endswith("_test") and "@db:5432/" in url
    assert SERVICES["tests-pg"]["depends_on"]["db"]["condition"] == "service_healthy"


def test_nginx_proxies_api_and_health_to_the_api_service() -> None:
    nginx = (ROOT / "frontend" / "nginx.conf").read_text(encoding="utf-8")
    assert "location /api/" in nginx and "proxy_pass http://api:8000" in nginx
    assert "location = /health" in nginx
    assert "try_files $uri $uri/ /index.html" in nginx  # SPA
