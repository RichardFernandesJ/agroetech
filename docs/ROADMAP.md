# Roadmap — Agro & Tech

Documento de progresso. A ordem segue a seção 12 do `AGENTS.md`: cada fase só
avança quando a anterior está executável e testada. “Concluído” significa
implementado **e** verificado; “parcial” significa que existe base funcional,
mas falta escopo da fase.

Última atualização: 2026-11-22.

## Visão geral

| Fase | Tema | Status |
|---|---|---|
| 1 | Fundação | ✅ Concluída |
| 2 | Mundo (personagem, mapa, movimento) | ⏭️ Próxima |
| 3 | Agricultura | 🟡 Backend concluído; integração visual pendente |
| 4 | Economia básica | ⬜ Não iniciada |
| 5 | Produção (animais, construções, fabricação) | ⬜ Não iniciada |
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
| Phaser | Phaser 3.90 + TypeScript + Vite; boot, health check e cena placeholder responsiva. |
| Autenticação | Cadastro, login por e-mail/username, JWT HS256 e `/auth/me`. |
| Documentação | `README.md`, `docs/architecture.md`, `docs/decisions.md`, `docs/GDD.md`, `docs/API.md`, `docs/DATABASE.md`, `docs/ROADMAP.md`, `docs/CHANGELOG.md`. |
| Migrações | Alembic configurado, revisão `0001_foundation` e teste de paridade schema/models. |

**Pendência de validação:** o Docker não está instalado no ambiente de
desenvolvimento usado até aqui. O Compose foi validado como YAML e o runtime foi
testado com Uvicorn + SQLite; falta executar `docker compose up --build` em uma
máquina com Docker.

## Fase 2 — Mundo ⏭️

Objetivo: dar corpo jogável ao MVP no cliente, mantendo o servidor como fonte
da verdade.

- [ ] Modelo `Character` (nome, aparência, posição, fazenda atual).
- [ ] Criação de personagem no cadastro ou no primeiro acesso.
- [ ] Mapa inicial em pixel art (tiles 16×16 ou 32×32, top-down).
- [ ] Movimentação com teclado e toque, animação de caminhada.
- [ ] Colisões com cenário e limites do mapa.
- [ ] Interações por proximidade (talhão, construção, NPC).
- [ ] Câmera seguindo o personagem e HUD mínimo.
- [ ] Endpoint para persistir posição/aparência e testes de autorização.

Critérios de saída: o jogador entra, cria/escolhe personagem, anda pelo mapa,
colide corretamente e interage com pelo menos um objeto.

## Fase 3 — Agricultura 🟡

Backend já entrega o ciclo principal. O que falta é a camada visual e escopo
opcional da seção 6 do `AGENTS.md`.

Concluído:

- [x] Catálogo de sementes e produtos.
- [x] Plantio por talhão com consumo de sementes.
- [x] Crescimento por timestamp e colheita manual.
- [x] Produção offline com janela e teto de ciclos.
- [x] Inventário por propriedade.
- [x] Culturas de ciclo único e recorrentes.

Pendente:

- [ ] Integração da fazenda Phaser com inventário/plantio/colheita.
- [ ] Preparação do terreno, irrigação e fertilizantes.
- [ ] Culturas especiais e desbloqueios por nível.
- [ ] Ferramentas/equipamentos de trabalho.

## Fase 4 — Economia básica ⬜

- [ ] Carteira com AgroCoin (AGC) e `WalletLedger`.
- [ ] Venda de produtos para NPCs.
- [ ] Loja de sementes.
- [ ] Histórico financeiro e auditoria.
- [ ] Idempotência em operações sensíveis.
- [ ] Testes de saldo, taxas e prevenção de duplicação.

## Fase 5 — Produção ⬜

- [ ] Animais (galinha, vaca, ovelha, porco, cabra, abelha).
- [ ] Alimentação, ciclo de produção e melhorias.
- [ ] Construções e expansão de terreno.
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
| Criação de personagem | ⬜ |
| Fazenda inicial | ✅ (criação via API; automática no primeiro acesso pendente) |
| Movimentação | ⬜ |
| Mapa em pixel art | ⬜ |
| Plantio | ✅ backend |
| Colheita | ✅ backend |
| Produção offline | ✅ backend |
| Inventário | ✅ backend |
| Venda para NPCs | ⬜ |
| Compra de sementes | ⬜ |
| Experiência e níveis | ⬜ |
| Construção melhorável | ⬜ |

## Próxima entrega recomendada

**Fase 2, incremento 1:** modelo `Character` + endpoint de criação/consulta +
cena de criação de personagem. Em seguida, mapa e movimentação. A criação de
personagem vem antes do mapa porque define o dado que a cena de mundo precisa
carregar.
