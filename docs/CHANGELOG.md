# Changelog — Agro & Tech

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/).
Versionamento semântico para a API e o cliente.

## [Não lançado]

### Próximo

- Experiência e níveis; primeira construção melhorável.
- Expansão de talhões e novas construções.
- Ampliar E2E Playwright (plantio e colheita).

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
