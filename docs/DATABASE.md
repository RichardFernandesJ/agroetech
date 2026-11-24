# Banco de dados — Agro & Tech

Banco principal: **PostgreSQL 16**. Driver: `asyncpg` via SQLAlchemy 2 async.
Testes usam SQLite em memória (`aiosqlite`), exceto o teste de migração, que usa
um arquivo SQLite temporário.

O schema é versionado com **Alembic**. `AGRO_AUTO_CREATE_TABLES=true` existe
apenas para bancos descartáveis de prototipagem.

## 1. Modelo entidade-relacionamento

```
┌──────────────┐
│    users     │
│──────────────│
│ id (PK)      │
│ email  UQ    │
│ username UQ  │
└──────┬───────┘
       │ 1:N (owner_id, CASCADE)
       ▼
┌──────────────────────┐
│      properties      │
│──────────────────────│
│ id (PK)              │
│ owner_id (FK)        │
│ name                 │
│ area_hectares        │
│ plot_count           │
│ last_production_sync │
└──────┬───────────┬───┘
       │ 1:N       │ 1:N
       ▼           ▼
┌───────────────┐  ┌────────────────────┐
│inventory_items│  │     plantings      │
│───────────────│  │────────────────────│
│ id (PK)       │  │ id (PK)            │
│ property_id   │  │ property_id (FK)   │
│ item_id       │  │ crop_id            │
│ quantity      │  │ plot_index         │
│ UQ(prop,item) │  │ status             │
└───────────────┘  │ stored_cycles      │
                   └────────────────────┘
                            │
                            ▼
                   catálogo em código
                   (app/game/catalog.py)
```

O catálogo de culturas/itens **não** é tabela nesta etapa: é conteúdo
versionado em código. `crop_id` e `item_id` são strings estáveis.

## 2. Convenções

- Chaves primárias: `UUID` geradas na aplicação (`uuid.uuid4`).
- Timestamps: `TIMESTAMPTZ` em UTC; `created_at` e `updated_at` em todas as
  tabelas.
- Nomes: tabelas em plural, colunas em `snake_case`, constraints prefixadas
  (`ck_`, `uq_`, `ix_`).
- Exclusões: `ON DELETE CASCADE` de `users` → `properties` → filhos.
- Dinheiro e tempo são responsabilidade do servidor; não há colunas calculadas
  pelo cliente.
- Toda alteração estrutural passa por uma revisão do Alembic.

## 3. Tabelas

### `users`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `email` | VARCHAR(255) | NOT NULL, único (`ix_users_email`) |
| `username` | VARCHAR(50) | NOT NULL, único (`ix_users_username`) |
| `password_hash` | VARCHAR(255) | NOT NULL; PBKDF2-HMAC-SHA256 |
| `is_active` | BOOLEAN | NOT NULL |
| `created_at` | TIMESTAMPTZ | NOT NULL |
| `updated_at` | TIMESTAMPTZ | NOT NULL |

E-mail e username são gravados em minúsculas pelo serviço de autenticação.

### `properties`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `owner_id` | UUID | FK `users.id`, CASCADE, indexado |
| `name` | VARCHAR(120) | NOT NULL |
| `area_hectares` | DOUBLE PRECISION | NOT NULL, > 0 |
| `plot_count` | INTEGER | NOT NULL, 1..24 no schema; limite de serviço configurável |
| `last_production_sync_at` | TIMESTAMPTZ | NOT NULL; relógio da produção offline |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

Índice: `ix_properties_owner_id`.

### `inventory_items`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `property_id` | UUID | FK `properties.id`, CASCADE, indexado |
| `item_id` | VARCHAR(80) | NOT NULL; `seed_*` ou `crop_*` |
| `quantity` | INTEGER | NOT NULL, `>= 0` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

Constraints:

- `uq_inventory_property_item (property_id, item_id)` — uma linha por item.
- `ck_inventory_quantity_non_negative` — impede quantidade negativa.
- Índice `ix_inventory_items_property_id`.

### `plantings`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `property_id` | UUID | FK `properties.id`, CASCADE, indexado |
| `crop_id` | VARCHAR(40) | NOT NULL; referência ao catálogo |
| `plot_index` | INTEGER | NOT NULL, `>= 0` |
| `planted_at` | TIMESTAMPTZ | NOT NULL |
| `next_ready_at` | TIMESTAMPTZ | NOT NULL; próximo ciclo |
| `cycles_done` | INTEGER | NOT NULL, `>= 0` |
| `stored_cycles` | INTEGER | NOT NULL, `>= 0`; colheitas prontas |
| `status` | VARCHAR(20) | `growing` / `ready` / `exhausted` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

Constraints e índices:

- `ck_plantings_plot_index_non_negative`
- `ck_plantings_cycles_done_non_negative`
- `ck_plantings_stored_cycles_non_negative`
- `ix_plantings_property_id`
- `ix_plantings_property_status (property_id, status)`
- `uq_plantings_active_plot (property_id, plot_index) WHERE status <> 'exhausted'`

O índice parcial garante **um plantio ativo por talhão** sem impedir o histórico
de plantios esgotados. Funciona em PostgreSQL e SQLite.

### `wallets`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK `users.id`, CASCADE, único |
| `balance` | BIGINT | NOT NULL, `>= 0` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

Constraints: `uq_wallets_user_id`, `ck_wallets_balance_non_negative`.

### `wallet_ledger`

Livro-razão imutável: toda mudança de saldo gera uma linha. A soma de `amount`
sempre iguala `wallets.balance` (verificado em teste).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `wallet_id` | UUID | FK `wallets.id`, CASCADE, indexado |
| `kind` | VARCHAR(30) | `initial_grant`, `seed_purchase`, `crop_sale` |
| `amount` | BIGINT | com sinal (crédito `+`, débito `-`) |
| `balance_after` | BIGINT | `>= 0` |
| `item_id` / `quantity` / `unit_price` | — | nulos no crédito inicial |
| `fee` | INTEGER | taxa retida em vendas |
| `idempotency_key` | VARCHAR(64) | nulo ou único por carteira |

Constraints: `uq_wallet_ledger_idempotency (wallet_id, idempotency_key)`,
`ck_wallet_ledger_balance_non_negative`. Migração: `0003_wallet`.

### `player_progress`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK `users.id`, CASCADE, único |
| `xp` | BIGINT | NOT NULL, `>= 0` |
| `created_at` / `updated_at` | TIMESTAMPTZ | NOT NULL |

O nível é derivado do XP (`game/progression.py`), nunca armazenado.
Constraints: `uq_player_progress_user_id`, `ck_player_progress_xp_non_negative`.
Migração: `0004_progress`.

### `talent_presets`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `user_id` | UUID | FK `users.id`, CASCADE, indexado |
| `name` | VARCHAR(30) | NOT NULL |
| `slot` | INTEGER | NOT NULL, `>= 1` |
| `is_active` | BOOLEAN | NOT NULL |
| `last_activated_at` | TIMESTAMPTZ | nulo até a primeira troca |

Constraints: `uq_talent_presets_user_slot (user_id, slot)` e índice único parcial
`uq_talent_presets_active (user_id) WHERE is_active` (no máximo um preset ativo).

### `preset_nodes`

Talentos adquiridos por preset: `preset_id` (FK, CASCADE) + `node_id` (VARCHAR 60),
único por `(preset_id, node_id)`. O catálogo de talentos vive em código
(`game/talents.py`).

### `talent_respecs`

Auditoria de redefinições: `user_id`, `preset_id`, `nodes_removed`, `cost`,
`performed_at`.

### `plantings` (colunas novas)

`grow_seconds` (INTEGER, nulo = usa o tempo do catálogo) e `modifiers` (JSON com os
bônus em pontos-base vigentes no plantio). Migração: `0005_talents`.

### `buildings`

Uma linha por construção já melhorada na fazenda (sem linha = nível inicial do catálogo).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `property_id` | UUID | FK `properties.id`, CASCADE, indexado |
| `building_id` | VARCHAR(40) | id do catálogo (`sede`, `poco`) |
| `level` | INTEGER | NOT NULL, `>= 0` |

Constraints: `uq_buildings_property_building`, `ck_buildings_level_non_negative`.
Migração: `0006_buildings`.

### `animals`

Um animal por linha. A produção é derivada dos timestamps (sem processo por jogador).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `property_id` | UUID | FK `properties.id`, CASCADE, indexado |
| `species` | VARCHAR(30) | id do catálogo (`galinha`, `vaca`, `ovelha`) |
| `fed_until` | TIMESTAMPTZ | até quando está alimentado (nulo = nunca) |
| `last_sync_at` | TIMESTAMPTZ | última contabilização da produção |
| `progress_seconds` | FLOAT | segundos alimentados rumo ao próximo produto, `>= 0` |
| `speed_bp` / `yield_bp` | INTEGER | bônus de talentos gravados ao alimentar com fome (pontos-base) |
| `stored` | INTEGER | produtos prontos para coleta, `>= 0` |

Migrações: `0007_animals` e `0009_animal_modifiers`.

### `production_jobs`

Um trabalho de fabricação por linha (entidade `ProductionJobs` do AGENTS.md). Trabalhos
coletados permanecem como histórico (`collected_at`).

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `property_id` | UUID | FK `properties.id`, CASCADE, indexado |
| `recipe_id` / `building_id` | VARCHAR(40) | receita e estação |
| `batches` | INTEGER | `>= 1` |
| `output_item` / `output_quantity` | VARCHAR / INTEGER | definidos ao iniciar (`>= 0`) |
| `started_at` / `finish_at` | TIMESTAMPTZ | término calculado ao iniciar |
| `collected_at` | TIMESTAMPTZ | nulo enquanto aberto |
| `request_key` | VARCHAR(64) | idempotência, único por fazenda |

Índice `ix_production_jobs_property_open (property_id, collected_at)`. Migração: `0008_production_jobs`.

### `properties` (regra de unicidade)

`uq_properties_owner (owner_id)` — **uma fazenda por jogador**, garantida no banco (migração
`0010_one_property_per_user`; substitui o índice comum `ix_properties_owner_id`). A migração
recusa rodar se já houver jogadores com mais de uma fazenda.

### `market_listings`

| Coluna | Tipo | Regras |
|---|---|---|
| `id` | UUID | PK |
| `seller_id` / `seller_property_id` | UUID | FKs, CASCADE (a fazenda recebe a devolução) |
| `item_id` | VARCHAR(80) | item negociável |
| `quantity_initial` / `quantity_remaining` | INTEGER | `0 <= restante <= inicial` |
| `unit_price` | INTEGER | `>= 1` |
| `status` | VARCHAR(12) | `active`, `sold`, `cancelled`, `expired` |
| `expires_at` | TIMESTAMPTZ | validade (48 h) |
| `request_key` | VARCHAR(64) | idempotência, único por vendedor |

Índices: `ix_market_listings_browse (status, item_id, unit_price)` e `ix_market_listings_seller_status`.

### `market_transactions`

Histórico imutável: uma linha por compra (inclusive parcial).

| Coluna | Tipo | Regras |
|---|---|---|
| `listing_id` / `buyer_id` / `seller_id` | UUID | FKs, CASCADE |
| `item_id`, `quantity`, `unit_price` | — | `quantity >= 1` |
| `gross` / `fee` / `seller_net` | BIGINT | `bruto = taxa + líquido` |
| `request_key` | VARCHAR(64) | idempotência, único por comprador |

Índices por comprador, vendedor (com `created_at`) e item. Migração: `0011_exchange`.

## 4. Regras que o banco não expressa

Algumas regras ficam nos services porque dependem do catálogo ou de tempo:

- cultura existente e sementes suficientes;
- `plot_index < property.plot_count`;
- cálculo de ciclos prontos e teto offline;
- transição de `status`;
- posse da fazenda/plantio (sempre filtrada por `owner_id`).

O banco reforça o que é estrutural: unicidade, FK, quantidade não negativa, um
plantio ativo por talhão e uma fazenda por jogador.

**Concorrência.** Saldo e estoque combinam trava de linha (`FOR UPDATE`, no PostgreSQL) com
**atualização condicional**: `UPDATE wallets SET balance = :novo WHERE id = :id AND balance = :lido`
e `UPDATE inventory_items SET quantity = quantity - :n WHERE id = :id AND quantity >= :n`. Se outra
operação mudou o valor no meio, nada é gravado (409 ou 422), mesmo em bancos sem trava de linha.
Violações de unicidade causadas por corridas viram `409 conflict` (nunca 500).

## 5. Migrações

Arquivos:

```
backend/
├── alembic.ini
├── alembic/
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       └── 0001_foundation.py
```

Comandos (a partir de `backend/`):

```bash
alembic upgrade head          # aplica todas as revisões
alembic current               # revisão atual
alembic history --verbose     # histórico
alembic downgrade -1          # desfaz a última
alembic revision --autogenerate -m "descrição"
alembic upgrade head --sql    # SQL offline para revisão
```

A URL vem de `AGRO_DATABASE_URL`. Para apontar para outro banco sem alterar o
`.env`:

```bash
# PowerShell
$env:AGRO_DATABASE_URL="postgresql+asyncpg://agro:agro@localhost:5432/agroetech"
alembic upgrade head
```

No Docker Compose, o serviço `api` executa `alembic upgrade head` antes do
Uvicorn.

### Banco criado antes do Alembic

Se o banco já foi criado com `create_all` e está com o schema correto, marque a
revisão inicial sem reexecutá-la:

```bash
alembic stamp 0001_foundation
```

Depois disso, use apenas `alembic upgrade head`.

### Verificação automática

`backend/tests/test_migrations.py`:

1. aplica `0001_foundation` em um SQLite temporário;
2. compara tabelas e colunas com `Base.metadata`;
3. confere a revisão e o índice parcial;
4. executa `downgrade base` e verifica a limpeza.

Isso detecta model alterado sem migração correspondente.

## 6. Estratégia de testes

- **API/services**: SQLite em memória com `StaticPool` e `create_all`.
- **Migrações**: SQLite em arquivo temporário, via API do Alembic.
- **Produção**: PostgreSQL real; recursos como `SELECT ... FOR UPDATE` só são
  exercitados lá. O repositório de inventário usa `FOR UPDATE` para evitar
  corrida na compra/consumo de itens.

## 7. Próximas entidades (roadmap)

Fase 2: `characters` (nome, aparência, posição, fazenda atual).

Fase 4: `wallets` e `wallet_ledger` (feitos); restante: `market_listings`, `market_transactions`,
`trade_offers`, `trade_items`.

Fase 5: `animals`, `buildings`, `recipes`, `production_jobs`, `skills`,
`player_skills`.

Toda nova entidade deve vir com migração, índices para consultas por
proprietário/status e testes de autorização.
