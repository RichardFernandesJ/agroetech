# Agro & Tech

Simulador de fazenda na ilha para navegador em pixel art ("God-view"). Monorepo com **API FastAPI/PostgreSQL** e **cliente Phaser 3/TypeScript**.

> **Status:** MVP completo e Fase 5 (produção) avançada. O jogador administra a própria ilha só com o mouse: planta e colhe, vende no mercado com AgroCoin, melhora construções, cria animais, fabrica produtos em estações e evolui numa árvore de talentos com quatro ramos e presets. Tudo é validado no servidor e a produção continua offline. A próxima fase é o multiplayer econômico. Veja `docs/ROADMAP.md` e, para validar na stack real, `docs/VALIDATION.md`.

## Stack

| Camada | Tecnologias |
|---|---|
| Frontend | Phaser 3.90, TypeScript 5, Vite 8 |
| Backend | Python 3.12+, FastAPI, SQLAlchemy 2 async, Pydantic v2, PyJWT |
| Banco | PostgreSQL 16 + Alembic |
| Testes | Pytest (SQLite e PostgreSQL), Playwright, `ruff` |
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
│   │   ├── game/scenes/    # BootScene e FarmScene
│   │   ├── game/world/     # mapa, texturas procedurais e construção do mundo
│   │   ├── services/       # ApiClient e serviços de API
│   │   ├── state/          # sessão (JWT) e estado do jogo
│   │   ├── styles/
│   │   ├── ui/             # painéis DOM (login, personagem), HUD e toque
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
# Backend (SQLite em memória, rápido): API, regras puras, migrações e integridade
cd backend
pytest
ruff check .

# Frontend: tipos, build e E2E (sobe a API em SQLite e o Vite sozinho)
cd frontend
npm run typecheck
npm run build
npm run test:e2e
```

Contra **PostgreSQL real** (travas de linha, migrações e requisições concorrentes de verdade):

```bash
docker compose --profile test run --rm tests-pg
# ou, com um PostgreSQL local (o banco precisa terminar em _test):
AGRO_TEST_DATABASE_URL=postgresql+asyncpg://agro:agro@localhost:5432/agroetech_test pytest -v
```

Com a stack no ar (`docker compose up`), o roteiro de fumaça percorre o ciclo principal e dispara
compras simultâneas: `python scripts/smoke.py`. O passo a passo completo, com o checklist manual
no navegador, está em [`docs/VALIDATION.md`](docs/VALIDATION.md). O CI (`.github/workflows/ci.yml`)
roda tudo isso, inclusive em PostgreSQL, a cada `push`.

## API

Base: `/api/v1`. Rotas com 🔒 exigem `Authorization: Bearer <token>`.

| Método | Rota | Descrição |
|---|---|---|
| POST | `/auth/register` | Cria conta (e-mail, username, senha). |
| POST | `/auth/login` | Login por e-mail ou username; devolve JWT. |
| GET | `/auth/me` 🔒 | Jogador autenticado. |
| POST | `/characters` 🔒 | Cria o personagem e, se preciso, a fazenda inicial. |
| GET | `/characters/me` 🔒 | Personagem do jogador autenticado. |
| PATCH | `/characters/me/position` 🔒 | Persiste posição e direção no mapa. |
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

**Fase 1 — Fundação (Concluída)**

- Monorepo com backend e frontend independentes e repositório Git.
- API em camadas, autenticação JWT, fazendas, inventário, plantio, colheita.
- Produção offline com janela de 12h e teto de 8 ciclos por plantio.
- Migrações Alembic com revisão inicial e teste de paridade com os models.
- Docker Compose com PostgreSQL, API, Vite e profile de testes.

**Fase 2 — Ilha & Câmera Livre (Concluída)**

- Cenário em Ilha cercada por mar profundo, águas rasas, praias e interior fértil.
- Remoção do avatar físico controlável (jogabilidade panorâmica "God-view").
- Câmera livre com Pan (arraste do mouse/toque) e Zoom in/out dinâmico pela roda do mouse (0.45x a 2.2x).
- Botões de zoom e recentralização no HUD para acessibilidade desktop e mobile.

**Fase 3 — Agricultura Point & Click (Concluída)**

- Ciclo completo de cultivo com o mouse: clique no talhão vazio para abrir o modal de sementes e plantar.
- Feedback visual em tempo real: brotos verdejantes e plantas maduras coloridas.
- Indicador pulsante de colheita pronta nos talhões maduros.
- Colheita individual com 1 clique (com números flutuantes de recompensa) e botão de colheita rápida no HUD.
- Modais DOM dedicados para a Sede da Fazenda (Casa) e o Armazém do Mercado.

**Próxima fase — Economia básica (Fase 4)**

- Carteira de AgroCoin (AGC) e livro-razão (`WalletLedger`).
- Venda de safras colhidas e compra de novas sementes no mercado.
- Melhorias de capacidade de armazenamento e expansão da ilha.

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
