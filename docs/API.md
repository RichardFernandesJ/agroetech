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
