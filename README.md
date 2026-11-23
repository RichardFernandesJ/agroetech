# Agro & Tech

RPG de fazenda para navegador. Monorepo com **API FastAPI/PostgreSQL** e
**cliente Phaser 3/TypeScript**.

> **Status:** Fase 1 (Fundação) concluída. O backend cobre contas, fazendas,
> inventário, plantio, colheita e produção offline, com migrações Alembic. O
> frontend entrega o boot do Phaser, uma cena placeholder responsiva e o health
> check da API. A próxima fase é o mundo jogável (personagem, mapa e
> movimentação).

## Stack

| Camada | Tecnologias |
|---|---|
| Frontend | Phaser 3.90, TypeScript 5, Vite 8 |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2 async, Pydantic v2, PyJWT |
| Banco | PostgreSQL 16 + Alembic |
| Testes | Pytest, SQLite em memória, `ruff` |
| Infra | Docker, Docker Compose, nginx (build de produção) |

## Estrutura

```
agroetech/
├── backend/
│   ├── app/
│   │   ├── api/            # rotas, dependências, erros, serializers
│   │   ├── core/           # config, banco, JWT, exceções, tempo
│   │   ├── game/           # catálogo, status, regras puras
│   │   ├── models/         # SQLAlchemy
│   │   ├── repositories/   # acesso a dados
│   │   ├── schemas/        # contratos Pydantic
│   │   ├── services/       # regras de negócio
│   │   └── main.py
│   ├── alembic/            # migrações versionadas
│   ├── tests/
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── config/         # env tipado + configuração do Phaser
│   │   ├── game/scenes/    # BootScene, FarmScene (placeholder)
│   │   ├── services/       # ApiClient, systemService
│   │   ├── styles/
│   │   └── main.ts
│   ├── Dockerfile          # alvos dev, build e prod
│   ├── nginx.conf
│   ├── vite.config.ts
│   └── package.json
├── docs/
│   ├── architecture.md     # visão técnica do monorepo
│   ├── decisions.md        # ADRs
│   ├── GDD.md              # regras e mecânicas do jogo
│   ├── API.md              # endpoints e contratos
│   ├── DATABASE.md         # schema, índices e migrações
│   ├── ROADMAP.md          # fases e progresso
│   └── CHANGELOG.md        # histórico de alterações
├── docker-compose.yml
├── .env.example
└── README.md
```

## Arquitetura em uma tela

```
HTTP → app/api → app/services → app/repositories → app/models → PostgreSQL
                      │
                      └── app/game (regras puras, sem banco/HTTP)

Phaser (cenas) → services (HTTP) → /api/v1 → FastAPI
```

- **Backend em camadas:** rotas não acessam SQL; services não importam FastAPI;
  repositories não contêm regras de jogo.
- **Cliente:** cenas cuidam de renderização/input; chamadas HTTP ficam em
  `src/services`. O servidor é a fonte da verdade de tempo, inventário e
  recompensas.
- **Produção offline:** simulada sob demanda, sem cron/worker, com janela e teto
  de ciclos configuráveis.
- **Docker:** Vite faz proxy para a API em dev; nginx faz o mesmo no build de
  produção. A mesma build do frontend serve qualquer ambiente.

Documentação:

- [`docs/architecture.md`](docs/architecture.md) — visão técnica e fluxo de uma
  requisição.
- [`docs/decisions.md`](docs/decisions.md) — ADRs com contexto e consequências.
- [`docs/GDD.md`](docs/GDD.md) — design do jogo e regras de agricultura.
- [`docs/API.md`](docs/API.md) — endpoints, payloads e erros.
- [`docs/DATABASE.md`](docs/DATABASE.md) — tabelas, índices e migrações.
- [`docs/ROADMAP.md`](docs/ROADMAP.md) — fases, status e próxima entrega.
- [`docs/CHANGELOG.md`](docs/CHANGELOG.md) — histórico de versões.

## Executando com Docker (recomendado)

Pré-requisitos: Docker Desktop com Compose v2.

```bash
# 1. Configure as variáveis do Compose
cp .env.example .env        # Windows: copy .env.example .env

# 2. Suba banco, API e frontend
docker compose up --build
```

| Serviço | URL |
|---|---|
| Jogo (Vite) | <http://localhost:5173> |
| API | <http://localhost:8000> |
| Swagger UI | <http://localhost:8000/docs> |
| Health check | <http://localhost:8000/health> |
| PostgreSQL | `localhost:5432` (`agro` / `agro` / `agroetech`) |

Comandos úteis:

```bash
docker compose logs -f api          # logs da API
docker compose logs -f web          # logs do Vite
docker compose exec db psql -U agro -d agroetech
docker compose down                 # para os serviços
docker compose down -v              # para e apaga o volume do banco
```

O serviço `api` executa `alembic upgrade head` antes de iniciar o Uvicorn. O
schema é versionado; `AGRO_AUTO_CREATE_TABLES` fica `false`.

## Desenvolvimento local (sem Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate           # Windows
# source .venv/bin/activate      # Linux/macOS

pip install -r requirements-dev.txt
copy .env.example .env           # ajuste AGRO_DATABASE_URL para localhost

alembic upgrade head             # cria/atualiza o schema
uvicorn app.main:app --reload
```

Se não quiser instalar PostgreSQL, os testes rodam com SQLite em memória. Para
subir apenas o banco via Docker:

```bash
docker compose up -d db
```

E use no `backend/.env`:

```env
AGRO_DATABASE_URL=postgresql+asyncpg://agro:agro@localhost:5432/agroetech
```

### Migrações

```bash
cd backend
alembic upgrade head
alembic current
alembic revision --autogenerate -m "descreva a mudança"
alembic downgrade -1
```

Se o banco já existir com o schema antigo criado por `create_all`, marque a
revisão inicial antes de continuar:

```bash
alembic stamp 0001_foundation
```

O fluxo completo está em [`docs/DATABASE.md`](docs/DATABASE.md).

### Frontend

```bash
cd frontend
npm install
npm run dev
```

O Vite abre em <http://localhost:5173> e encaminha `/api` e `/health` para
`http://localhost:8000` por padrão. Para outro alvo:

```bash
API_PROXY_TARGET=http://localhost:8000 npm run dev
```

As variáveis `VITE_*` estão documentadas em `frontend/.env.example`.

## Testes e qualidade

```bash
# Backend: 34 testes (API, regras puras e migrações)
cd backend
pytest
ruff check .

# Frontend: typecheck + build
cd frontend
npm run typecheck
npm run build
```

Via Docker, sem instalar Python/Node:

```bash
docker compose --profile test run --rm tests
```

## API

Base: `/api/v1`. Rotas com 🔒 exigem `Authorization: Bearer <token>`.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/register` | Cria conta (e-mail, username, senha). |
| POST | `/auth/login` | Login por e-mail ou username; devolve JWT. |
| GET | `/auth/me` 🔒 | Jogador autenticado. |
| POST | `/properties` 🔒 | Cria fazenda + kit inicial de sementes. |
| GET | `/properties` 🔒 | Lista fazendas do jogador. |
| GET | `/properties/{id}` 🔒 | Detalha uma fazenda. |
| GET | `/properties/{id}/inventory` 🔒 | Sementes e produtos. |
| GET | `/properties/{id}/plantings` 🔒 | Plantios ativos (sincroniza produção offline). |
| POST | `/properties/{id}/plantings` 🔒 | Planta em um talhão. |
| POST | `/properties/{id}/harvest` 🔒 | Colhe todos os plantios prontos. |
| POST | `/plantings/{id}/harvest` 🔒 | Colhe um plantio. |
| POST | `/properties/{id}/production/sync` 🔒 | Simula o tempo offline. |
| GET | `/catalog/crops` | Catálogo público de culturas. |
| GET | `/catalog/items` | Catálogo público de itens. |

Exemplo mínimo:

```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@agro.com.br","username":"ana","password":"colheita2026"}'

TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"login":"ana","password":"colheita2026"}' | jq -r .access_token)
```

## Escopo desta etapa

**Fase 1 — concluída**

- Monorepo com backend e frontend independentes e repositório Git.
- API em camadas, autenticação JWT, fazendas, inventário, plantio, colheita.
- Produção offline com janela de 12h e teto de 8 ciclos por plantio.
- Migrações Alembic com revisão inicial e teste de paridade com os models.
- Docker Compose com PostgreSQL, API, Vite e profile de testes.
- Phaser 3 inicializado, cena placeholder responsiva e health check da API.
- README, arquitetura, ADRs, GDD, API, banco, roadmap e changelog.

**Próxima fase — Mundo**

- Modelo `Character` e criação de personagem.
- Mapa inicial em pixel art, movimentação, colisões e interações.
- Telas de login/cadastro e armazenamento de sessão no cliente.
- Integração da fazenda com a API (inventário, plantio, colheita).

Depois: economia (AGC), loja, animais, construções, mercado e multiplayer.
Detalhes em [`docs/ROADMAP.md`](docs/ROADMAP.md).

## Decisões técnicas

Resumo:

- Backend em camadas com regras de jogo isoladas em `app/game`.
- SQLAlchemy assíncrono com PostgreSQL; SQLite apenas nos testes.
- Produção offline preguiçosa, determinística e sem worker.
- Phaser 3 + Vite + TypeScript estrito; proxy para evitar CORS.
- Docker Compose para desenvolvimento e imagem multi-stage para produção.

O racional de cada decisão está em [`docs/decisions.md`](docs/decisions.md).
