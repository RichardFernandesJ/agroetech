# GDD — Agro & Tech

**Slogan:** Cultive sua história. Construa seu legado.
**Gênero:** RPG rural / farming simulator / idle game com economia multiplayer.
**Plataforma:** navegador (desktop e mobile), Phaser 3 + TypeScript.
**Câmera:** top-down, pixel art.

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
4. **Economia sustentável.** Nenhum mecanismo pode emitir moeda ou item sem
   contrapartida; transações precisam ser atômicas e auditáveis.
5. **Mundo com identidade própria.** Pixel art rural original, sem copiar
   sprites, mapas ou nomes de outros jogos.

## 2. Loop principal

```
plantar → crescer (online/offline) → colher → vender → comprar sementes
   ↑                                                    │
   └──────────── expandir fazenda / melhorar ←──────────┘
```

No MVP, o jogador deve conseguir entrar, criar o personagem, andar pela
fazenda, plantar, sair, voltar, colher, vender e fazer uma melhoria.

## 3. Estado atual do design

| Sistema | Estado |
|---|---|
| Conta e login | Implementado |
| Propriedade e talhões | Implementado (criação via API) |
| Inventário | Implementado |
| Plantio, crescimento e colheita | Implementado no backend |
| Produção offline | Implementado no backend |
| Catálogo de culturas | Implementado (5 culturas) |
| Personagem e mapa | Planejado — Fase 2 |
| Economia (AGC) | Planejado — Fase 4 |
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
3. O jogador precisa ter a semente correspondente.
4. A semente é consumida no plantio.
5. O tempo de crescimento é calculado pelo servidor e gravado em
   `next_ready_at`.

### 4.3 Colheita

- A colheita é **manual**. Produção offline apenas deixa ciclos prontos
  armazenados no plantio.
- Cada ciclo colhido entrega `yield_quantity` do produto e `seed_yield` da
  semente.
- Colheita individual (`POST /plantings/{id}/harvest`) ou em lote
  (`POST /properties/{id}/harvest`).

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

## 5. Personagem e mundo (Fase 2)

Planejado:

- Personagem 32×32 com animação de caminhada em quatro direções.
- Mapa inicial da fazenda com tiles de 16×16 ou 32×32.
- Colisão com cercas, construções, água e limites do mapa.
- Interação por proximidade: talhão, casa, placa, NPC.
- Câmera seguindo o personagem; HUD em DOM para inventário e ações.
- Persistência de posição e aparência no servidor.

Decisão de design: o personagem **não** calcula crescimento nem recompensa. A
cena apenas apresenta o estado retornado pela API.

## 6. Economia (Fase 4)

- Moeda interna: **AgroCoin (AGC)**.
- Toda operação financeira validada no backend.
- Estruturas previstas: `WalletLedger`, `MarketListings`, `MarketTransactions`,
  `TradeOffers`, `TradeItems`.
- Requisitos: histórico, taxas, idempotência, transações atômicas, auditoria e
  prevenção de duplicação.
- Fontes de moeda devem ter sumidouros equivalentes (sementes, construções,
  taxas, melhorias) para evitar inflação.

## 7. Progressão (pós-MVP)

- XP por plantio, colheita, fabricação e exploração.
- Níveis desbloqueiam culturas, receitas, animais e expansões.
- Habilidades e profissões alteram eficiência, não substituem o ciclo principal.
- Conquistas como objetivos de médio prazo.

## 8. Identidade visual

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
