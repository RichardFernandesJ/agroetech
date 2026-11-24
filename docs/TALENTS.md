# Talentos, Guildas e Disputas — Desenho Técnico

Documento de design aprovado em 2026-11-23. Descreve o sistema de progressão por
**Árvore de Talentos**, as **guildas** e o modelo de **disputas** do Agro & Tech.
Entrega em fatias pequenas (ver `ROADMAP.md`, Fase 4.5 e seguintes).
**Implementado:** fatia 1 (XP e níveis), fatia 2 (motor de modificadores e talentos no
servidor) e fatia 3 (interface da árvore). Guildas e disputas ainda não existem.

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
| `crop_yield` | produção por colheita | +30% |
| `crop_grow_time` | tempo de crescimento | −25% |
| `extra_harvest_chance` | colheita extra | 10% |
| `seed_save_chance` | economia de semente | 30% |
| `xp_gain` | XP | +50% |
| `sell_price` | preço de venda ao entreposto | +45% |
| `market_fee` | taxa de venda | mínimo 1% |
| `production_time` | tempo de fabricação (escopo: estação) | −25% |
| `production_yield` | rendimento da fabricação | +30% |
| `production_saving` | chance de um lote não gastar insumos | 25% |
| `animal_yield` | produtos dos animais (escopo: espécie) | +30% |
| `animal_speed` | tempo de produção dos animais | −25% |
| `feed_efficiency` | rendimento da ração | +30% |

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

**Escopo atual:** Agricultura, Comércio, Pecuária e Indústria têm efeito. Exploração e
Estratégia aparecem bloqueadas ("em breve") até suas mecânicas existirem.

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

## 11. Estado da fatia 2 (implementada)

- Catálogo: 26 talentos em Agricultura e Comércio, mais 1 híbrido (Contratos de Safra).
  Os outros quatro ramos aparecem no mapa como indisponíveis.
- Pontos: 1 por nível a partir do nível 2. Camadas pedem nível mínimo 2/5/10/20/35 e
  pontos já investidos no ramo 0/2/8/16/24. Um talento mestre por ramo (exclusivo).
- Presets: 1 espaço + 1 a cada 10 níveis (máx. 5). Trocar de build tem recarga de 1 h
  (a primeira troca é livre). Redefinir: primeira grátis, depois `nível × 5` AGC.
  A troca fica bloqueada quando `is_build_locked` for verdadeiro (gancho das disputas).
- Paridade: o simulador `tests/unit/balance.py` compara três builds de referência no
  nível 50. Hoje todas ficam entre +81% e +96% de AGC/hora sobre a base (diferença de
  8%, meta ±10%), com XP/hora dentro de 15%.
- Observação de balanceamento: como toda colheita devolve uma semente, **Economia de
  Sementes** quase não afeta o lucro; é um talento de conveniência. Se ganhar mais
  peso, revisar ou trocar o efeito.
- A troca de preset não exige estar na fazenda (a API não tem outro contexto de
  localização hoje); a regra entra com a interface.

## 12. Estado da fatia 3 (implementada)

- Abre pelo botão **🌳 Talentos** do menu do HUD (ou Esc/✕/clique fora para fechar).
- Mapa em SVG: pan por arrasto, zoom por roda do mouse, pinça no toque e botões
  `+`, `−`, `⌂` (centralizar nos talentos) e `⤢` (mapa inteiro). Um clique no fundo
  limpa a seleção; arrastar não seleciona talentos por engano.
- Estados visuais: adquirido (preenchido, linha acesa), disponível (halo pulsante,
  linha dourada), bloqueado (apagado) e ramo "em breve". Animação ao adquirir.
- Tooltip no hover, painel lateral com custo, nível, benefícios e o que ainda falta
  (a lista de requisitos pendentes é calculada no cliente só para exibir; o servidor
  continua validando tudo).
- Cabeçalho com pontos disponíveis e progresso por especialização.
- Rodapé com presets (ativar, criar, renomear, excluir), indicação de recarga,
  espaços bloqueados por nível e botão de redefinição com o custo.
- Layout responsivo: em telas estreitas o painel lateral vai para baixo do mapa.
- Cobertura: E2E `frontend/e2e/talents.spec.ts` (mapa com 27 nós, detalhes,
  requisito bloqueado, aquisição, pontos, criação de preset e fechamento).

## 13. Estado dos ramos Pecuária e Indústria (implementados)

- **Pecuária (13 talentos):** Pasto Verde, Cocho Farto, Manejo Gentil; especialistas por
  espécie (Avicultor, Leiteiro, Pastor) e Silagem; Genética, Ordenha e Nutrição; masters
  Rebanho (produtos) e Manejo (tempo), exclusivos; lendário Fazenda Modelo.
- **Indústria (13 talentos):** Ferramentas, Aproveitamento, Boa Receita; especialistas por
  estação (Moleiro, Padeiro, Queijeiro) e Estoque; Linha de Produção, Otimização e Controle de
  Qualidade; masters Eficiência (lote grátis) e Volume (rendimento), exclusivos; lendário
  Fábrica Lendária.
- **Híbridos:** *Laticínios* (Pecuária + Indústria: leite, queijo e manteiga +8% no preço) e
  *Feira de Produtos* (Comércio + Pecuária: ovos, leite e lã +8%). Exigem 6 pontos em cada ramo.
- **Sem efeito retroativo:** o plantio, a fabricação e agora o animal gravam os bônus ao
  começar (o animal, ao ser alimentado com fome). Trocar de build só afeta o que vier depois.
- **Paridade (simulador):** como animais e fabricação têm margem fina, qualquer bônus
  percentual rende muito mais ali. Para o Comércio não virar o melhor industrial, as margens
  foram elevadas (ração rende 35 min por porção; produtos processados valem mais) e o teste
  `test_each_specialist_wins_its_own_domain_without_being_overpowered` exige que: cada
  especialista fique entre 1,8× e 2,4× no próprio domínio; vença qualquer outra build de
  referência ali em pelo menos 5%; e a diferença entre especialistas fique em até 20%.
  Hoje: agricultor 1,96×, pecuarista 2,25× e industrial 2,28× (Comércio: 1,81× em lavoura,
  1,77× em animais e 2,07× em fabricação).

