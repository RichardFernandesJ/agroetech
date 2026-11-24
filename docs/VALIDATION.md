# Validação em Docker e PostgreSQL

Este roteiro valida o jogo na **stack real** (Docker Compose + PostgreSQL 16). Até aqui, o
desenvolvimento rodou com SQLite e a API; Docker e PostgreSQL ainda **não foram executados**
na máquina de desenvolvimento (não há Docker lá). Tudo abaixo foi preparado e testado até onde
foi possível sem eles; o que depende deles está marcado em [§7](#7-o-que-já-foi-validado-e-o-que-falta).

Tempo estimado: 15 a 20 minutos.

## 1. Pré-requisitos

- Docker com Compose v2 (`docker compose version`).
- Python 3.10+ no host (só para o roteiro de fumaça; ele usa apenas a biblioteca padrão).
- Portas livres: 5432 (PostgreSQL), 8000 (API), 5173 (web). Mude em `.env` se necessário.

## 2. Subir a stack

```bash
cp .env.example .env
docker compose up --build
```

O que deve acontecer, em ordem:

1. `db` fica saudável (`pg_isready`).
2. `api` roda `alembic upgrade head` — nos logs, as 10 revisões até `0010_one_property_per_user`.
3. `api` fica saudável (`/health`) e `web` sobe o Vite.

Conferir:

```bash
docker compose ps                 # db, api e web "healthy"/"running"
curl http://localhost:8000/health # {"status":"ok"...}
```

Abra `http://localhost:8000/docs` (Swagger) e `http://localhost:5173` (jogo).

## 3. Roteiro de fumaça (automático)

```bash
python scripts/smoke.py            # contra http://localhost:8000
```

Esperado: **20 verificações ok, 0 falhas**, inclusive:

- uma fazenda por jogador (segunda criação recusada com 409);
- compra idempotente (a mesma chave não cobra duas vezes);
- **dez compras simultâneas com saldo para uma: exatamente uma passa, sem erro 500**;
- extrato (`wallet_ledger`) igual ao saldo.

Se o passo de concorrência falhar no PostgreSQL, **pare e investigue**: é o sinal de que a
trava de linha (`FOR UPDATE`) ou a atualização condicional não está funcionando.

## 4. Suíte completa em PostgreSQL

A mesma suíte (inclui `tests/test_postgres.py`, que em SQLite fica "pulado"):

```bash
docker compose --profile test run --rm tests-pg
```

Esperado: todos os testes passam e **nenhum "skipped"**. O que `test_postgres.py` cobre:

| Teste | O que prova |
|---|---|
| migrações | `alembic upgrade head` gera tabelas, colunas, índices (inclusive os parciais) e restrições iguais aos models; `downgrade base` desfaz tudo |
| compras simultâneas | o saldo nunca fica negativo e o extrato fecha |
| mesma `Idempotency-Key` em paralelo | cobra uma vez só |
| primeiro acesso simultâneo | uma carteira, um progresso, um preset |
| cadastro simultâneo | um 201, os demais 409 |
| criação de fazenda simultânea | uma fazenda por jogador |
| melhorias simultâneas | cobra uma vez |
| fabricação simultânea | nunca passa do número de vagas |
| colheita/coleta simultâneas | pagam uma vez |

Sem Docker, dá para rodar com um PostgreSQL local:

```bash
cd backend
AGRO_TEST_DATABASE_URL=postgresql+asyncpg://agro:agro@localhost:5432/agroetech_test pytest -v
```

O nome do banco **precisa terminar em `_test`** (a suíte apaga e recria as tabelas); a trava
aborta antes de tocar em qualquer outro banco.

## 5. Migrações e backup

```bash
docker compose exec api alembic current          # 0010_one_property_per_user (head)
docker compose exec api alembic history --verbose
docker compose exec api alembic downgrade -1 && docker compose exec api alembic upgrade head

# Backup e restauração (AGENTS.md §14)
docker compose exec db pg_dump -U agro agroetech > backup.sql
docker compose exec -T db psql -U agro -d agroetech < backup.sql
```

A migração `0010` **recusa** rodar se algum jogador já tiver mais de uma fazenda (criadas antes
da regra) e diz o que fazer; ela nunca apaga dados.

## 6. Checklist manual no navegador (`http://localhost:5173`)

Marque cada item; "esperado" é o que deve aparecer.

**Ciclo do MVP**

- [ ] Criar conta, criar o perfil → o HUD mostra a fazenda, 100 AGC e "Nv 1".
- [ ] Clicar num talhão vazio → seletor de sementes → plantar → toast "Plantou…" e +2 XP.
- [ ] Passar o mouse no talhão → dica com o tempo restante.
- [ ] Esperar (milho = 5 min) ou usar a produção offline (fechar a aba, voltar depois) → selo dourado pulsante → clicar colhe, mostra recompensa flutuante e XP.
- [ ] **🏪 Mercado** → vender a safra (taxa de 5% informada) e comprar sementes → saldo muda; aba **Extrato** lista as operações.
- [ ] **Persistência:** `docker compose restart api`, recarregar a página → continua logado, mesma fazenda, mesmo saldo.

**Sistemas novos**

- [ ] **🏗️ Construções** → melhorar o Poço (nível de jogador 2) → o próximo plantio fica 2% mais rápido; melhorar a Casa abre 2 talhões novos no mapa.
- [ ] **🐔 Animais** (ou clicar no Curral) → construir Galinheiro, comprar uma galinha, alimentar com milho → "Alimentada por…" → depois de alguns minutos há ovos → **Coletar tudo**.
- [ ] **🏭 Fabricação** (ou clicar na Oficina) → construir o Moinho → produzir farinha → barra de progresso → **Coletar prontos**.
- [ ] **🌳 Talentos** → o mapa mostra 4 ramos ativos; adquirir um talento, criar um segundo preset, trocar de preset (recarga de 1 h), redefinir (1ª grátis).
- [ ] Clicar num botão de painel que fica sobre um talhão **não** abre o seletor de plantio.

**Resiliência**

- [ ] Duas abas logadas na mesma conta: comprar a mesma coisa nas duas ao mesmo tempo nunca deixa o saldo negativo.
- [ ] Derrubar a API (`docker compose stop api`): o jogo mostra erro amigável e volta sozinho com `docker compose start api`.

## 7. O que já foi validado e o que falta

**Validado sem Docker** (SQLite e API local):

- 179 testes automatizados (API, regras puras, migrações, integridade) e 6 E2E com Playwright; mais
  10 testes exclusivos de PostgreSQL que ficam "pulados" em SQLite.
- Paridade entre migrações e models (colunas, índices, únicos e checks).
- Roteiro de fumaça 20/20 contra a API local, **inclusive a disputa concorrente** (que revelou o
  duplo gasto em SQLite e levou à atualização condicional, ver ADR-020).
- Verificação estática do `docker-compose.yml`, dos Dockerfiles, do nginx e dos `.env.example`
  (`tests/test_deploy_config.py`).

**Ainda não executado (precisa de Docker/PostgreSQL):**

- O build das imagens e a subida real da stack.
- A suíte em PostgreSQL (`tests/test_postgres.py` e o restante contra PG).
- As travas `FOR UPDATE` sob concorrência real e o desempenho das consultas.
- O pipeline de CI (`.github/workflows/ci.yml`) — roda sozinho no primeiro `git push` para um
  repositório do GitHub, com PostgreSQL de verdade.

## 8. Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `api` reinicia em loop | `alembic upgrade head` falhou: veja `docker compose logs api` (ex.: migração `0010` com jogadores duplicados) |
| Porta em uso | ajuste `API_PORT`, `WEB_PORT` ou `POSTGRES_PORT` em `.env` |
| `tests-pg` aborta com "precisa terminar em _test" | `AGRO_TEST_DATABASE_URL` aponta para o banco de desenvolvimento |
| Navegador sem acentos no smoke | use `PYTHONIOENCODING=utf-8` (o script já reconfigura a saída) |
| Quer recomeçar do zero | `docker compose down -v` (apaga o volume `pgdata`) |
