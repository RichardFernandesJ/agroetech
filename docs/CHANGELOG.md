# Changelog — Agro & Tech

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento semântico para a API e o cliente.

## [Não lançado]

### Próximo

- Fase 2: modelo `Character`, criação de personagem, mapa e movimentação.
- Integração do Phaser com inventário, plantio e colheita.
- Testes E2E com Playwright.

## [0.1.1] — 2026-11-22

### Adicionado

- Alembic configurado para engine assíncrona (`backend/alembic/`).
- Revisão inicial `0001_foundation` com usuários, propriedades, inventário e
  plantios, incluindo o índice parcial de um plantio ativo por talhão.
- Teste `tests/test_migrations.py` comparando schema migrado com os models e
  validando upgrade/downgrade.
- Documentos obrigatórios: `docs/GDD.md`, `docs/API.md`, `docs/DATABASE.md`,
  `docs/ROADMAP.md` e este `CHANGELOG.md`.
- Repositório Git inicializado com `.gitignore` para Python, Node, env e bancos
  locais.

### Alterado

- `AGRO_AUTO_CREATE_TABLES` agora tem padrão `false`; o schema é criado por
  `alembic upgrade head`.
- Docker Compose executa as migrações antes de iniciar o Uvicorn.
- `requirements.txt` inclui `alembic`.
- README e documentação de arquitetura atualizados com o fluxo de migrações e o
  status real do roadmap.

### Validado

- `pytest`: 34 testes passando.
- `ruff check`: sem erros.
- Migração aplicada e revertida em SQLite temporário.
- Build do frontend (`tsc --noEmit` + `vite build`) sem erros.

## [0.1.0] — 2026-11-22

### Adicionado

- Monorepo com `backend/` (FastAPI) e `frontend/` (Phaser 3 + TypeScript).
- Backend em camadas: `api`, `services`, `repositories`, `models`, `schemas`,
  `game`, `core`.
- Cadastro, login por e-mail/username, JWT HS256 e `/auth/me`.
- Propriedades com kit inicial de sementes.
- Inventário por propriedade.
- Plantio, crescimento, colheita individual e em lote.
- Produção offline preguiçosa com janela de 12h e teto de 8 ciclos por plantio.
- Catálogo público de 5 culturas e itens.
- Docker Compose com PostgreSQL 16, API, Vite e profile de testes.
- Frontend com Vite, TypeScript estrito, `BootScene`, `FarmScene` placeholder,
  cliente HTTP e health check.
- 33 testes de API e regras puras.
- README, `docs/architecture.md` e `docs/decisions.md`.

### Limitações conhecidas

- Docker Compose não foi executado no ambiente de desenvolvimento (Docker
  indisponível); foi validado como YAML e o runtime com Uvicorn + SQLite.
- Sem criação de personagem, mapa ou movimentação.
- Sem economia, loja, animais, construções ou multiplayer.
- Sem refresh token, revogação ou rate limiting.
