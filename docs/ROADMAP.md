# Roadmap — Agro & Tech

Documento de progresso. A ordem segue a seção 12 do `AGENTS.md`: cada fase só
avança quando a anterior está executável e testada. “Concluído” significa
implementado **e** verificado; “parcial” significa que existe base funcional,
mas falta escopo da fase.

Última atualização: 2026-11-23.

## Visão geral

| Fase | Tema | Status |
|---|---|---|
| 1 | Fundação | ✅ Concluída |
| 2 | Ilha e Câmera Livre (God-View) | ✅ Concluída |
| 3 | Agricultura Point & Click | ✅ Concluída |
| 4 | Economia básica (AgroCoin & Mercado) | 🟡 Em andamento (núcleo pronto) |
| 4.5 | Progressão e Talentos (XP, árvore, presets) | 🟡 Em andamento (fatias 1 a 3 prontas) |
| 5 | Produção (animais, construções, fabricação) | 🟡 Em andamento (construções prontas) |
| 6 | Multiplayer econômico | ⬜ Não iniciada |
| 7 | Expansão (cidades, regiões, profissões) | ⬜ Não iniciada |
| 8 | Lançamento | ⬜ Não iniciada |

## Fase 1 — Fundação ✅

| Item | Evidência |
|---|---|
| Repositório Git | `git init` + commit inicial; `.gitignore` para Python, Node, env e bancos locais. |
| Docker | `docker-compose.yml` com `db`, `api`, `web` e profile `test`; Dockerfiles separados. |
| FastAPI | `backend/app/main.py`, rotas versionadas em `/api/v1`, OpenAPI em `/docs`. |
| PostgreSQL | SQLAlchemy 2 async + `asyncpg`; Compose com `postgres:16-alpine` e healthcheck. |
| Phaser | Phaser 3.90 + TypeScript + Vite; boot, health check e cena responsiva. |
| Autenticação | Cadastro, login por e-mail/username, JWT HS256 e `/auth/me`. |
| Documentação | `README.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/GDD.md`, `docs/API.md`, `docs/DATABASE.md`, `docs/ROADMAP.md`, `docs/CHANGELOG.md`. |
| Migrações | Alembic configurado, revisão `0001_foundation` e teste de paridade schema/models. |

## Fase 2 — Ilha e Câmera Livre (God-View) ✅

Objetivo: transformar o jogo em simulação panorâmica em uma ilha jogada pelo mouse,
eliminando a necessidade de controlar um avatar físico para fazer as tarefas.

- [x] Mapa da Ilha em pixel art cercado por oceano profundo, águas rasas, praias de areia dourada e platô fértil.
- [x] Remoção do avatar/personagem físico e de suas restrições de colisão para trabalhar.
- [x] Câmera livre com Pan (arrastar com mouse/toque) com limites da ilha.
- [x] Zoom dinâmico suave pela roda do mouse (scroll wheel de 0.45x a 2.2x) com foco sob o cursor.
- [x] Controles de zoom acessíveis no HUD (`[+]`, `[-]` e `[⌂ Centralizar]`).
- [x] Estruturas interativas com detecção de hover e clique (Casa, Mercado, Poço, Barco, Talhões).

## Fase 3 — Agricultura Point & Click ✅

Objetivo: permitir que todas as etapas agrícolas sejam realizadas diretamente
com o mouse com resposta visual imediata.

- [x] Catálogo de culturas integrado ao frontend (Milho, Cenoura, Tomate, Morango, Café).
- [x] Plantio direto por clique: clicar em talhão vazio abre seletor com sementes disponíveis do inventário.
- [x] Visual dos talhões em tempo real: brotos verdejantes e plantas maduras coloridas.
- [x] Indicador flutuante pulsante de colheita pronta.
- [x] Colheita com 1 clique no talhão com animação de recompensa flutuante (`+3 Milho`, `+1 Semente`).
- [x] Botão de colheita geral no HUD (`🌾 Colher Tudo (X)`).
- [x] Modais DOM integrados para a Casa da Fazenda e o Armazém do Mercado.
- [x] Sincronização periódica da produção em background com o servidor.

## Fase 4 — Economia básica 🟡

- [x] Carteira com AgroCoin (AGC) e `WalletLedger` (migração `0003_wallet`).
- [x] Venda de safras ao entreposto, com taxa de 5%.
- [x] Compra de sementes no entreposto.
- [x] Histórico financeiro (extrato) por API e na interface.
- [x] Idempotência (`Idempotency-Key`) e transações atômicas.
- [x] Testes de saldo, taxas, idempotência, autorização e conciliação do ledger.
- [x] Interface do mercado 100% por mouse e saldo no HUD.
- [ ] Balanceamento fino de preços com dados de jogo reais.
- [ ] Rate limiting nas rotas de mercado (Fase 8).

## Fase 4.5 — Progressão e Talentos 🟡

Desenho completo em [`TALENTS.md`](TALENTS.md). Inserida antes da Fase 5 por decisão
de produto (2026-11-23); guildas e disputas permanecem nas Fases 6 e 7.

- [x] Fatia 1 — XP e níveis (1 a 50), XP por plantio e colheita, barra no HUD.
- [x] Fatia 2 — Motor de modificadores e talentos (Agricultura e Comércio), pontos, presets, redefinição e simulador de paridade.
- [x] Fatia 3 — Interface da árvore de talentos (mapa SVG com pan/zoom, painel lateral, presets).
- [ ] Fatia 4 — Demais ramos, conforme as mecânicas da Fase 5.

## Fase 5 — Produção 🟡

- [x] Construções melhoráveis: Casa da Fazenda (expansão de terreno) e Poço (irrigação).
- [x] Bônus de construções integrado ao motor de modificadores (`ModifierService`).
- [x] Uma fazenda por jogador e talhões iniciais fixos (corrige brecha de criação).
- [ ] Mais construções: celeiro (armazenamento), estábulo, galinheiro.
- [ ] Animais (galinha, vaca, ovelha, porco, cabra, abelha).
- [ ] Alimentação, ciclo de produção e melhorias.
- [ ] Receitas e estações (moinho, padaria, queijaria, engenho, cozinha).
- [ ] `ProductionJobs` para processos com duração.

## Fase 6 — Multiplayer econômico ⬜

- [ ] Mercado global e listagens.
- [ ] Trocas diretas e histórico comercial.
- [ ] Visitação de fazendas.
- [ ] Taxas e controle de inflação.
- [ ] WebSocket/SSE para eventos econômicos.

## Fase 7 — Expansão ⬜

- [ ] Cidades, regiões e pontos de interesse.
- [ ] Viagens automáticas e entregas.
- [ ] Profissões, habilidades, conquistas e equipamentos.

## Fase 8 — Lançamento ⬜

- [ ] Hardening de segurança e rate limiting.
- [ ] Performance, índices e carga.
- [ ] Testes E2E com Playwright.
- [ ] Observabilidade, backups e monitoramento.
- [ ] Beta fechado.

## MVP — checklist

| Requisito | Status |
|---|---|
| Cadastro e login | ✅ |
| Perfil do jogador (`Character`) | ✅ |
| Fazenda inicial | ✅ |
| Câmera livre (pan/zoom) | ✅ |
| Mapa da ilha em pixel art | ✅ |
| Plantio | ✅ |
| Colheita | ✅ |
| Produção offline | ✅ |
| Inventário | ✅ |
| Venda para NPCs | ✅ |
| Compra de sementes | ✅ |
| Experiência e níveis | ✅ |
| Construção melhorável | ✅ |

## Pendências técnicas

- Painel de criação de personagem ainda tem campos de avatar (tom de pele, cabelo, roupa).
- Ampliar E2E Playwright: plantio e colheita pela UI (hoje cobre cadastro, perfil, HUD e sessão).
- Pasta `workers/` do backend (necessária a partir da Fase 5).

> **MVP completo:** todos os itens do checklist acima estão entregues (falta apenas
> validar o ciclo no navegador com Docker/PostgreSQL e balancear com dados reais).

## Próxima entrega recomendada

**Fase 5, animais:** estruturas de criação (galinheiro, estábulo) como construções do
catálogo, animais com alimentação e produção offline determinística, reaproveitando
`buildings`, `ModifierService`, `ModalManager` e o menu do HUD. A `FarmScene` já foi dividida em módulos.
