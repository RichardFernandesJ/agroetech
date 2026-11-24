# GDD — Agro & Tech

**Slogan:** Cultive sua história. Construa seu legado.
**Gênero:** Simulação de Fazenda na Ilha / Farming Tycoon / Idle Game com economia multiplayer.
**Plataforma:** navegador (desktop e mobile), Phaser 3 + TypeScript.
**Câmera:** visão aérea (God-view), pixel art, controle livre com mouse/toque (Pan & Zoom dinâmico).

Este documento registra as regras de jogo. Ele descreve o alvo de design e
marca claramente o que já existe no código. Implementação técnica fica em
`docs/architecture.md`; endpoints em `docs/API.md`.

## 1. Pilares

1. **Cultivar compensa.** O ciclo plantar → esperar → colher → vender → expandir
   deve ser legível e recompensador já nos primeiros minutos.
2. **O tempo trabalha pelo jogador.** Produção offline é parte do jogo, não um
   remendo; voltar depois de horas precisa render algo útil e previsível.
3. **Servidor é a verdade.** Tempo, inventário, saldo e recompensas são
   calculados no backend. O cliente envia intenções, nunca resultados.
4. **Visão panorâmica e jogabilidade relaxante.** O jogador contempla sua fazenda
   em uma ilha paradisíaca a partir de cima, sem atrito de movimentação física de
   um avatar para trabalhar. Toda ação acontece na ponta do mouse com fluidez.
5. **Economia sustentável.** Nenhum mecanismo pode emitir moeda ou item sem
   contrapartida; transações precisam ser atômicas e auditáveis.
6. **Mundo com identidade própria.** Pixel art rural e costeiro original, sem copiar
   sprites, mapas ou nomes de outros jogos.

## 2. Loop principal

```
plantar (clique no talhão) → crescer (online/offline) → colher (1 clique) → estocar/vender
   ↑                                                                               │
   └──────────────────────── expandir fazenda / melhorar ←────────────────────────┘
```

No MVP, o jogador entra, contempla sua ilha de cima, aproxima e afasta o zoom,
clica no talhão vazio para escolher e plantar uma semente do inventário, acompanha
o crescimento, colhe com 1 clique (ou colheita geral), consulta o armazém no
mercado e a sede da fazenda na casa.

## 3. Estado atual do design

| Sistema | Estado |
|---|---|
| Conta e login | Implementado |
| Propriedade e talhões | Implementado |
| Inventário e Armazém | Implementado (backend + modal frontend) |
| Plantio, crescimento e colheita | Implementado (backend + interação por clique no frontend) |
| Produção offline | Implementado no backend (simulação determinística) |
| Catálogo de culturas | Implementado (5 culturas) |
| Cenário em Ilha e Câmera Pan/Zoom | Implementado (God-view, sem avatar físico) |
| Feedback visual de lavouras e colheita | Implementado (brotos, plantas maduras, badge pulsante e recompensas flutuantes) |
| Economia (AGC) | Em andamento — Fase 4 (carteira, compra e venda NPC) |
| Animais, construções, fabricação | Planejado — Fase 5 |
| Mercado entre jogadores | Planejado — Fase 6 |
| XP, níveis, habilidades | Planejado |

## 4. Agricultura

### 4.1 Culturas iniciais

| Cultura | Cresce em | Rende por ciclo | Ciclos por plantio | Sementes no kit inicial |
|---|---:|---:|---:|---:|
| Milho | 5 min | 3 | 1 | 6 |
| Cenoura | 10 min | 4 | 1 | 4 |
| Tomate | 15 min | 3 | 3 | 3 |
| Morango | 20 min | 5 | 4 | 2 |
| Café | 60 min | 8 | 6 | 1 |

- Culturas de **ciclo único** liberam o talhão após a colheita.
- Culturas **recorrentes** voltam a crescer até esgotar `max_cycles`.
- Toda colheita devolve sementes (`seed_yield` por ciclo), mantendo o ciclo
  sustentável sem depender de loja.
- Um talhão comporta **um plantio ativo**. O histórico de plantios esgotados é
  preservado.

### 4.2 Regras de plantio

1. O talhão precisa existir (`0 <= plot_index < plot_count`).
2. O talhão não pode ter outro plantio ativo.
3. O jogador precisa ter a semente correspondente no inventário.
4. Ao clicar no talhão vazio, o modal exibe as sementes disponíveis com tempo e rendimento.
5. A semente é consumida no plantio no backend.
6. O tempo de crescimento é calculado pelo servidor e gravado em `next_ready_at`.

### 4.3 Colheita

- A colheita é acionada por **clique direto**:
  - Clicar em um talhão maduro (indicado por um distintivo dourado pulsante) colhe a safra imediatamente.
  - Botão no HUD `🌾 Colher Tudo (X)` permite colher todos os talhões prontos em um único clique.
- Cada ciclo colhido entrega `yield_quantity` do produto e `seed_yield` da semente.
- Feedback visual com recompensas flutuantes animadas subindo do talhão (`+3 Milho`, `+1 Semente`).

### 4.4 Produção offline

Regras atuais:

1. A simulação acontece sob demanda (login, listagem, plantio, colheita ou
   `POST /production/sync`).
2. Só conta o intervalo dentro da janela `AGRO_OFFLINE_MAX_HOURS` (padrão 12h).
3. No máximo `AGRO_OFFLINE_MAX_CYCLES_PER_PLANTING` ciclos ficam armazenados por
   plantio (padrão 8), além do limite natural da cultura.
4. Ciclos concluídos antes da janela são perdidos de propósito.
5. O relógio da fazenda (`last_production_sync_at`) avança para o instante da
   sincronização.

Exemplo: café (1 ciclo/hora, 6 safras), 30 horas offline, janela de 12 horas →
até 6 ciclos ficam prontos; ao colher, rendem 48 cafés e 6 sementes.

## 5. Mundo em Ilha e Navegação Point & Click

### 5.1 Sem Avatar Físico (God-View)
O jogo abandona a mecânica de controlar um boneco andando pelo mapa. O jogador atua
como o gestor supremo da fazenda:
- Não há colisão com obstáculos ou tempo perdido andando de um lado para o outro.
- A atenção do jogador é 100% voltada para as tomadas de decisão, planejamento da ilha e cultivo.

### 5.2 Câmera Pan & Zoom Livre
- **Pan (Arrasto):** Clicar e arrastar com o mouse (ou toque) move a visão livremente sobre a ilha.
- **Zoom Dinâmico:** A roda do mouse (scroll wheel) aproxima e afasta a visão (de 0.45x a 2.2x)
  com ponto focal inteligente sob o cursor do mouse.
- **Controles no HUD:** Botões dedicados `[+]`, `[-]` e `[⌂ Centralizar na Ilha]` facilitam
  o enquadramento em qualquer dispositivo.

### 5.3 O Cenário da Ilha
- A fazenda é cercada por oceano profundo com ondulações em pixel art.
- Orla da ilha com águas rasas turquesa, espumas de praia e areia dourada com conchas e estrelas-do-mar.
- Palmeiras tropicais ao longo da praia e árvores rurais no platô central fértil.
- Estruturas com interação no clique:
  - **Casa da Fazenda:** Painel com métricas da ilha, área, talhões e controle de conta.
  - **Mercado e Píer Portuário:** Armazém geral de sementes e produtos com ancoradouro de barco.
  - **Poço Artesiano:** Ponto de irrigação de água doce.
  - **Lagoa Interna:** Enseada de água doce no quadrante sudoeste.

## 6. Economia (Fase 4)

- Moeda interna: **AgroCoin (AGC)**.
- Toda operação financeira validada no backend.
- Estruturas previstas: `WalletLedger`, `MarketListings`, `MarketTransactions`,
  `TradeOffers`, `TradeItems`.
- Requisitos: histórico, taxas, idempotência, transações atômicas, auditoria e
  prevenção de duplicação.
- **Implementado (entreposto NPC):**
  - Crédito inicial único de 100 AGC (única emissão sem contrapartida).
  - Sementes compradas do entreposto: milho 8, cenoura 14, tomate 22, morango 30, café 90.
  - Safras vendidas ao entreposto: milho 5, cenoura 6, tomate 6, morango 6, café 9 (por unidade).
  - Taxa de 5% sobre vendas, arredondada para baixo — é um sumidouro de moeda.
  - Valores em `backend/app/game/catalog.py` e `economy.py`; o cliente nunca envia preço.
  - Interação 100% por mouse: botões ×1, ×5 e Máx/Tudo, sem digitar quantidades.
- Fontes de moeda devem ter sumidouros equivalentes (sementes, construções,
  taxas, melhorias) para evitar inflação.

## 6.1 Construções e expansão de terreno

- **Casa da Fazenda:** cada melhoria abre mais talhões (6 → 8 → 10 → 12), custando
  150, 400 e 900 AGC e exigindo nível de jogador 3, 8 e 15. Os talhões novos aparecem
  no mapa a leste, em colunas de dois, e a cerca acompanha.
- **Poço da Ilha:** irrigação. Cada nível reduz o tempo de crescimento (−2%, −4%, −6%)
  por 60, 200 e 500 AGC (jogador nível 2, 6 e 12). Soma com os talentos pelo motor de
  modificadores (teto total de −25%).
- Cada jogador tem uma fazenda. Todas as melhorias são pagas pelo servidor, atômicas e
  idempotentes. Toda a interação é por clique (menu **🏗️ Construções**, a Casa ou o Poço).

## 7. Progressão

**Implementado:** XP e nível (1 a 50) por jogador. Plantar rende 2 XP; colher rende
XP por ciclo conforme a cultura. O HUD mostra nível e barra de XP, e avisa ao subir.

**Planejado:** árvore de talentos, presets, guildas e disputas — ver `docs/TALENTS.md`.

### Progressão (pós-MVP)

- XP por plantio, colheita, fabricação e exploração.
- Níveis desbloqueiam culturas, receitas, animais e expansões.
- Habilidades e profissões alteram eficiência, não substituem o ciclo principal.
- Conquistas como objetivos de médio prazo.

## 8. Identidade visual

- Estilo: **pixel art moderno** — pixels nítidos, paleta limpa e saturação controlada, sombras suaves e HUD em DOM nítido por cima.
- Pixel art top-down, sem suavização (`pixelArt`, `roundPixels`).
- Personagens 32×32; tiles 16×16 ou 32×32.
- Paleta rural: verdes dessaturados, terra, madeira, pedra e céu em gradiente.
- Ciclo de dia e noite previsto; iluminação não deve esconder informação de HUD.
- Assets organizados por categoria em `frontend/public/assets/` (a criar).
- A cena atual é um **placeholder vetorial**; não é a arte final.

## 9. Interface

- Canvas para o mundo; HUD e menus podem usar DOM sobreposto.
- Ações sempre com feedback imediato (som, animação, texto).
- Erros do servidor exibidos como mensagem curta, sem jargão técnico.
- Mobile: toque para mover/interagir; alvos mínimos de 44×44 px.

## 10. Regras de balanceamento

- Culturas curtas ensinam o loop; culturas longas pagam mais por hora.
- O teto offline evita progresso infinito sem exigir que o jogador esteja
  online o tempo todo.
- Sementes retornam na colheita para impedir bloqueio permanente por falta de
  insumo.
- Novas fontes de renda devem ser comparadas em **lucro por hora por talhão**.

## 11. Fora de escopo do MVP

- PvP, combate e guildas.
- Microtransações e moeda real.
- Microserviços, Kubernetes e sharding.
- Voz, tradução automática e multiplayer em tempo real complexo.

## 12. Critérios de sucesso do MVP

1. Um novo jogador entende o loop sem tutorial longo.
2. Plantar, sair por algumas horas, voltar e colher funciona de forma
   determinística.
3. Nenhuma recompensa pode ser duplicada por refresh, reenvio ou manipulação do
   cliente.
4. O jogo roda em desktop e mobile sem perda de legibilidade.
