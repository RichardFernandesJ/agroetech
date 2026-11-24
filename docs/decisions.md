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

## ADR-016 — Construções como catálogo com níveis e bônus pelo motor de modificadores

**Contexto:** A Fase 5 começa pelas construções melhoráveis (último item do MVP). O
AGENTS.md pede expansão de terrenos, melhorias e evitar regras espalhadas.

**Decisão:**
1. Construções são conteúdo em código (`game/buildings.py`), com níveis, custo em AGC,
   nível de jogador mínimo e efeitos. O banco guarda só o nível por fazenda (`buildings`).
2. Efeitos de bônus são `Effect` do motor de modificadores; o `ModifierService` soma
   talentos e construções. Novas fontes (guilda, território) entram ali.
3. Talhões não são um modificador: a melhoria da Casa grava `plot_count` na fazenda.
4. A melhoria usa a carteira (travada), é idempotente e atômica, no mesmo padrão do mercado.
5. Brecha corrigida: uma fazenda por jogador, 6 talhões iniciais fixos.
6. No cliente, eventos do mouse só valem no mundo se nascerem no canvas e sem painel aberto.

**Consequências:** Estruturas novas (celeiro, galinheiro, estábulo) viram entradas do
catálogo + um card no painel. A expansão visual de talhões segue o layout do mapa
(colunas a leste); novas estruturas físicas precisarão de posição própria no mapa.

## ADR-017 — Produção animal por tempo alimentado, com tetos

**Contexto:** A Fase 5 exige animais, alimentação e produção offline (AGENTS.md §6 e §8),
sem processo por jogador, determinística e com limite de capacidade.

**Decisão:**
1. O estado do animal é `fed_until`, `progress_seconds`, `last_sync_at` e `stored`. A
   produção é uma função pura (`advance`) do tempo alimentado entre duas sincronizações;
   muitas sincronizações pequenas dão o mesmo resultado que uma grande (testado).
2. Tetos: ração acumulada (8 h) e produtos guardados (8 h de produção). Nada de acumular
   por dias; o excedente é perdido.
3. A ração são safras do inventário, o que liga plantio, animais e mercado em uma cadeia
   e faz a economia consumir o que a lavoura produz.
4. Abrigos são construções do catálogo com `capacity`; o estábulo é compartilhado por
   vacas e ovelhas. A compra reutiliza a carteira travada e a idempotência do mercado.
5. Sem bônus de talentos próprios ainda: o ramo Pecuária virá depois, com estatísticas novas
   no motor de modificadores (o XP da coleta já usa `xp_gain`).

**Consequências:** Novas espécies são linhas no catálogo. Fabricação (Fase 5) poderá usar
os produtos animais como matéria-prima. Modificar o tempo de produção por talentos exigirá
decidir se vale no momento da alimentação (como o plantio) para evitar efeito retroativo.

## ADR-018 — Fabricação por trabalhos com resultado fixado ao iniciar

**Contexto:** A Fase 5 pede receitas, estações e `ProductionJobs`, com produção offline
determinística e proteção contra duplicação.

**Decisão:**
1. Cada trabalho grava no início `finish_at` e `output_quantity`, já com os bônus
   vigentes. Assim trocar de talentos depois não altera o que está em andamento (mesma
   lição do plantio e o contrário do que o animal permite hoje).
2. Estações são construções do catálogo; as vagas (`job_slots`) e a velocidade vêm do
   nível. O escopo do efeito de tempo é o id da estação, reaproveitando o `scope` do
   motor de modificadores (antes só de culturas).
3. Um trabalho ocupa a vaga até ser coletado, o que evita acumular trabalhos prontos sem
   limite. Coletar é atômico e marca `collected_at` (nunca coleta duas vezes).
4. Os insumos são consumidos ao iniciar na mesma transação; se faltar um, nada é gasto.
   O início aceita `Idempotency-Key` com unicidade `(property_id, request_key)`.
5. A fazenda é travada (`FOR UPDATE` no PostgreSQL) em início e coleta para que o número
   de vagas não seja ultrapassado por requisições concorrentes.
6. Os itens processados entram na tabela de preços do entreposto; a faixa de ganho (1,15×
   a 2×) é validada por teste.

**Consequências:** O ramo Indústria dos talentos só precisa declarar efeitos em
`production_time`/`production_yield`. O ganho de valor das receitas é uma nova fonte de
moeda (limitada por insumos, vagas e tempo) a rever com dados reais antes do multiplayer.

## ADR-019 — Bônus de animais gravados ao alimentar e paridade por domínio

**Contexto:** Com Pecuária e Indústria, os talentos passam a afetar a produção contínua
dos animais. O ADR-017 deixou em aberto como evitar efeito retroativo ao trocar de build.

**Decisão:**
1. O animal grava `speed_bp` e `yield_bp` quando é alimentado **estando com fome** (começo de
   uma rodada de produção) e os mantém até a ração acabar. Alimentar de novo com ração
   sobrando não muda nada; a eficiência da ração vale no ato de alimentar.
2. O estoque do animal acompanha a velocidade (8 h de produção), para o bônus de tempo não
   desperdiçar produtos. O rendimento aplica-se na coleta, com sorteio determinístico.
3. Na fabricação, o lote grátis (`production_saving`) devolve os insumos depois de consumi-los,
   evitando que alguém "ensaie" lotes sem ter os insumos.
4. Paridade é medida por domínio: o simulador compara cada especialista com o melhor
   "intruso" no mesmo domínio. Domínios de margem fina amplificam bônus percentuais; por
   isso as margens dos produtos foram elevadas em vez de reduzir os talentos a quase nada.

**Consequências:** Novos ramos (Exploração, Estratégia) só precisam declarar efeitos e, se
tiverem produção contínua, seguir o mesmo padrão de gravar o bônus no início. O simulador
precisa ganhar um domínio novo a cada mecânica econômica nova.

## ADR-020 — Concorrência: trava de linha e atualização condicional

**Contexto:** O desenvolvimento rodou em SQLite, que não tem `SELECT ... FOR UPDATE`. Ao disparar
dez compras simultâneas contra a API, duas passaram com saldo para uma e o extrato divergiu do
saldo (duplo gasto). Em produção o PostgreSQL trava a linha, mas depender só disso é frágil:
um índice faltando ou uma consulta fora da trava reabre a brecha.

**Decisão:**
1. Duas linhas de defesa independentes: trava de linha (`FOR UPDATE`) no PostgreSQL **e**
   atualização condicional no SQL (`WHERE balance = :lido`, `WHERE quantity >= :n`) para saldo e
   estoque. Quem perde a corrida recebe 409/422 e nada é gravado.
2. Violação de unicidade por corrida (cadastro, fazenda, primeiro acesso) é tratada como `409`,
   nunca como `500`; criações "se não existir" usam savepoint.
3. Regras de unicidade do domínio (uma fazenda por jogador) vivem também no banco.
4. A mesma suíte roda em PostgreSQL (`AGRO_TEST_DATABASE_URL`) e há testes só de PostgreSQL com
   requisições realmente concorrentes. O CI executa ambos.

**Consequências:** Um cliente pode receber 409 "tente novamente" em disputas reais; a interface
já trata erros de API com mensagem amigável. Novos recursos que mexem em dinheiro ou itens
devem usar `WalletService.apply` e `InventoryService.consume/add` (já atômicos) e ganhar um
caso de concorrência em `tests/test_postgres.py`.

## ADR-021 — Mercado entre jogadores: custódia, faixa de preço e taxa que não se evita

**Contexto:** A Fase 6 abre a economia entre jogadores. O AGENTS.md pede mercado global, taxas,
controle de inflação, histórico comercial, transações atômicas e proteção contra duplicação.

**Decisão:**
1. **Custódia (escrow):** os itens saem do inventário ao anunciar (débito atômico) e voltam ao
   vendedor se o anúncio for cancelado ou vencer. Ninguém vende o que não tem nem vende duas vezes.
2. **Compra atômica** numa única transação: debita o comprador, credita o vendedor (bruto − taxa),
   entrega os itens e grava a transação. As duas carteiras são travadas em ordem fixa de usuário
   (compras cruzadas A↔B não geram deadlock) e o estoque do anúncio só diminui se ainda houver
   (`WHERE quantity_remaining >= :n`).
3. **Faixa de preço** (50% a 300% do valor do NPC): sem isso, "vender por 1 AGC" a uma conta
   parceira transfere itens de graça e preços sem teto inflacionam a economia.
4. **Taxa do vendedor arredondada para cima, mínimo de 1 AGC por compra:** arredondar para baixo
   (como no NPC) deixaria compras abaixo de 20 AGC sem taxa, e fatiar uma venda grande em compras
   pequenas fugiria dela. A taxa sai da economia (sumidouro).
5. **Expiração sob demanda:** sem processo em segundo plano (AGENTS.md §8), a devolução dos
   anúncios vencidos acontece quando alguém navega pela praça ou o dono abre os próprios anúncios.
   Um worker periódico pode substituir isso depois sem mudar o contrato.
6. **Nível 3, 20 anúncios ativos e 48 h:** proteção a contas novas e contra spam de anúncios; a
   criação de anúncios é serializada por fazenda para o limite não ser furado em concorrência.

**Consequências:** O padrão (custódia + CAS + ordem de travas) serve às trocas diretas e ao cofre de
guilda. Fica em aberto: limites diários de volume por conta e detecção de contas parceiras.
