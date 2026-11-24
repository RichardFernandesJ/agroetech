# Arquitetura — Agro & Tech

Documento de referência da fundação do projeto. O objetivo desta etapa é ter
um monorepo executável, com responsabilidades separadas e espaço para crescer
sem reescrever a base.

## 1. Visão geral

O Agro & Tech é um RPG de fazenda para navegador. O cliente é um jogo Phaser 3
executado no browser; o servidor é uma API REST em FastAPI. O servidor é a
fonte da verdade para contas, fazendas, inventário, plantios e tempo de
produção — o cliente nunca calcula recompensas sozinho.

```
┌──────────────────────────┐        HTTPS/JSON        ┌──────────────────────────┐
│  Frontend (Phaser 3/TS)  │ ───────────────────────▶ │  Backend (FastAPI)       │
│  Vite · cenas · API      │ ◀─────────────────────── │  services · repositories │
└──────────────────────────┘                          └────────────┬─────────────┘
                                                                   │ SQLAlchemy async
                                                                   ▼
                                                          ┌──────────────────┐
                                                          │   PostgreSQL 16  │
                                                          └──────────────────┘
```

Em desenvolvimento, o Vite faz proxy de `/api` e `/health` para o FastAPI. Em
produção, o nginx dentro da imagem do frontend faz o mesmo. Assim o browser
sempre conversa com a mesma origem e não há necessidade de liberar CORS para
cada deploy.

## 2. Estrutura do monorepo

```
agroetech/
├── backend/
│   ├── app/
│   │   ├── api/            # HTTP: rotas, dependências, erros, serializers
│   │   ├── core/           # config, banco, JWT, exceções, tempo
│   │   ├── game/           # catálogo, status e regras puras do jogo
│   │   ├── models/         # SQLAlchemy
│   │   ├── repositories/   # acesso a dados
│   │   ├── schemas/        # contratos Pydantic
│   │   ├── services/       # regras de negócio
│   │   └── main.py
│   ├── alembic/            # migrações versionadas
│   ├── tests/              # Pytest (API, regras puras, migrações)
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements*.txt
├── frontend/
│   ├── src/
│   │   ├── config/         # env e configuração do Phaser
│   │   ├── game/scenes/    # cenas Phaser
│   │   ├── services/       # cliente HTTP e serviços de API
│   │   ├── styles/
│   │   ├── main.ts
│   │   └── vite-env.d.ts
│   ├── Dockerfile          # alvos dev, build e prod
│   ├── nginx.conf
│   ├── vite.config.ts
│   └── package.json
├── docs/
│   ├── architecture.md
│   ├── decisions.md
│   ├── GDD.md
│   ├── API.md
│   ├── DATABASE.md
│   ├── ROADMAP.md
│   └── CHANGELOG.md
├── docker-compose.yml
├── .env.example
└── README.md
```

## 3. Frontend

### Responsabilidades

| Pasta | Responsabilidade |
|---|---|
| `src/config` | Variáveis de ambiente tipadas e configuração do `Phaser.Game`. |
| `src/game/scenes` | `BootScene` (autenticação/carregamento) e `FarmScene` (só monta os módulos e cuida do ciclo de vida, ≈100 linhas). |
| `src/game/scenes/farm` | Módulos da fazenda: `CameraController` (pan, zoom e filtro de eventos do mundo), `PlotRenderer` (o que cresce em cada talhão), `FarmController` (dados, plantio, colheita e sincronização), `FarmPanels` (painéis e menu do HUD), `bindWorldInteractions` (hover e cliques) e `FarmState` (estado compartilhado). Uma estrutura ou sistema novo entra em `FarmPanels` (painel + item de menu) e `world-interactions` (clique no mapa). |
| `src/ui` | Painéis DOM sobre o jogo. `ModalManager` garante um painel aberto por vez; cada painel recebe `onClose` e não conhece a cena. O HUD tem um **menu declarativo** (`HudMenuItem[]`): um sistema novo (estrutura, guilda, fábrica) entra com um item de menu e um painel. |
| `src/ui/talents` | Árvore de talentos dividida por responsabilidade: `talent-map` (SVG com pan/zoom), `talent-sidebar` (detalhes), `talent-presets-bar` (builds) e `talent-rules` (regras de exibição; o servidor é a autoridade). `ui/talent-modal.ts` orquestra. |
| `src/game/world` | Geração orgânica do mapa da ilha (`map.ts`), posicionamento de estruturas (`build-world.ts`) e texturas procedurais pixel art (`textures.ts`). |
| `src/services` | Comunicação HTTP com a API (`propertyService`, `characterService`, etc.) e tratamento padronizado de erros. |
| `src/state` | Gerenciamento de sessão JWT (`session.ts`) e estado local do jogador. |
| `src/ui` | HUD moderno e modais DOM sobrepostos (`PlantingModal`, `HouseModal`, `MarketModal`, `AuthPanel`, `CharacterPanel`). |
| `src/styles` | Reset, layout, HUD e design dos modais. |

### Fluxo de jogo e interação

1. `main.ts` cria o `Phaser.Game` com `GAME_CONFIG`.
2. `BootScene` valida a conexão com a API, restaura sessão ou apresenta o login/cadastro.
3. `FarmScene` desenha a **Ilha** em pixel art cercada por oceano e centraliza a visão aérea ("God-view").
4. **Navegação Livre:** O jogador usa o mouse para arrastar a tela (pan) e a roda do mouse para zoom in e out com foco inteligente sob o ponteiro (0.45x a 2.2x), ou botões no HUD.
5. **Cultivo Direto por Clique:**
   - Clicar em um talhão vazio abre o `PlantingModal` com as sementes do inventário para plantio imediato.
   - Os talhões refletem os estágios em tempo real: brotos verdejantes e plantas maduras com distintivo dourado pulsante.
   - Clicar no talhão maduro realiza a colheita instantânea com animação flutuante de recompensas.
   - Botão no HUD permite colher todos os talhões prontos em um só clique.
6. **Estruturas:** Clicar na Casa abre métricas e logout; clicar no Mercado abre o inventário/armazém.
7. A sincronização periódica de plantios roda a cada 4 segundos, mantendo a tela atualizada com o servidor.

### Decisões de frontend

- **Vite**: dev server rápido, proxy nativo e build estático simples.
- **TypeScript estrito**: `strict`, `noUnusedLocals`, `noUnusedParameters`,
  `noUncheckedIndexedAccess`.
- **God-View sem avatar físico:** Elimina atrito de locomoção e foca 100% na gestão da fazenda.
- **Interface Híbrida (Canvas + DOM):** O mundo da ilha roda em Canvas de alta performance no Phaser; formulários, HUD e modais usam DOM nítido e acessível sobreposto.
- **Pixel Art Nítido:** Configurações `pixelArt: true` e `roundPixels: true` garantem que os tiles não sofram borramento durante o zoom.
- **Alias `@/`**: evita caminhos relativos profundos.
- **Sem framework de UI**: o jogo é o canvas; HUDs complexos podem usar
  HTML/DOM sobreposto no futuro.
- **Phaser 3**: requisito do projeto e ecossistema estável. Phaser 4 não foi
  adotado nesta fundação.

## 4. Backend

### Camadas e direção de dependência

```
api → services → repositories → models
        │
        └──▶ game (regras puras)
```

- `api` conhece HTTP, mas não SQL.
- `services` conhece as regras do jogo, mas não FastAPI.
- `repositories` conhece SQLAlchemy, mas não regras de jogo.
- `models` apenas mapeia tabelas e constraints.
- `game` não conhece banco nem HTTP; é testável de forma pura.
- `schemas` define os contratos de entrada/saída.

### Transações

`get_db` abre uma sessão por request, faz `commit` no sucesso e `rollback` em
exceção. Services chamam `flush` quando precisam de IDs ou de consultas
intermediárias. A regra de negócio não fica acoplada ao ciclo de vida HTTP.

### Erros

Services lançam exceções de domínio (`NotFoundError`, `ConflictError`,
`GameRuleError`, `AuthenticationError`). Um handler único converte para:

```json
{ "detail": "Mensagem para o jogador.", "code": "conflict" }
```

O cliente usa `ApiError` para preservar `status` e `code`, permitindo que a UI
decida entre toast, tela de erro ou retry.

### Produção offline

Não há worker nem cron. A produção é simulada sob demanda ao acessar a fazenda,
plantar, colher ou chamar `POST /production/sync`:

1. `window_start = max(last_sync, now - offline_max_hours)`.
2. Ciclos concluídos dentro da janela são armazenados no plantio.
3. O total é limitado por `offline_max_cycles_per_planting` e por
   `max_cycles` da cultura.
4. Ciclos antigos são descartados.
5. A colheita continua manual; a produção offline apenas prepara os ciclos.

A matemática fica em `app/game/rules.py` (`simulate_growth`) e é testada sem
banco.

## 5. Dados

```
User 1 ─── N Property 1 ─── N InventoryItem
                   │
                   └────── N Planting ──▶ CropDefinition (código)
```

- IDs UUID; timestamps em UTC.
- Um índice parcial garante um único plantio ativo por talhão.
- `inventory_items` tem unicidade por `(property_id, item_id)` e quantidade
  não negativa.
- O catálogo de culturas é conteúdo versionado em código. Se virar tabela, os
  services não precisam mudar (basta trocar a implementação de consulta).
- O schema é versionado pelo Alembic. A revisão `0001_foundation` cria as
  quatro tabelas, índices e constraints; `tests/test_migrations.py` garante que
  ela continua igual aos models.
- `AGRO_AUTO_CREATE_TABLES` tem padrão `false`. `create_all` só é usado nos
  testes de API, que não exercitam o ciclo de migração.

## 6. Infraestrutura Docker

| Serviço | Imagem / build | Porta padrão | Papel |
|---|---|---:|---|
| `db` | `postgres:16-alpine` | 5432 | Banco relacional. |
| `api` | `backend/Dockerfile` | 8000 | FastAPI + Uvicorn (reload em dev). |
| `web` | `frontend/Dockerfile` (target `dev`) | 5173 | Vite dev server com HMR. |
| `tests` | `backend/Dockerfile` (profile `test`) | — | Pytest isolado. |

- `db` tem healthcheck com `pg_isready`.
- `api` executa `alembic upgrade head` e só então inicia o Uvicorn; tem
  healthcheck em `/health`.
- `web` só inicia depois da API saudável.
- Volumes: código montado para hot reload; `pgdata` persiste o banco;
  `/app/node_modules` fica em volume anônimo para não conflitar com o host.
- A imagem do frontend tem alvos `dev`, `build` e `prod` (nginx).

## 7. Ambientes

| Arquivo | Uso |
|---|---|
| `.env` (raiz) | Variáveis do Docker Compose (credenciais, portas, segredo JWT). |
| `backend/.env` | Execução local do backend fora do Docker. |
| `frontend/.env` | Sobrescreve `VITE_*` no desenvolvimento local. |

Nenhum `.env` real é versionado; apenas os `.env.example`.

## 8. Qualidade

- **Backend**: `pytest` com SQLite em memória e override de `get_db`; a suíte
  de migração usa um arquivo SQLite temporário e a API do Alembic; `ruff` para
  lint/format.
- **Frontend**: `tsc --noEmit` (typecheck) e `vite build` como validação.
- **Contratos**: Pydantic no servidor; interfaces TypeScript espelham os DTOs
  usados pelos serviços do cliente.
- **Convenções**: identificadores e código em inglês; textos de jogo e
  documentação em português; dinheiro/tempo sempre no servidor.

## 9. Caminhos de evolução

1. Fase 2: personagem, mapa, movimentação, colisões e interações.
2. Tela de login e armazenamento seguro do token (memória + refresh).
3. Integração da fazenda com inventário, plantio e colheita.
4. Estado do jogo no cliente (store) e HUD em DOM.
5. Assets, atlas e pipeline de áudio.
6. Loja, mercado e economia de moedas.
7. WebSocket/SSE para atualizar culturas prontas em tempo real.
8. Redis/workers apenas quando houver produção passiva global ou eventos
   entre jogadores.
9. CI/CD, observabilidade e rate limiting.
