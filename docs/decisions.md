# Decisões técnicas (ADRs resumidos)

Formato leve de Architecture Decision Record: contexto, decisão e
consequências. O objetivo é registrar o porquê, não apenas o como.

## ADR-001 — Monorepo com `backend/` e `frontend/`

**Contexto:** API e jogo evoluem juntos e compartilham contratos.

**Decisão:** um único repositório, com pastas independentes e builds separados.
Não há workspace npm nem pacote compartilhado nesta etapa.

**Consequências:** onboarding simples e commits coordenados; contratos
precisam ser mantidos manualmente entre Pydantic e TypeScript até existir
geração automática de clientes.

---

## ADR-002 — FastAPI + SQLAlchemy assíncrono + PostgreSQL

**Contexto:** o jogo precisa de I/O concorrente e consistência relacional.

**Decisão:** FastAPI, SQLAlchemy 2 async, `asyncpg` em produção e PostgreSQL 16.

**Consequências:** boa performance para I/O e tipagem; exige atenção a
transações e ao event loop. SQLite em memória é usado apenas nos testes.

---

## ADR-003 — Backend em camadas

**Contexto:** regras de jogo tendem a crescer e se misturar com HTTP/SQL.

**Decisão:** separar `api`, `services`, `repositories`, `models`, `schemas` e
`game`. Dependências apontam para dentro: `api → services → repositories →
models`. `services` pode usar `game`; `game` não conhece banco nem HTTP.

**Consequências:** testes unitários baratos e troca de detalhes de persistência
sem reescrever regras. Custo: mais arquivos e mapeamento explícito entre
camadas.

---

## ADR-004 — Produção offline preguiçosa, sem worker

**Contexto:** culturas continuam crescendo com o jogador offline. Um cron/worker
adicionaria infraestrutura e estados intermediários.

**Decisão:** simular o tempo sob demanda em `ProductionService.sync_property`,
com janela máxima e teto de ciclos armazenados por plantio.

**Consequências:** determinístico, sem fila, resistente a reinícios e fácil de
testar. O "relógio" avança apenas quando a fazenda é acessada; eventos em tempo
real exigirão WebSocket/SSE ou worker no futuro.

---

## ADR-005 — JWT HS256 + PBKDF2 na fundação

**Contexto:** autenticação simples para o cliente Phaser, sem dependências
nativas problemáticas.

**Decisão:** JWT de acesso com `sub = user.id`, expiração configurável e senha
com PBKDF2-HMAC-SHA256 (600k iterações, salt aleatório) da biblioteca padrão.

**Consequências:** funciona em qualquer ambiente Python. Para produção,
recomenda-se Argon2/bcrypt, refresh tokens, revogação e rate limiting. A troca
de hash fica isolada em `app/core/security.py`.

---

## ADR-006 — Phaser 3 + TypeScript

**Contexto:** o projeto define Phaser 3 como engine e TypeScript como linguagem.

**Decisão:** Phaser `3.90.x` com Vite, cenas em classes e tipos estritos.
Phaser 4 não é adotado nesta etapa.

**Consequências:** ecossistema e documentação maduros. O bundle é grande
(~1,2 MB), aceitável para um jogo; code splitting e carregamento de assets
entram quando houver conteúdo real.

---

## ADR-007 — Vite como dev server e bundler

**Contexto:** necessidade de HMR rápido, TypeScript nativo e proxy para a API.

**Decisão:** Vite 8, alias `@/`, proxy de `/api` e `/health` para o FastAPI e
build estático em `dist/`.

**Consequências:** feedback rápido e configuração enxuta. A build é servida por
nginx em produção.

---

## ADR-008 — URLs relativas e proxy (sem CORS no caminho principal)

**Contexto:** o cliente precisa falar com a API em dev e produção sem reconfigurar
a build.

**Decisão:** o browser usa `/api/v1` e `/health`. Vite faz proxy em dev; nginx
faz proxy em produção. O CORS do FastAPI permanece apenas como fallback para
ferramentas externas.

**Consequências:** mesma build em qualquer ambiente e menos superfície de CORS.
O nginx precisa conhecer o host `api` na rede do Compose.

---

## ADR-009 — Docker Compose para desenvolvimento e imagem multi-stage

**Contexto:** onboarding e paridade entre máquinas.

**Decisão:** Compose com `db`, `api`, `web` e profile `test`; frontend com
estágios `dev`, `build` e `prod` (nginx). Credenciais e portas vêm do `.env`
da raiz.

**Consequências:** `docker compose up --build` sobe o ambiente completo. Em
produção, o alvo `prod` serve o bundle e faz proxy para a API; orquestração
real (Kubernetes, etc.) fica fora desta etapa.

---

## ADR-010 — Catálogo de culturas em código

**Contexto:** o balanceamento do jogo é conteúdo versionado e precisa ser
testável sem banco.

**Decisão:** `CropDefinition` e `ITEM_CATALOG` em `app/game/catalog.py`.

**Consequências:** mudanças de balanceamento passam por code review e testes.
Se o catálogo precisar ser editado por painel, vira tabela; a interface de
consulta dos services pode ser mantida.

---

## ADR-011 — Alembic como fonte do schema

**Contexto:** agilidade no início versus segurança de schema. `create_all` é
rápido, mas não versiona alterações e não permite rollback controlado.

**Decisão:** o schema é criado e evoluído por revisões do Alembic. O Compose
executa `alembic upgrade head` antes do Uvicorn e
`AGRO_AUTO_CREATE_TABLES` tem padrão `false`. `create_all` permanece apenas nos
testes de API, que usam SQLite em memória.

**Consequências:** todo deploy parte de um schema conhecido e reproduzível;
alterações de model exigem uma revisão. Um teste aplica a revisão inicial em
SQLite e compara o resultado com o metadata, evitando divergência silenciosa.
Bancos antigos criados por `create_all` precisam de `alembic stamp
0001_foundation` uma única vez.

---

## ADR-012 — Testes de API com SQLite em memória

**Contexto:** a suíte precisa rodar sem Docker e sem PostgreSQL.

**Decisão:** engine SQLite `aiosqlite` com `StaticPool`, `create_all` por teste
e override da dependência `get_db`. Testes de regras puras não tocam no banco.
A migração é validada à parte, em arquivo SQLite temporário.

**Consequências:** suíte rápida e isolada. Recursos específicos de PostgreSQL
(ex.: `FOR UPDATE`) não são exercitados nos testes; revisões de queries devem
considerar isso. O teste de migração cobre o que o `create_all` não cobre:
upgrade, downgrade e paridade com os models.

---

## ADR-013 — Fonte da verdade no servidor

**Contexto:** jogos no browser são manipuláveis pelo cliente.

**Decisão:** tempo, crescimento, inventário, sementes e recompensas são
calculados e validados no backend. O Phaser apenas apresenta estado e envia
intenções.

**Consequências:** reduz cheating e mantém consistência entre dispositivos.
O cliente pode prever animações, mas nunca decide o resultado.

---

## ADR-014 — Jogabilidade God-View em Ilha e Interação Point & Click sem Avatar Físico

**Contexto:** O modelo inicial previa um RPG top-down tradicional onde o jogador
controlava um boneco andando pelo mapa com teclado (WASD) e colisões físicas,
tendo que caminhar até cada talhão para interagir por proximidade. Esse modelo gerava
atrito para um jogo de gestão rural / farming simulator de navegador, tornando tarefas
repetitivas lentas e cansativas.

**Decisão:** Eliminar o personagem controlável físico do mapa e migrar para uma
experiência de simulação panorâmica ("God-view") em uma ilha cercada de água:
1. **Câmera Pan & Zoom no Mouse:** O jogador navega arrastando a tela livremente (pan)
   e aplicando zoom dinâmico na roda do mouse (scroll wheel de 0.45x a 2.2x com ponto
   focal no cursor), além de controles acessíveis no HUD.
2. **Cenário em Ilha:** O mapa foi reestruturado para ser uma ilha orgânica com mar
   profundo, praias com conchas, caminhos de terra batida e platô fértil no centro.
3. **Agricultura 100% no Clique:** Clicar em talhões vazios abre seletor com as
   sementes do inventário para plantio imediato com 1 clique; talhões maduros exibem
   distintivo dourado pulsante e são colhidos com um único clique (com recompensas
   flutuantes) ou pelo botão "Colher Tudo" no HUD.
4. **Desacoplamento do Backend:** As rotas do backend já operavam baseadas em
   `property_id` e `plot_index`, dispensando alterações de regras de negócio.

**Consequências:** Jogabilidade muito mais fluida, relaxante e ágil, perfeitamente
alinhada a clássicos de gerenciamento como *Islanders*, *Hay Day* e *Rusty's Retirement*.
Elimina bugs de travamento em colisão física de avatar e simplifica a renderização.

## ADR-015 — Carteira por jogador, ledger imutável e idempotência por cabeçalho

**Contexto:** A Fase 4 introduz o AgroCoin (AGC). O AGENTS.md exige validação no
servidor, transações atômicas, histórico, taxas e prevenção de duplicação.

**Decisão:**
1. Uma carteira por **usuário** (não por propriedade), pensando no multiplayer futuro.
2. Valores inteiros (`BIGINT`); nada de centavos ou ponto flutuante.
3. Todo movimento gera uma linha imutável em `wallet_ledger` com `balance_after`;
   o saldo é conciliável com a soma do ledger.
4. A operação (saldo + inventário + ledger) roda na transação da requisição, com
   `SELECT ... FOR UPDATE` na carteira, e `CHECK balance >= 0` como rede de segurança.
5. Idempotência por `Idempotency-Key` com unicidade `(wallet_id, key)`; replays
   devolvem o resultado original e chaves reutilizadas com outro corpo dão `409`.
6. Preços vivem no catálogo do servidor; a taxa de 5% é sumidouro de moeda.

**Consequências:** Base pronta para mercado global e trocas. A venda ao entreposto
NPC ainda emite moeda limitada pela produção das fazendas; o balanceamento deve ser
revisto com dados reais antes do multiplayer.
