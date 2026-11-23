# Talentos, Guildas e Disputas — Desenho Técnico

Documento de design aprovado em 2026-11-23. Descreve o sistema de progressão por
**Árvore de Talentos**, as **guildas** e o modelo de **disputas** do Agro & Tech.
Entrega em fatias pequenas (ver `ROADMAP.md`, Fase 4.5 e seguintes). Nada além da
fatia 1 (XP e níveis) está implementado ainda.

## 1. Princípios

- O servidor calcula tudo; o cliente só envia intenções (`{node_id}`).
- Nenhum bônus é calculado em código espalhado: tudo passa pelo **motor de modificadores**.
- Especialização é recompensada, mas nenhuma build domina e todas têm teto.
- A fazenda é o centro: nenhuma disputa destrói plantações, inventário ou propriedade.
- Tudo é determinístico e funciona offline (sem eventos em tempo real obrigatórios).
- Interação 100% por mouse/toque.

## 2. Motor de modificadores (`game/modifiers.py`)

Cada efeito de talento tem a forma `(stat, escopo, operação, valor)`, por exemplo
`crop_yield · cultura=soja · +8%`.

`resolve(stat, base, contexto)` soma os bônus por fonte (talentos, guilda,
território, equipamentos), aplica o **teto da estatística** e devolve o valor final.

Estatísticas previstas (cada uma só pode ser usada por talentos quando a mecânica
correspondente existir; um teste impede talentos para estatísticas não implementadas):

| Estatística | Mecânica | Teto |
|---|---|---|
| `crop_yield` | produção por colheita | +60% |
| `crop_grow_time` | tempo de crescimento | −40% |
| `extra_harvest_chance` | colheita extra | 25% |
| `seed_save_chance` | economia de semente | 30% |
| `xp_gain` | XP | +50% |
| `sell_price` | preço de venda ao entreposto | +25% |
| `market_fee` | taxa de venda | mínimo 1% |

Regras:

- Modificadores do plantio (tempo e produção) são **gravados no plantio** quando ele
  é criado. Trocar de preset nunca altera plantações em andamento (determinismo offline).
- Chances usam sorteio com semente derivada de `(planting_id, ciclo)`: recarregar a
  página não permite sortear de novo.

## 3. Catálogo de talentos

Definido em código (versionado, como o catálogo de culturas). Cada nó:
`id`, ramo, camada, custo, pré-requisitos (todos/algum), nível mínimo, grupo de
exclusão, efeitos e posição `(x, y)` no mapa.

| Camada | Custo | Papel |
|---|---|---|
| Básico | 1 | benefício pequeno e acessível |
| Intermediário | 2 | especialização (uma cultura, um mercado) |
| Avançado | 3 | modifica uma mecânica |
| Mestre | 5 | define a build; um por ramo (exclusivo) |
| Lendário | 8 | raro, grande investimento |

Regras de especialização: cada camada exige um mínimo de pontos no próprio ramo
(o Mestre, por exemplo, exige 20). Híbridos exigem cerca de 10 pontos em dois ramos
e entregam sinergias. O total de pontos não cobre todos os ramos.

Ramos iniciais: Agricultura, Comércio, Pecuária, Indústria, Exploração, Estratégia
e Defesa. Ramos propostos: Logística e Mar, Solo e Água, Gastronomia.
Híbridos propostos: contratos de safra (Agricultura + Comércio), laticínios
(Pecuária + Indústria), botânico (Exploração + Agricultura), rotas protegidas
(Estratégia + Comércio), cães de guarda (Defesa + Pecuária).

**Escopo de lançamento:** só Agricultura e Comércio têm efeito. Os demais ramos
aparecem bloqueados e marcados "em breve" até suas mecânicas existirem.

## 4. Dados

| Tabela | Conteúdo |
|---|---|
| `player_progress` | XP do jogador (o nível é derivado) — **implementada** |
| `talent_presets` | presets: nome, espaço, ativo, último uso |
| `preset_nodes` | nós adquiridos por preset |
| `talent_respecs` | auditoria de trocas e redefinições |

Pontos de talento vêm do nível; cada preset redistribui o mesmo total.

## 5. Presets

- 1 espaço inicial; novos espaços por nível, até 5.
- Trocar de build: apenas na própria fazenda, com cooldown e custo em AGC
  proporcional ao nível. A primeira redefinição é gratuita.
- Durante a janela de uma disputa, os talentos dos participantes ficam congelados
  a partir de um snapshot.

## 6. Interface

Mapa em SVG dentro do DOM, com pan/zoom por mouse e toque; raiz central (a fazenda),
um setor por ramo, camadas crescendo para fora e híbridos nas fronteiras. Painel
lateral com o talento selecionado, tooltip, minimapa, pontos disponíveis, progresso
por ramo e barra de presets embaixo. Estilo pergaminho/mapa antigo. Se passar de
cerca de 150 nós, migrar a renderização para Phaser.

## 7. Guildas (Fase 6)

Tabelas: `guilds`, `guild_members` (líder, oficial, membro), `guild_invites`,
`guild_messages`, `guild_vault` (com ledger, mesmo padrão da carteira) e
`guild_missions`. Chat por REST com polling, evoluindo para WebSocket.

A árvore coletiva usa o mesmo motor de modificadores (fonte `guild`). Pontos vêm do
nível da guilda e são investidos por contribuições de itens e AGC, com decisão dos
oficiais. Bônus de território entram no mesmo `resolve`.

## 8. Disputas e combate (Fases 6 e 7)

Modelo adotado: **pontuação cooperativa assíncrona**, sem PvP direto em fazendas.

- **Disputas territoriais** em janelas de 48h. A guilda soma pontos em cinco
  categorias: produção (entrega de safras), comércio (contratos), indústria,
  exploração e defesa. Cada categoria vale no máximo 30% do total, o que exige
  builds complementares. O resultado é calculado no servidor a partir do ledger
  de contribuições.
- **Expedições PvE** em grupo, com timer. A composição importa (explorador revela
  rotas, defensor reduz perdas, industrial fornece equipamento). Resultado
  determinístico, com recompensa proporcional ao risco.
- **Competição econômica:** contratos, corridas de produção, eventos de colheita e
  rotas comerciais (píer e barco).

Proteções: nenhuma perda de fazenda, inventário ou plantações (o custo é só o que
foi contribuído e o território); disputas entre guildas de poder parecido, com
recompensa maior contra mais fortes; trégua de 24h após derrota; limite de
confrontos repetidos; nível mínimo 10 para disputas; bônus de reconstrução.

## 9. Exemplos de sinergia

1. O agricultor de soja entrega a safra, o industrial a transforma e o comerciante a
   vende em contrato: os três pontuam na mesma disputa.
2. O explorador revela uma região e o estrategista a fortifica antes da janela.
3. O defensor reduz perdas de uma expedição liderada pelo botânico, atrás de
   sementes raras.
4. Uma guilda de laticínios (pecuária + indústria) abastece uma rota comercial
   protegida por uma guilda aliada.

## 10. Entrega em fatias

1. **XP e níveis** (feito).
2. Motor de modificadores + talentos no servidor (Agricultura e Comércio), pontos,
   presets e redefinição, com simulador de paridade entre builds (±10% de AGC/hora).
3. Interface da árvore.
4. Demais ramos, conforme a Fase 5 entrega as mecânicas.
5. Guildas e talentos coletivos (Fase 6).
6. Disputas e expedições (Fases 6 e 7).
