# API — Agro & Tech

Base local: `http://localhost:8000`
Base versionada: `/api/v1`
OpenAPI interativo: `/docs` · schema JSON: `/openapi.json`

Todas as rotas de jogo exigem `Authorization: Bearer <token>`, exceto cadastro,
login e catálogo. Datas são ISO 8601 em UTC.

## 1. Autenticação

### POST `/api/v1/auth/register`

Cria a conta. E-mail e username são normalizados para minúsculas.

```json
{
  "email": "ana@agro.com.br",
  "username": "ana_fazendeira",
  "password": "colheita2026"
}
```

Regras: e-mail válido; username de 3 a 30 caracteres (`a-z`, `A-Z`, `0-9`, `_`,
`.`, `-`); senha de 8 a 128 caracteres.

**201 Created**

```json
{
  "id": "6f1c2a0e-6f6a-4d1e-9f0a-1a2b3c4d5e6f",
  "email": "ana@agro.com.br",
  "username": "ana_fazendeira",
  "is_active": true,
  "created_at": "2026-11-22T12:00:00Z"
}
```

### POST `/api/v1/auth/login`

Aceita e-mail **ou** username no campo `login`.

```json
{ "login": "ana_fazendeira", "password": "colheita2026" }
```

**200 OK**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 86400
}
```

### GET `/api/v1/auth/me` 🔒

Devolve o jogador do token no mesmo formato de `UserRead`.

## 2. Propriedades

### POST `/api/v1/properties` 🔒

Cria a fazenda e entrega o kit inicial de sementes (milho, cenoura, tomate,
morango e café).

```json
{ "name": "Fazenda Boa Vista", "area_hectares": 12.5, "plot_count": 6 }
```

`plot_count` aceita de 1 a 24; o serviço limita ao máximo configurado
(`AGRO_MAX_PLOTS_PER_PROPERTY`, padrão 12).

**201 Created**

```json
{
  "id": "9b2f...",
  "name": "Fazenda Boa Vista",
  "area_hectares": 12.5,
  "plot_count": 6,
  "created_at": "2026-11-22T12:00:00Z",
  "last_production_sync_at": "2026-11-22T12:00:00Z"
}
```

### GET `/api/v1/properties` 🔒

Lista as fazendas do jogador autenticado. Fazendas de outros jogadores não
aparecem.

### GET `/api/v1/properties/{property_id}` 🔒

Detalha uma fazenda. Propriedade de outro jogador retorna **404** de propósito.

## 3. Inventário

### GET `/api/v1/properties/{property_id}/inventory` 🔒

```json
{
  "property_id": "9b2f...",
  "items": [
    {
      "item_id": "seed_milho",
      "name": "Semente de milho",
      "category": "seed",
      "description": "Semente usada para plantar milho.",
      "quantity": 6
    },
    {
      "item_id": "crop_milho",
      "name": "Milho",
      "category": "product",
      "description": "Cultura de ciclo curto e colheita única. Ótima para começar.",
      "quantity": 0
    }
  ]
}
```

Itens sem metadados no catálogo aparecem com `category: "unknown"`.

## 4. Plantação

### GET `/api/v1/properties/{property_id}/plantings` 🔒

Sincroniza a produção offline antes de responder e lista os plantios ativos.

```json
[
  {
    "id": "b7d1...",
    "property_id": "9b2f...",
    "crop_id": "milho",
    "crop_name": "Milho",
    "plot_index": 0,
    "status": "growing",
    "planted_at": "2026-11-22T12:00:00Z",
    "next_ready_at": "2026-11-22T12:05:00Z",
    "cycles_done": 0,
    "max_cycles": 1,
    "stored_cycles": 0,
    "seconds_until_ready": 300,
    "expected_yield": 3
  }
]
```

`status`: `growing` | `ready` | `exhausted`.
`seconds_until_ready` é `0` quando pronto e `null` quando esgotado.

### POST `/api/v1/properties/{property_id}/plantings` 🔒

```json
{ "crop_id": "milho", "plot_index": 0 }
```

**201 Created** com o mesmo formato de `PlantingRead`.

Erros de regra: cultura inexistente (404), talhão inválido, sementes
insuficientes (422), talhão ocupado (409).

### POST `/api/v1/plantings/{planting_id}/harvest` 🔒

Colhe um plantio específico.

```json
{
  "planting_id": "b7d1...",
  "crop_id": "milho",
  "crop_name": "Milho",
  "cycles_harvested": 1,
  "product_item": "crop_milho",
  "product_name": "Milho",
  "product_quantity": 3,
  "seed_item": "seed_milho",
  "seed_name": "Semente de milho",
  "seed_quantity": 1,
  "planting_status": "exhausted"
}
```

### POST `/api/v1/properties/{property_id}/harvest` 🔒

Colhe todos os plantios com ciclos prontos.

```json
{
  "property_id": "9b2f...",
  "harvests": [ ... ],
  "products": { "crop_milho": 3, "crop_tomate": 6 },
  "seeds": { "seed_milho": 1, "seed_tomate": 2 }
}
```

## 5. Produção offline

### POST `/api/v1/properties/{property_id}/production/sync` 🔒

Simula o tempo decorrido e armazena ciclos maduros.

```json
{
  "property_id": "9b2f...",
  "synced_at": "2026-11-22T18:00:00Z",
  "window_start": "2026-11-22T06:00:00Z",
  "offline_seconds": 21600,
  "plantings_synced": 3,
  "cycles_stored": 2,
  "ready_plantings": 2
}
```

O resultado não altera o inventário; a colheita continua manual.

## 6. Catálogo (público)

### GET `/api/v1/catalog/crops`

```json
[
  {
    "id": "milho",
    "name": "Milho",
    "description": "Cultura de ciclo curto e colheita única. Ótima para começar.",
    "grow_seconds": 300,
    "yield_quantity": 3,
    "seed_yield": 1,
    "max_cycles": 1,
    "seed_item": "seed_milho",
    "product_item": "crop_milho"
  }
]
```

### GET `/api/v1/catalog/items`

Lista sementes e produtos com `id`, `name`, `category` e `description`.

### Carteira e Mercado (Fase 4)

Moeda: **AgroCoin (AGC)**, inteira. Preços são sempre definidos no servidor;
o cliente envia apenas `item_id` e `quantity` (1 a 999).

#### GET `/api/v1/wallet` 🔒

Cria a carteira no primeiro acesso, com crédito inicial único de 100 AGC.

```json
{ "id": "…", "balance": 100, "currency": "AGC" }
```

#### GET `/api/v1/wallet/ledger?limit=20&offset=0` 🔒

Histórico financeiro, mais recente primeiro (`limit` 1–100). Cada linha traz
`kind` (`initial_grant`, `seed_purchase`, `crop_sale`), `amount` (com sinal),
`balance_after`, item, quantidade, `unit_price` e `fee`.

#### GET `/api/v1/market/offers` 🔒

Lista `buy_price` (sementes vendidas pelo entreposto) e `sell_price` (safras
compradas), além de `fee_basis_points` (500 = 5% sobre vendas).

#### POST `/api/v1/properties/{property_id}/market/buy` 🔒
#### POST `/api/v1/properties/{property_id}/market/sell` 🔒

```json
{ "item_id": "seed_milho", "quantity": 5 }
```

Cabeçalho opcional `Idempotency-Key` (8–64 caracteres `[A-Za-z0-9_-]`): reenviar a
mesma chave com o mesmo corpo devolve o resultado original (`"replayed": true`) sem
repetir débito/crédito; a mesma chave com corpo diferente retorna `409`.

Resposta: `kind`, `item_id`, `item_name`, `quantity`, `unit_price`, `gross`, `fee`,
`amount` (variação do saldo), `balance` e `replayed`.

Erros: `422` saldo/estoque insuficiente ou item fora de negociação; `404`
propriedade de outro jogador; `409` conflito de idempotência.

O catálogo de culturas (`/catalog/crops`) agora inclui `seed_price` e `sell_price`.

### Progressão (XP e nível)

#### GET `/api/v1/progress` 🔒

```json
{ "level": 2, "xp": 60, "xp_into_level": 10, "xp_for_next": 100, "max_level": 50 }
```

XP total para o nível `L`: `25 * (L - 1) * L` (nível 2 = 50, nível 10 = 2.250, nível 50 = 61.250).
O nível máximo é 50 e o XP não passa disso. O XP vem de:

- plantar: 2 XP;
- colher: `harvest_xp` da cultura por ciclo colhido (milho 8, cenoura 14, tomate 18,
  morango 26, café 70).

As respostas de colheita (`/plantings/{id}/harvest` e `/properties/{id}/harvest`)
incluem `xp_gained`. O catálogo de culturas inclui `harvest_xp`.

### Talentos (Fase 4.5)

Pontos: 1 por nível a partir do nível 2 (49 no nível 50). Espaços de preset:
`1 + nível // 10`, no máximo 5. Detalhes de design em [`TALENTS.md`](TALENTS.md).

#### GET `/api/v1/catalog/talents` (público)

Mapa completo: `branches` (com `available`), `nodes` (custo, camada, nível mínimo,
`requires`, `requires_any`, `branch_points`, `exclusive_group`, `effects` e posição
`x`/`y`) e o centro do mapa.

#### GET `/api/v1/talents` 🔒

Estado do jogador: `points_total/spent/available`, `presets` (com `node_ids`),
`active_preset_id`, `switch_available_at`, `reset_cost`, `reset_is_free`,
`build_locked` e `modifiers` (totais de bônus do preset ativo, em pontos-base).
Cria o preset "Build 1" no primeiro acesso.

#### POST `/api/v1/talents/allocate` 🔒 · `{ "node_id": "agro_solo_fertil" }`

Adquire um talento no preset ativo. `422` se faltar ponto, nível, pré-requisito ou
pontos no ramo; `409` se já possuir o talento ou outro mestre do mesmo ramo; `404` se
não existir. Retorna o estado.

#### POST `/api/v1/talents/reset` 🔒

Redefine o preset ativo. A primeira redefinição é grátis; as seguintes custam
`nível × 5` AGC (ledger `talent_respec`). Retorna `{ cost, state }`.

#### Presets 🔒

- `POST /talents/presets` `{ "name" }` — cria (exige espaço livre).
- `PATCH /talents/presets/{id}` `{ "name" }` — renomeia.
- `DELETE /talents/presets/{id}` — exclui (não o ativo).
- `POST /talents/presets/{id}/activate` — troca de build; a primeira troca é livre e
  as seguintes têm recarga de 1 hora (`talent_switch_cooldown_seconds`).

Efeitos no jogo:

- **Plantio:** tempo de crescimento, produção, colheita extra, XP e chance de poupar a
  semente ficam gravados no plantio (`plantings.grow_seconds` e `plantings.modifiers`).
  Trocar de preset não altera plantações em andamento. Sorteios são determinísticos.
- **Mercado:** `sell_price` e `market_fee` valem na hora da venda. `GET /market/offers`
  passa a trazer `sell_bonus_bp` por item e a `fee_basis_points` efetiva.

### Construções (Fase 5)

Construções têm níveis; cada melhoria custa AgroCoin e exige nível de jogador.
Conteúdo em `backend/app/game/buildings.py`.

| Construção | Nível | Custo | Nível do jogador | Efeito |
|---|---:|---:|---:|---|
| Casa da Fazenda | 1 (inicial) | — | 1 | 6 talhões |
| | 2 | 150 | 3 | 8 talhões |
| | 3 | 400 | 8 | 10 talhões |
| | 4 | 900 | 15 | 12 talhões |
| Galinheiro | 1 | 80 | 2 | abriga 3 animais |
| | 2 | 250 | 6 | 6 animais |
| | 3 | 600 | 12 | 10 animais |
| Estábulo | 1 | 200 | 4 | abriga 2 animais (vacas e ovelhas) |
| | 2 | 500 | 9 | 4 animais |
| | 3 | 1100 | 16 | 6 animais |
| Moinho | 1 | 150 | 3 | 1 vaga de produção |
| | 2 | 400 | 8 | 2 vagas, produção −5% de tempo |
| | 3 | 900 | 14 | 3 vagas, −10% |
| Padaria | 1 / 2 / 3 | 250 / 600 / 1300 | 5 / 10 / 16 | 1 / 2 / 3 vagas, −0% / −5% / −10% |
| Queijaria | 1 / 2 / 3 | 300 / 700 / 1500 | 6 / 11 / 17 | 1 / 2 / 3 vagas, −0% / −5% / −10% |
| Poço da Ilha | 1 | 60 | 2 | tempo de crescimento −2% |
| | 2 | 200 | 6 | −4% |
| | 3 | 500 | 12 | −6% |

#### GET `/api/v1/catalog/buildings` (público)

Todas as construções, níveis, custos e efeitos.

#### GET `/api/v1/properties/{property_id}/buildings` 🔒

Estado de cada construção na fazenda: `level`, `max_level`, `current`, `next`,
`can_upgrade` e `blocked_reason` (nível de jogador ou saldo insuficiente), além de
`plot_count`, `player_level` e `balance`.

#### POST `/api/v1/properties/{property_id}/buildings/{building_id}/upgrade` 🔒

Melhora a construção em um nível, debitando o custo (ledger `building_upgrade`).
Aceita `Idempotency-Key` (8–64 caracteres): reenviar a mesma chave não cobra de novo
(`"replayed": true`); a mesma chave em outra operação retorna `409`.
`422` se faltar nível de jogador, saldo ou se já estiver no nível máximo; `404` para
construção desconhecida ou fazenda de outro jogador. O efeito dos talhões vale na hora
(`plots`); bônus como o do Poço valem para plantios **novos** (ficam gravados no plantio).

#### Mudanças em `POST /api/v1/properties`

Cada jogador pode ter **uma** fazenda (`409` na segunda) e ela sempre começa com 6
talhões (`plot_count` maior que 6 retorna `422`). Mais talhões só pela Casa da Fazenda.

### Animais (Fase 5)

Animais só produzem enquanto **alimentados**. Cada porção de ração (uma safra do
inventário) mantém o animal alimentado por 30 minutos; a ração acumulada tem teto de
8 horas, e o estoque de produtos do animal guarda no máximo o equivalente a 8 horas.
Assim a produção offline é determinística e limitada (nada de acumular por dias).
Conteúdo em `backend/app/game/animals.py`.

| Espécie | Abrigo | Preço | Nível | Produto (a cada) | Valor | Ração |
|---|---|---:|---:|---|---:|---|
| Galinha | Galinheiro | 60 | 2 | Ovo (15 min) | 4 | Milho |
| Vaca | Estábulo | 300 | 5 | Leite (20 min) | 9 | Cenoura |
| Ovelha | Estábulo | 220 | 7 | Lã (40 min) | 14 | Milho |

Os produtos (`animal_ovo`, `animal_leite`, `animal_la`) vão para o inventário e são
vendidos no mercado como qualquer produto (com bônus de preço e taxa dos talentos).

#### GET `/api/v1/properties/{property_id}/animals` 🔒

Contabiliza a produção até agora e devolve: `animals` (`stored`, `max_stored`,
`is_fed`, `fed_seconds_left`, `seconds_to_next`), `housings` (`capacity`/`used` por
abrigo) e `species` (preço, nível, `can_buy` e `blocked_reason`), além de `balance` e
`player_level`.

#### POST `/api/v1/properties/{property_id}/animals/buy` 🔒 · `{ "species": "galinha" }`

Compra um animal (ledger `animal_purchase`). Exige nível de jogador, abrigo construído
com vaga e saldo (`422` com o motivo). Aceita `Idempotency-Key` (reenvio não cobra de
novo; `409` se a chave for de outra operação). `404` para espécie desconhecida.

#### POST `/api/v1/properties/{property_id}/animals/{animal_id}/feed` 🔒 · `{ "units": 1 }`
#### POST `/api/v1/properties/{property_id}/animals/feed-all` 🔒 · `{ "units": 4 }`

Consome ração do inventário (`units` de 1 a 64, limitado pelo estoque e pelo teto de
8 h). `units_fed` informa o que foi usado. `422` sem ração ou com os animais já cheios.

#### POST `/api/v1/properties/{property_id}/animals/collect` 🔒

Coleta todos os produtos prontos para o inventário e concede XP (`xp_gained`, com o
bônus de talentos). `422` se não houver nada pronto.

### Fabricação (Fase 5)

Receitas rodam em estações (Moinho, Padaria, Queijaria), que são construções com vagas
de produção. Cada trabalho consome os insumos ao iniciar e entrega o produto após
`duração × lotes`. O término e a quantidade ficam gravados no trabalho com os bônus
vigentes no início (determinístico, funciona offline e não muda se trocar de talentos).
Conteúdo em `backend/app/game/recipes.py`.

| Receita | Estação | Insumos (por lote) | Resultado | Tempo | Nível |
|---|---|---|---|---:|---:|
| Farinha de milho | Moinho | 3 milho | 1 farinha (24 AGC) | 10 min | 3 |
| Pão | Padaria | 2 farinha + 1 ovo | 3 pães (22 AGC) | 15 min | 5 |
| Bolo | Padaria | 2 farinha + 2 ovos + 1 leite | 1 bolo (90 AGC) | 30 min | 9 |
| Queijo | Queijaria | 3 leite | 1 queijo (42 AGC) | 20 min | 6 |
| Manteiga | Queijaria | 2 leite | 1 manteiga (26 AGC) | 10 min | 6 |

Os produtos processados (`processed_*`) vão para o inventário e vendem no mercado.

#### GET `/api/v1/properties/{property_id}/crafting` 🔒

`stations` (nível, `job_slots`, `used_slots`, `time_bonus_bp` e os `jobs` abertos com
`seconds_left` e `ready`) e `recipes` (insumos com `have`, `max_batches`, `can_craft` e
`blocked_reason`).

#### POST `/api/v1/properties/{property_id}/crafting/start` 🔒 · `{ "recipe_id": "farinha", "batches": 3 }`

Inicia um trabalho (1 a 24 lotes; o tempo e os insumos são proporcionais aos lotes).
`422` se faltar estação, nível, vaga ou insumos (nada é consumido nesses casos).
Aceita `Idempotency-Key`: o reenvio não inicia outro trabalho (`replayed: true`).

#### POST `/api/v1/properties/{property_id}/crafting/collect` 🔒

Coleta todos os trabalhos prontos para o inventário e concede XP (`collected`,
`xp_gained`). `422` se nada estiver pronto. Cada trabalho só pode ser coletado uma vez.

## 7. Infra

| Método | Rota | Descrição |
|---|---|---|
| GET | `/` | Nome, links de docs/health/api. |
| GET | `/health` | `{ "status": "ok" }`. |

## 8. Erros

Erros de domínio seguem o formato:

```json
{ "detail": "Este talhão já está ocupado por outro plantio.", "code": "conflict" }
```

| HTTP | `code` | Quando ocorre |
|---:|---|---|
| 401 | `authentication_error` | Token ausente, conta desativada ou credenciais inválidas. |
| 401 | `invalid_token` | Token expirado, malformado ou usuário removido. |
| 403 | `forbidden` | Conta desativada no login. |
| 404 | `not_found` | Fazenda, plantio, cultura ou item inexistente (inclusive de outro jogador). |
| 409 | `conflict` | E-mail/username duplicado ou talhão ocupado. |
| 422 | `game_rule_violation` | Sementes insuficientes, talhão inválido, colheita não pronta. |

Erros de validação do Pydantic/FastAPI usam **422** com `detail` em lista, sem
`code`. O cliente deve tratar os dois formatos.

## 9. Exemplo com `curl`

```bash
BASE=http://localhost:8000/api/v1

curl -X POST "$BASE/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"ana@agro.com.br","username":"ana","password":"colheita2026"}'

TOKEN=$(curl -s -X POST "$BASE/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"login":"ana","password":"colheita2026"}' | jq -r .access_token)

PROPERTY_ID=$(curl -s -X POST "$BASE/properties" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"name":"Fazenda Boa Vista","area_hectares":12.5,"plot_count":6}' | jq -r .id)

curl -X POST "$BASE/properties/$PROPERTY_ID/plantings" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"crop_id":"milho","plot_index":0}'

curl -X POST "$BASE/properties/$PROPERTY_ID/production/sync" \
  -H "Authorization: Bearer $TOKEN"

curl -X POST "$BASE/properties/$PROPERTY_ID/harvest" \
  -H "Authorization: Bearer $TOKEN"
```
