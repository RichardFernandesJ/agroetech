# Changelog — Agro & Tech

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento semântico para a API e o cliente.

## [Não lançado]

### Próximo

- Experiência e níveis; primeira construção melhorável.
- Expansão de talhões e novas construções.
- Ampliar E2E Playwright (plantio e colheita).

## [0.10.0] — 2026-11-23

### Adicionado

- **Ramos Pecuária e Indústria da árvore de talentos:** 26 talentos novos (55 no total), com especialistas por espécie e por estação, masters exclusivos e lendários, e os híbridos *Laticínios* e *Feira de Produtos*.
- Estatísticas novas no motor de modificadores: `animal_yield`, `animal_speed`, `feed_efficiency` (escopo por espécie) e `production_saving` (lote grátis); `production_time`/`production_yield` passam a valer por estação.
- Bônus de preço com escopo por produto (ovo, leite, lã, farinha, pão, bolo, queijo, manteiga) via `sell_scope_for_item`.
- Animais gravam velocidade e rendimento (`speed_bp`, `yield_bp`, migração `0009`) quando alimentados com fome: sem efeito retroativo ao trocar de build.
- Painéis de animais e fabricação mostram os bônus ativos.
- Simulador de paridade por domínio (lavoura, animais, fabricação) e 11 testes novos (165 no total).

### Alterado

- **Rebalanceamento da economia** para que bônus percentuais não distorçam os domínios de margem fina: ração rende 35 min por porção; ovo vale 5 AGC; farinha 30, pão 40, bolo 150, queijo 52 e manteiga 34 AGC.
- Validação do catálogo de talentos reconhece escopos de culturas, espécies, produtos e estações.

## [0.9.0] — 2026-11-23

### Adicionado

- **Fabricação (Fase 5):** receitas e `ProductionJobs`. Tabela `production_jobs` (migração `0008`), catálogo em `game/recipes.py` e `CraftingService`.
- Estações como construções: **Moinho**, **Padaria** e **Queijaria**, com vagas de produção por nível (`BuildingLevel.job_slots`) e aceleração nos níveis 2 e 3.
- 5 receitas (farinha, pão, bolo, queijo, manteiga) e 5 itens processados, vendáveis no mercado.
- Endpoints `GET /properties/{id}/crafting`, `POST .../crafting/start` (idempotente) e `POST .../crafting/collect`.
- Estatísticas `production_time` (escopo por estação) e `production_yield` no motor de modificadores, prontas para o ramo Indústria dos talentos.
- Painel **🏭 Fabricação** com contagem regressiva, e a **Oficina** clicável no mapa. `PressGuard` compartilhado evita perder cliques em atualizações automáticas (usado também no painel de animais).
- 16 testes novos (154 no total), incluindo atomicidade (insumo faltando não consome nada), coleta única e idempotência; E2E completo de fabricação.

### Corrigido

- O utilitário do E2E entregava itens à primeira fazenda do banco (e não à do teste em andamento), causando falhas intermitentes. Agora usa a fazenda e o jogador mais recentes.

## [0.8.0] — 2026-11-23

### Adicionado

- **Animais (Fase 5):** galinha, vaca e ovelha. Tabela `animals` (migração `0007_animals`), catálogo em `game/animals.py` e regras puras de alimentação e produção (`advance` e `feed`), testadas sem banco.
- Abrigos como construções: **Galinheiro** e **Estábulo** (capacidade por nível); `BuildingLevel.capacity`.
- Endpoints `GET /properties/{id}/animals`, `POST .../animals/buy` (idempotente), `.../{animal}/feed`, `.../feed-all` e `.../collect`.
- Produtos animais (`animal_ovo`, `animal_leite`, `animal_la`) no catálogo de itens, vendáveis no mercado.
- Painel **🐔 Animais** e **Curral** no mapa (clicável), com alimentação por ×1/×4/Máx, coleta e compra.
- 24 testes novos (138 no total), incluindo equivalência entre muitas sincronizações pequenas e uma grande, e um teste de balanceamento da economia animal. E2E completo: construir abrigo, comprar, alimentar, avançar o relógio e coletar.

### Alterado

- `tests/helpers.boost_player` (nível + AGC para os testes) compartilhado por vários testes.
- E2E ganhou o utilitário `e2e/support/e2e_db.py` (dar itens e avançar o relógio no SQLite descartável).

## [0.7.1] — 2026-11-23

### Alterado

- **`FarmScene` dividida:** de 735 para 107 linhas. Responsabilidades em `game/scenes/farm/` (`CameraController`, `PlotRenderer`, `FarmController`, `FarmPanels`, `world-interactions`, `FarmState`), sem mudança de comportamento.
- `Hud.setMenu()` permite definir o menu depois da criação.

### Adicionado

- E2E de plantio por clique direto no talhão do mapa (`e2e/plant-flow.spec.ts`).

## [0.7.0] — 2026-11-23

### Adicionado

- **Fase 5 — Construções melhoráveis:** Casa da Fazenda (6 a 12 talhões) e Poço da Ilha (−2/−4/−6% no tempo de crescimento). Tabela `buildings` (migração `0006_buildings`).
- Endpoints `GET /catalog/buildings`, `GET /properties/{id}/buildings` e `POST /properties/{id}/buildings/{building}/upgrade` (idempotente, atômico, paga em AGC, exige nível).
- `ModifierService`: reúne talentos e construções no mesmo `ModifierSet`; plantio e mercado passaram a usá-lo.
- Painel **🏗️ Construções** (menu do HUD, clique na Casa ou no Poço), talhões novos no mapa (até 12) com cerca dinâmica.
- 15 testes de construções (114 no total) e E2E de construções.

### Corrigido

- **Brecha:** `POST /properties` permitia criar várias fazendas (sementes grátis a cada uma) e escolher o número de talhões. Agora é uma fazenda por jogador, com 6 talhões iniciais.
- **Clique vazando para o mapa:** clicar num botão de painel que estivesse sobre um talhão abria o seletor de plantio. A cena ignora eventos que não nasceram no canvas ou com painel aberto.
- Painéis mais altos que a janela eram cortados no topo; agora rolam a partir do cabeçalho.
- Dica do HUD movida para baixo (colidia com o menu); palmeira que cobria um talhão novo foi realocada.
- Teto de redução do tempo de crescimento passou de −20% para −25% para comportar talentos + Poço.

## [0.6.0] — 2026-11-23

### Adicionado

- **Árvore de Talentos (interface):** mapa SVG com pan, zoom (roda, pinça e botões), nós conectados por linhas, estados adquirido/disponível/bloqueado, tooltip, painel lateral com benefícios e requisitos pendentes, pontos disponíveis, progresso por ramo e animação ao adquirir.
- Presets na parte inferior: ativar, criar, renomear, excluir, recarga de troca, espaços por nível e redefinição com custo.
- Menu do HUD declarativo (`HudMenuItem[]`) com Mercado e Talentos; saldo continua abrindo o mercado.
- `ModalManager`: um único painel aberto por vez, ciclo de vida centralizado.
- E2E de talentos (`e2e/talents.spec.ts`).

### Alterado

- `FarmScene` usa o `ModalManager` (menos código repetido de abrir/fechar painéis).
- Layout do mapa de talentos com mais espaço entre camadas e nós.
- Estilos `.btn` e `.btn-primary` passaram a existir (os painéis antigos os usavam sem estilo).

## [0.5.0] — 2026-11-23

### Adicionado

- **Motor de modificadores** (`game/modifiers.py`): soma de bônus por fonte e escopo (cultura), tetos por estatística, sorteios determinísticos.
- **Talentos no servidor:** catálogo de 27 talentos (Agricultura, Comércio e um híbrido), pontos por nível, requisitos, talento mestre exclusivo, presets (até 5), recarga de troca e redefinição (primeira grátis; depois `nível × 5` AGC). Migração `0005_talents`.
- Endpoints `GET /catalog/talents`, `GET /talents`, `POST /talents/allocate`, `POST /talents/reset` e `/talents/presets`.
- Efeitos reais: tempo de crescimento, produção, colheita extra, XP e poupança de sementes (gravados no plantio) e preço de venda e taxa (no mercado).
- `GET /market/offers` traz `sell_bonus_bp` e a taxa efetiva; o modal do mercado mostra o bônus.
- Simulador de paridade entre builds e 32 testes novos.

## [0.4.0] — 2026-11-23

### Adicionado

- **XP e níveis:** tabela `player_progress` (migração `0004_progress`), curva de nível 1–50, `GET /progress`.
- XP ao plantar (2) e ao colher (`harvest_xp` por ciclo); `xp_gained` nas respostas de colheita.
- Barra de nível e XP no HUD e aviso de subida de nível.
- `docs/TALENTS.md`: desenho aprovado de talentos, presets, guildas e disputas; Fase 4.5 no ROADMAP.

## [0.3.0] — 2026-11-23

### Adicionado

- **Fase 4 — Economia básica:** carteira AgroCoin (`wallets`) e livro-razão (`wallet_ledger`), migração `0003_wallet`.
- Endpoints `GET /wallet`, `GET /wallet/ledger`, `GET /market/offers`, `POST /properties/{id}/market/buy|sell`.
- Idempotência via cabeçalho `Idempotency-Key`; taxa de 5% nas vendas; crédito inicial único de 100 AGC.
- Preços `seed_price` e `sell_price` no catálogo de culturas.
- Mercado no jogo (Comprar / Vender / Extrato) operado só com cliques e saldo clicável no HUD.
- 14 testes de economia; o E2E cobre compra e extrato.

### Corrigido

- O armazém do mercado filtrava a categoria `crop`, mas o backend usa `product`; as safras nunca apareciam.

## [0.2.1] — 2026-11-23

### Alterado

- `AGENTS.md`: Fase 2 e MVP alinhados ao modelo God-view sem avatar; `Characters` definido como perfil do jogador; adicionada seção de convenções operacionais.
- Playwright adicionado (`frontend/e2e`, `npm run test:e2e`): fluxo cadastro → perfil → HUD → sessão persistente, com API em SQLite e Vite, sem Docker.
- `AGENTS.md.txt` removido (duplicado de `AGENTS.md`).
- `docs/ROADMAP.md`: removida duplicação da Fase 4, MVP e próxima entrega atualizados.

## [0.2.0] — 2026-11-23

### Adicionado

- **Cenário em Ilha:** Mundo redesenhado como uma ilha cercada por mar profundo (`tile-ocean`), águas rasas turquesa (`tile-shallow-water`), praias de areia dourada com conchas (`tile-sand`, `tile-sand-decor`), píer de madeira e barco de pesca.
- **Câmera Pan & Zoom no Mouse:** Navegação com arrasto de tela (pan) e zoom in/out suave pela roda do mouse (0.45x a 2.2x) com ponto focal inteligente sob o cursor do mouse.
- **Controles no HUD:** Botões dedicados `[+]`, `[-]` e `[⌂ Centralizar na Ilha]` para desktop e dispositivos móveis.
- **Agricultura Point & Click:**
  - `PlantingModal`: Seletor de sementes disponíveis no inventário ao clicar em talhões vazios para plantio com 1 clique.
  - Renderização dos estágios das plantas nos talhões: brotos viçosos e plantas maduras coloridas para cada cultura do catálogo.
  - Distintivo pulsante de colheita pronta flutuando sobre talhões maduros.
  - Colheita por clique direto com animação de recompensa flutuante (`+X safra`).
  - Botão de colheita rápida no HUD (`🌾 Colher Tudo (X)`).
- **Modais de Estruturas:**
  - `HouseModal`: Painel de métricas da ilha, talhões, área e logout.
  - `MarketModal`: Painel de armazém com visualização completa de sementes e safras.
- Sincronização periódica em background a cada 4 segundos com a API.
- Documento `AGENTS.md` e ADR-014 documentando a transição de design para o modelo God-view de ilha.

### Alterado

- Removido avatar físico controlável, controles WASD de caminhada e física de colisão de corpo rígido.
- `propertyService` expandido com chamadas para `getPlantings`, `plant`, `harvest`, `harvestAll` e `getInventory`.
- `README.md`, `docs/GDD.md`, `docs/architecture.md`, `docs/ROADMAP.md` e `AGENTS.md` atualizados com o novo formato.

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
